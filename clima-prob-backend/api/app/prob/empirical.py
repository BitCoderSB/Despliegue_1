import numpy as np
import pandas as pd
from typing import Dict
from .thresholds import Thresholds
from ..utils.timewin import ensure_daily_index, window_mask, wilson_interval

def _labels_from_thresholds(df: pd.DataFrame, thr: Thresholds) -> Dict[str, pd.Series]:
    lab = {}
    if "Tmax_C" in df: lab["very_hot"]  = (df["Tmax_C"] >= thr.very_hot_Tmax_C)
    if "Tmin_C" in df: lab["very_cold"] = (df["Tmin_C"] <= thr.very_cold_Tmin_C)
    if "WS_ms"  in df: lab["very_windy"] = (df["WS_ms"] >= thr.very_windy_speed_ms)
    if "P_mmday" in df: lab["very_wet"] = (df["P_mmday"] >= thr.very_wet_precip_mmday)
    if "HI_C" in df: lab["very_uncomfortable"] = (df["HI_C"] >= thr.very_uncomfortable_HI_C)
    return lab

def empirical_probabilities(df_daily: pd.DataFrame, date_of_interest: str, thresholds: Thresholds, window_days: int = 7) -> Dict[str, Dict[str, float]]:
    df = ensure_daily_index(df_daily)
    doi = pd.to_datetime(date_of_interest)
    mask = window_mask(df.index, doi, window_days)
    dfw = df.loc[mask].dropna(how="all")
    labs = _labels_from_thresholds(dfw, thresholds)
    out = {}
    for name, y in labs.items():
        yy = y.dropna(); n = int(yy.shape[0]); k = int(yy.sum())
        p, lo, hi = wilson_interval(k, n, z=1.96)
        out[name] = {"prob": float(p if np.isfinite(p) else 0.0), "lo": float(lo or 0.0), "hi": float(hi or 0.0), "n": n, "k": k}
    return out
