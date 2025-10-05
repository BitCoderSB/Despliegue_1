import pandas as pd
from .gldas import gldas_daily_series
from .imerg import imerg_daily_series

def build_dataset(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.DataFrame:
    gldas = gldas_daily_series(lat, lon, start_iso, end_iso)
    imerg = imerg_daily_series(lat, lon, start_iso, end_iso)
    df = gldas.join(imerg, how="outer").sort_index()
    return df.loc[start_iso[:10]:end_iso[:10]]
