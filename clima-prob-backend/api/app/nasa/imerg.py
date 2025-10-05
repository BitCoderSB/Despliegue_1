import pandas as pd
import numpy as np
import requests
from .giovanni import giovanni_timeseries

IMERG_DAILY_CANDIDATES = [
    "GPM_3IMERGDF_07_precipitation",
    "GPM_3IMERGDF_07_precipitationCal",
    "GPM_3IMERGDF_precipitation",
    "GPM_3IMERGDF_precipitationCal",
]

def imerg_daily_series(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.Series:
    last_err = None
    for data_id in IMERG_DAILY_CANDIDATES:
        try:
            df = giovanni_timeseries(data_id, lat, lon, start_iso, end_iso, None)
            col = df.columns[0]
            s = df[col].rename("P_mmday").astype(float)
            s = s.resample("1D").mean()
            full_index = pd.date_range(start=start_iso[:10], end=end_iso[:10], freq="D", tz="UTC")
            return s.reindex(full_index)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"IMERG Daily no disponible. Último error: {repr(last_err)}")
