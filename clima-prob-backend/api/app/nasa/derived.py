import numpy as np
import pandas as pd

def K_to_C(x): return x - 273.15

def daily_agg(series: pd.Series, how: str) -> pd.Series:
    if how == "max":  return series.resample("1D").max()
    if how == "min":  return series.resample("1D").min()
    if how == "mean": return series.resample("1D").mean()
    if how == "sum":  return series.resample("1D").sum()
    raise ValueError("how debe ser 'max|min|mean|sum'")

def es_pa_from_Tc(Tc: pd.Series) -> pd.Series:
    es_hPa = 6.112 * np.exp(17.67 * Tc / (Tc + 243.5))
    return es_hPa * 100.0

def rh_from_q_p_t(q: pd.Series, P: pd.Series, T_K: pd.Series) -> pd.Series:
    e = (q * P) / (0.622 + 0.378 * q)
    Tc = K_to_C(T_K)
    es = es_pa_from_Tc(Tc)
    rh = (e / es) * 100.0
    return rh.clip(lower=0, upper=100)

def heat_index_C(Tc: pd.Series, RH: pd.Series) -> pd.Series:
    Tf = Tc * 9.0/5.0 + 32.0
    c = {"c1": -42.379, "c2": 2.04901523, "c3": 10.14333127, "c4": -0.22475541,
         "c5": -6.83783e-3, "c6": -5.481717e-2, "c7": 1.22874e-3, "c8": 8.5282e-4, "c9": -1.99e-6}
    HI_f = (c["c1"] + c["c2"]*Tf + c["c3"]*RH + c["c4"]*Tf*RH +
            c["c5"]*Tf*Tf + c["c6"]*RH*RH + c["c7"]*Tf*Tf*RH +
            c["c8"]*Tf*RH*RH + c["c9"]*Tf*Tf*RH*RH)
    return (HI_f - 32.0) * 5.0/9.0
