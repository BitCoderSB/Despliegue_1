import pandas as pd
from .giovanni import giovanni_timeseries
from .derived import K_to_C, daily_agg, rh_from_q_p_t, heat_index_C

def gldas_daily_series(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.DataFrame:
    t_df = giovanni_timeseries("GLDAS_NOAH025_3H_2_1_Tair_f_inst",  lat, lon, start_iso, end_iso, None)
    w_df = giovanni_timeseries("GLDAS_NOAH025_3H_2_1_Wind_f_inst",  lat, lon, start_iso, end_iso, None)
    q_df = giovanni_timeseries("GLDAS_NOAH025_3H_2_1_Qair_f_inst",  lat, lon, start_iso, end_iso, None)
    p_df = giovanni_timeseries("GLDAS_NOAH025_3H_2_1_Psurf_f_inst", lat, lon, start_iso, end_iso, None)

    T_K   = t_df[t_df.columns[0]]
    T_C   = K_to_C(T_K)
    WS    = w_df[w_df.columns[0]]
    Qair  = q_df[q_df.columns[0]]
    Psurf = p_df[p_df.columns[0]]

    RH_pct  = rh_from_q_p_t(Qair, Psurf, T_K)
    HI_C_hr = heat_index_C(T_C, RH_pct)

    out = pd.DataFrame({
        "Tmax_C": daily_agg(T_C, "max"),
        "Tmin_C": daily_agg(T_C, "min"),
        "WS_ms":  daily_agg(WS,   "mean"),
        "RH_pct": daily_agg(RH_pct, "mean"),
        "HI_C":   daily_agg(HI_C_hr, "max"),
    })
    return out
