import numpy as np
import pandas as pd
from dataclasses import dataclass
from ..utils.timewin import window_mask

@dataclass
class Thresholds:
    very_hot_Tmax_C: float = 32.0
    very_cold_Tmin_C: float = 0.0
    very_windy_speed_ms: float = 10.0
    very_wet_precip_mmday: float = 20.0
    very_uncomfortable_HI_C: float = 32.0

def make_thresholds_from_df(df: pd.DataFrame, date_of_interest: str, window_days: int = 7,
                            p_hot=0.90, p_cold=0.10, p_windy=0.90, p_wet=0.90, p_hi=0.90,
                            wet_floor_mm=1.0, wind_floor_ms=2.0) -> dict:
    doi = pd.to_datetime(date_of_interest)
    m = window_mask(df.index, doi, window_days)
    sub = df.loc[m]
    def pct(s, p): 
        s = s.dropna()
        return float(np.nanpercentile(s, p*100)) if s.size else np.nan
    thr = {}
    if "Tmax_C" in sub:
        v = pct(sub["Tmax_C"], p_hot); thr["very_hot_Tmax_C"] = float(v) if np.isfinite(v) else 30.0
    if "Tmin_C" in sub:
        v = pct(sub["Tmin_C"], p_cold); thr["very_cold_Tmin_C"] = float(v) if np.isfinite(v) else 5.0
    if "WS_ms" in sub:
        v = pct(sub["WS_ms"], p_windy); v = max(v, wind_floor_ms) if np.isfinite(v) else 6.0
        thr["very_windy_speed_ms"] = float(v)
    if "P_mmday" in sub:
        v = pct(sub["P_mmday"], p_wet); v = max(v, wet_floor_mm) if np.isfinite(v) else 10.0
        thr["very_wet_precip_mmday"] = float(v)
    if "HI_C" in sub:
        v = pct(sub["HI_C"], p_hi); thr["very_uncomfortable_HI_C"] = float(v) if np.isfinite(v) else 32.0
    return thr
