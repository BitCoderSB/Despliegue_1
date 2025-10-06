
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Iterable, Optional


THRESHOLD_KEY = {
    "Tmax_C": "very_hot_Tmax_C",
    "Tmin_C": "very_cold_Tmin_C",
    "WS_ms": "very_windy_speed_ms",
    "P_mmday": "very_wet_precip_mmday",
    "HI_C": "very_uncomfortable_HI_C",
}

ALLOWED_VARS = {"Tmax_C", "Tmin_C", "WS_ms", "P_mmday", "HI_C", "RH_pct"}

def _doy365(idx: pd.DatetimeIndex) -> np.ndarray:
    """Day-of-year in 365-day calendar (29-feb → 28-feb)."""
    months = idx.month.values
    days   = idx.day.values
    days = np.where((months == 2) & (days == 29), 28, days)
    _DOY_CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334], dtype=int)
    return _DOY_CUM[months - 1] + days

def _window_mask(idx: pd.DatetimeIndex, date_of_interest: pd.Timestamp, window_days: int) -> np.ndarray:
    """Window mask ±K days around target DOY (circular)."""
    idx_utc = idx.tz_convert("UTC") if getattr(idx, "tz", None) is not None else idx
    doi = pd.to_datetime(date_of_interest)
    doi = doi.tz_convert("UTC") if doi.tzinfo is not None else doi.tz_localize("UTC")
    doy_series = _doy365(idx_utc)
    doy0 = _doy365(pd.DatetimeIndex([doi]))[0]
    dist = np.abs(doy_series - doy0)
    dist = np.minimum(dist, 365 - dist)
    return dist <= window_days

def monthly_climatology(
    df_daily: pd.DataFrame,
    variables: Optional[Iterable[str]] = None,
    qextras: Optional[Iterable[float]] = None,
) -> Dict[str, list]:
    """
    Devuelve un dict listo para graficar con 12 puntos por variable:
    { "month":[1..12], "<var>_mean":[..], opcional "<var>_p90":[..], ... }
    """
    d = df_daily.copy()
    d = d[~d.index.duplicated(keep="first")].sort_index()

    if variables is None:
        variables = [c for c in d.columns if c in ALLOWED_VARS]
    variables = list(variables)

    gb = d.groupby(d.index.month, observed=True)
    out = {"month": list(range(1, 13))}
    for v in variables:
        if v not in d.columns:
            continue
        m = gb[v].mean()
        out[f"{v}_mean"] = [float(m.get(mo, np.nan)) for mo in range(1, 13)]
        if qextras:
            for q in qextras:
                qq = gb[v].quantile(q)
                out[f"{v}_p{int(q*100)}"] = [float(qq.get(mo, np.nan)) for mo in range(1, 13)]
    return out

def window_percentiles(
    df_daily: pd.DataFrame,
    date_of_interest: str | pd.Timestamp,
    window_days: int,
    thresholds: Optional[Dict[str, float]] = None,
    variables: Optional[Iterable[str]] = None,
) -> Dict[str, dict]:
    """
    Devuelve stats por variable en ventana ±K días:
    { "window_days": K, "<var>": {"n","min","p10","p50","p90","max","threshold"} }
    """
    d = df_daily.copy()
    d = d[~d.index.duplicated(keep="first")].sort_index()

    doi = pd.to_datetime(date_of_interest)
    mask = _window_mask(d.index, doi, window_days)
    sub = d.loc[mask]

    if variables is None:
        variables = [c for c in sub.columns if c in ALLOWED_VARS]
    variables = list(variables)

    def _pct(s: pd.Series, q: float) -> float:
        x = s.dropna()
        return float(np.nanpercentile(x, q)) if x.size else float("nan")

    stats = {"window_days": int(window_days)}
    for v in variables:
        if v not in sub.columns:
            continue
        s = sub[v].dropna()
        if s.empty:
            stats[v] = {"n": 0, "min": np.nan, "p10": np.nan, "p50": np.nan, "p90": np.nan, "max": np.nan,
                        "threshold": float(thresholds.get(THRESHOLD_KEY[v], np.nan)) if thresholds else np.nan}
            continue
        stats[v] = {
            "n": int(s.size),
            "min": float(np.nanmin(s)),
            "p10": _pct(s, 10),
            "p50": _pct(s, 50),
            "p90": _pct(s, 90),
            "max": float(np.nanmax(s)),
            "threshold": float(thresholds.get(THRESHOLD_KEY[v], np.nan)) if thresholds else np.nan,
        }
    return stats
