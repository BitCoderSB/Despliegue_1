from fastapi import FastAPI
from .routes.probabilities import router as prob_router
from fastapi.middleware.cors import CORSMiddleware
from .config.settings import settings

app = FastAPI(title="Weather Likelihood API", version="0.2.0")

@app.get("/health")  
def health():
    mode = "synthetic" if settings.OFFLINE_MODE else "live"
    return {
        "ok": True, 
        "mode": mode,
        "offline_mode": settings.OFFLINE_MODE,
        "earthdata_configured": bool(settings.EARTHDATA_USERNAME and settings.EARTHDATA_PASSWORD)
    }

app.include_router(prob_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # luego cámbialo a tu dominio del FE
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# from fastapi import FastAPI, Query, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field
# from datetime import date, datetime
# import pandas as pd
# from .config import MODE
# from .nasa.synthetic import get_daily_series as get_synth

# APP_TITLE = "Weather Likelihood API"
# APP_VERSION = "0.1.0"

# VALID_VARS = {"Tmax_C", "Tmin_C", "WS_ms", "P_mmday", "HI_C"}
# MAX_SPAN_DAYS = 3660  # 10 years
# MIN_LAT, MAX_LAT = -90.0, 90.0
# MIN_LON, MAX_LON = -180.0, 180.0
# MIN_BUFFER_KM, MAX_BUFFER_KM = 0.0, 200.0
# DATE_REGEX = r"\d{4}-\d{2}-\d{2}"

# app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# # Allow frontend requests during development
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ---------- Data Models ----------
# class Thresholds(BaseModel):
#     very_hot_Tmax_C: float = 32.0
#     very_cold_Tmin_C: float = 0.0
#     very_windy_speed_ms: float = 10.0
#     very_wet_precip_mmday: float = 20.0
#     very_uncomfortable_HI_C: float = 32.0


# class ProbabilitiesRequest(BaseModel):
#     lat: float = Field(..., ge=-90, le=90)
#     lon: float = Field(..., ge=-180, le=180)
#     buffer_km: float = Field(25, ge=0, le=200)
#     start_date: date
#     end_date: date
#     date_of_interest: date
#     engine: str = Field("logistic", pattern="^(logistic|empirical)$")
#     window_days: int = Field(7, ge=0, le=30)
#     thresholds: Thresholds = Thresholds()


# # ---------- Validation helpers ----------
# def _parse_date(s: str) -> date:
#     try:
#         return datetime.fromisoformat(s).date()
#     except ValueError:
#         raise HTTPException(status_code=400, detail=f"Invalid date: {s}")


# def _validate_geo(lat: float, lon: float, buffer_km: float):
#     if not (MIN_LAT <= lat <= MAX_LAT):
#         raise HTTPException(status_code=400, detail="Latitude out of range [-90, 90]")
#     if not (MIN_LON <= lon <= MAX_LON):
#         raise HTTPException(status_code=400, detail="Longitude out of range [-180, 180]")
#     if not (MIN_BUFFER_KM <= buffer_km <= MAX_BUFFER_KM):
#         raise HTTPException(status_code=400, detail=f"buffer_km out of range [{MIN_BUFFER_KM}, {MAX_BUFFER_KM}]")


# def _validate_dates(start: str, end: str):
#     sd = _parse_date(start)
#     ed = _parse_date(end)
#     span = (ed - sd).days
#     if span < 0:
#         raise HTTPException(status_code=400, detail="Date range inverted (end < start)")
#     if span > MAX_SPAN_DAYS:
#         raise HTTPException(status_code=400, detail=f"Date range too large (> {MAX_SPAN_DAYS} days)")
#     return sd, ed


# # ---------- Endpoints ----------
# @app.get("/health")
# def health():
#     return {"ok": True, "mode": MODE}


# @app.post("/api/probabilities")
# def probabilities(req: ProbabilitiesRequest):
#     # Mock response until BE-2 model is implemented
#     doy = req.date_of_interest.timetuple().tm_yday

#     def make_curve():
#         return [{"doy": i, "p_raw": 0.1, "p_smooth": 0.1} for i in range(1, 367)]

#     curves = {
#         "very_hot": make_curve(),
#         "very_cold": make_curve(),
#         "very_windy": make_curve(),
#         "very_wet": make_curve(),
#         "very_uncomfortable": make_curve(),
#     }
#     snapshot = {k: c[doy - 1]["p_smooth"] for k, c in curves.items()}
#     return {
#         "meta": {
#             "lat": req.lat,
#             "lon": req.lon,
#             "period": f"{req.start_date}..{req.end_date}",
#             "engine": req.engine,
#             "source": "synthetic",
#             "mode": "synthetic",
#         },
#         "snapshot_date": str(req.date_of_interest),
#         "snapshot": snapshot,
#         "curves": curves,
#         "download": {"csv": None, "json": None},
#     }


# def _series_to_json(s: pd.Series):
#     return {
#         "index": s.index.strftime("%Y-%m-%d").tolist(),
#         "values": [None if pd.isna(v) else float(v) for v in s.values],
#         "name": s.name,
#     }


# @app.get("/nasa/daily")
# def nasa_daily(
#     lat: float,
#     lon: float,
#     buffer_km: float = 25.0,
#     start: str = Query(..., pattern=DATE_REGEX),
#     end: str = Query(..., pattern=DATE_REGEX),
#     varname: str = Query(...),
# ):
#     if varname not in VALID_VARS:
#         raise HTTPException(status_code=400, detail={"error": "Invalid varname", "valid": sorted(VALID_VARS)})

#     _validate_geo(lat, lon, buffer_km)
#     _validate_dates(start, end)

#     s = get_synth(lat, lon, buffer_km, start, end, varname)
#     return _series_to_json(s)
