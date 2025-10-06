import numpy as np
import pandas as pd
from typing import Tuple

_DOY_CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334], dtype=int)

def ensure_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy().sort_index()
    d = d[~d.index.duplicated(keep="first")]
    return d

def doy365(idx: pd.DatetimeIndex) -> np.ndarray:
    months = idx.month.values
    days   = idx.day.values
    days = np.where((months == 2) & (days == 29), 28, days)
    return _DOY_CUM[months - 1] + days

def window_mask(idx: pd.DatetimeIndex, date_of_interest: pd.Timestamp, window_days: int) -> np.ndarray:
    idx_utc = idx.tz_convert("UTC") if getattr(idx, "tz", None) is not None else idx
    doi = pd.to_datetime(date_of_interest)
    doi = doi.tz_convert("UTC") if doi.tzinfo is not None else doi.tz_localize("UTC")
    d_series = doy365(idx_utc)
    d0 = doy365(pd.DatetimeIndex([doi]))[0]
    dist = np.abs(d_series - d0)
    dist = np.minimum(dist, 365 - dist)
    return dist <= window_days

def wilson_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float, float]:
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    center = p + z**2/(2*n)
    adj = z*np.sqrt((p*(1-p) + z**2/(4*n)) / n)
    lo = (center - adj) / denom
    hi = (center + adj) / denom
    return (p, max(0.0, lo), min(1.0, hi))
