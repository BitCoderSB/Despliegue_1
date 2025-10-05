from fastapi import APIRouter
from pydantic import BaseModel, Field
from datetime import date, timedelta
import pandas as pd

from ..nasa.build import build_dataset
from ..prob.thresholds import Thresholds, make_thresholds_from_df
from ..prob.compute import compute_probabilities

router = APIRouter(prefix="/api", tags=["probabilities"])

class ThresholdsIn(BaseModel):
    very_hot_Tmax_C: float | None = None
    very_cold_Tmin_C: float | None = None
    very_windy_speed_ms: float | None = None
    very_wet_precip_mmday: float | None = None
    very_uncomfortable_HI_C: float | None = None

class ProbabilitiesRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    start_date: date
    end_date: date
    date_of_interest: date
    engine: str = Field("empirical", pattern="^(logistic|empirical)$")
    window_days: int = Field(7, ge=0, le=30)
    thresholds: ThresholdsIn | None = None  # si no vienen, se calculan adaptativos

@router.post("/probabilities")
def probabilities(req: ProbabilitiesRequest):
    start_iso = f"{req.start_date.isoformat()}T00:00:00"
    end_iso   = f"{req.end_date.isoformat()}T23:59:59"

    df = build_dataset(req.lat, req.lon, start_iso, end_iso)

    # thresholds: si no vienen, calculamos adaptativos (p90/p10) en la ventana
    if req.thresholds is None or all(getattr(req.thresholds, k) is None for k in req.thresholds.model_fields):
        thr = make_thresholds_from_df(df, req.date_of_interest.isoformat(), window_days=req.window_days)
    else:
        # mezcla: usa los que vinieron y completa con adaptativos si hay None
        base = make_thresholds_from_df(df, req.date_of_interest.isoformat(), window_days=req.window_days)
        user = {k: getattr(req.thresholds, k) for k in base.keys()}
        thr = {k: (user[k] if user[k] is not None else base[k]) for k in base.keys()}

    probs = compute_probabilities(
        df, req.date_of_interest.isoformat(), thr,
        window_days=req.window_days, engine=req.engine
    )

    # series para 1–2 gráficas (últimos 30 días)
    end_d = req.date_of_interest
    start_d = end_d - timedelta(days=29)
    last30 = df.loc[start_d.isoformat():end_d.isoformat()]
    series_T = [{"date": d.date().isoformat(), "value": float(v)} for d, v in last30["Tmax_C"].dropna().items()] if "Tmax_C" in df else []
    series_P = [{"date": d.date().isoformat(), "value": float(v)} for d, v in last30["P_mmday"].dropna().items()] if "P_mmday" in df else []

    return {
        "location": {"lat": req.lat, "lon": req.lon, "date_of_interest": req.date_of_interest.isoformat()},
        "probabilities": probs,
        "series_for_plots": {
            "daily_Tmax_C_last30": series_T,
            "daily_P_mmday_last30": series_P
        },
        "meta": {"units": {"Tmax_C":"°C","P_mmday":"mm/day"}, "thresholds": thr}
    }
