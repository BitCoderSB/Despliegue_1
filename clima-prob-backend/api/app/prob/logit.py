import numpy as np
import pandas as pd
from typing import Dict
from sklearn.linear_model import LogisticRegression
from .thresholds import Thresholds
from ..utils.timewin import ensure_daily_index, window_mask, wilson_interval

def _years_float(idx: pd.DatetimeIndex) -> np.ndarray:
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("UTC")
    return idx.year.values.astype(float)

def _labels_from_thresholds(df: pd.DataFrame, thr: Thresholds) -> Dict[str, pd.Series]:
    lab = {}
    if "Tmax_C" in df: lab["very_hot"]  = (df["Tmax_C"] >= thr.very_hot_Tmax_C)
    if "Tmin_C" in df: lab["very_cold"] = (df["Tmin_C"] <= thr.very_cold_Tmin_C)
    if "WS_ms"  in df: lab["very_windy"] = (df["WS_ms"] >= thr.very_windy_speed_ms)
    if "P_mmday" in df: lab["very_wet"] = (df["P_mmday"] >= thr.very_wet_precip_mmday)
    if "HI_C" in df: lab["very_uncomfortable"] = (df["HI_C"] >= thr.very_uncomfortable_HI_C)
    return lab

def logistic_probabilities(df_daily: pd.DataFrame, date_of_interest: str, thresholds: Thresholds, window_days: int = 7, min_pos: int = 5, min_neg: int = 5) -> Dict[str, Dict[str, float]]:
    df = ensure_daily_index(df_daily)
    doi = pd.to_datetime(date_of_interest)
    mask = window_mask(df.index, doi, window_days)
    sub = df.loc[mask].dropna(how="all")
    labs = _labels_from_thresholds(sub, thresholds)

    years_all = _years_float(sub.index)
    if years_all.size == 0:
        return {name: {"prob": np.nan, "n": 0, "k": 0, "engine": "empty"} for name in labs}

    year0 = float(np.mean(years_all))
    target_year = float(doi.year)
    X_pred = np.array([[target_year - year0]])

    out = {}
    for name, y in labs.items():
        yy = y.dropna().astype(int)
        if yy.empty:
            out[name] = {"prob": np.nan, "n": 0, "k": 0, "engine": "empty"}; continue
        common_idx = yy.index.intersection(sub.index)
        yi = yy.loc[common_idx].values
        Xi = (_years_float(common_idx) - year0).reshape(-1, 1)
        pos = int(yi.sum()); neg = int(yi.shape[0] - pos); n = pos + neg
        if pos < min_pos or neg < min_neg:
            p, lo, hi = wilson_interval(pos, n)
            out[name] = {"prob": float(0.0 if not np.isfinite(p) else p), "n": n, "k": pos, "engine": "empirical_fallback"}
            continue
        clf = LogisticRegression(class_weight="balanced", solver="lbfgs")
        clf.fit(Xi, yi)
        p = float(clf.predict_proba(X_pred)[0, 1])
        out[name] = {"prob": p, "n": n, "k": pos, "engine": "logistic_year_trend"}
    return out
