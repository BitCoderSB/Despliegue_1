from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import date, timedelta
import pandas as pd
import traceback
import logging

from ..nasa.build import build_dataset
from ..prob.thresholds import Thresholds, make_thresholds_from_df
from ..prob.compute import compute_probabilities

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        logger.info(f"🚀 Starting probability request for lat={req.lat}, lon={req.lon}, date={req.date_of_interest}")
        
        start_iso = f"{req.start_date.isoformat()}T00:00:00"
        end_iso   = f"{req.end_date.isoformat()}T23:59:59"
        
        logger.info(f"📅 Time range: {start_iso} to {end_iso}")

        # Paso 1: Obtener datos NASA
        try:
            logger.info("🌍 Fetching NASA data...")
            df = build_dataset(req.lat, req.lon, start_iso, end_iso)
            logger.info(f"📊 Data shape: {df.shape}, columns: {list(df.columns)}")
            
            if df.empty:
                logger.error("❌ DataFrame is empty!")
                raise HTTPException(status_code=422, detail=f"No data available for lat={req.lat}, lon={req.lon} in period {req.start_date} to {req.end_date}")
                
        except Exception as e:
            logger.error(f"❌ NASA data extraction failed: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"NASA data extraction failed: {str(e)}")

        # Paso 2: Calcular thresholds
        try:
            logger.info("📈 Calculating thresholds...")
            if req.thresholds is None or all(getattr(req.thresholds, k) is None for k in req.thresholds.model_fields):
                thr = make_thresholds_from_df(df, req.date_of_interest.isoformat(), window_days=req.window_days)
            else:
                # mezcla: usa los que vinieron y completa con adaptativos si hay None
                base = make_thresholds_from_df(df, req.date_of_interest.isoformat(), window_days=req.window_days)
                user = {k: getattr(req.thresholds, k) for k in base.keys()}
                thr = {k: (user[k] if user[k] is not None else base[k]) for k in base.keys()}
            logger.info(f"✅ Thresholds calculated: {thr}")
        except Exception as e:
            logger.error(f"❌ Threshold calculation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Threshold calculation failed: {str(e)}")

        # Paso 3: Calcular probabilidades
        try:
            logger.info(f"🎯 Computing probabilities with engine={req.engine}...")
            probs = compute_probabilities(
                df, req.date_of_interest.isoformat(), thr,
                window_days=req.window_days, engine=req.engine
            )
            logger.info(f"✅ Probabilities computed: {probs}")
        except Exception as e:
            logger.error(f"❌ Probability computation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Probability computation failed: {str(e)}")

        # Paso 4: Generar series para gráficas
        try:
            end_d = req.date_of_interest
            start_d = end_d - timedelta(days=29)
            last30 = df.loc[start_d.isoformat():end_d.isoformat()]
            series_T = [{"date": d.date().isoformat(), "value": float(v)} for d, v in last30["Tmax_C"].dropna().items()] if "Tmax_C" in df else []
            series_P = [{"date": d.date().isoformat(), "value": float(v)} for d, v in last30["P_mmday"].dropna().items()] if "P_mmday" in df else []
        except Exception as e:
            # No es crítico, puede devolver arrays vacíos
            series_T, series_P = [], []

        return {
            "location": {"lat": req.lat, "lon": req.lon, "date_of_interest": req.date_of_interest.isoformat()},
            "probabilities": probs,
            "series_for_plots": {
                "daily_Tmax_C_last30": series_T,
                "daily_P_mmday_last30": series_P
            },
            "meta": {"units": {"Tmax_C":"°C","P_mmday":"mm/day"}, "thresholds": thr}
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch-all para errores no manejados
        error_detail = f"Unexpected error: {str(e)}"
        print(f"Full traceback: {traceback.format_exc()}")  # Para logs de Render
        raise HTTPException(status_code=500, detail=error_detail)
