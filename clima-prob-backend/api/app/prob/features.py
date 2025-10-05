import numpy as np, pandas as pd
def add_time_features(dates: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    doy = dates.dayofyear.values
    years = dates.year.values
    y0, y1 = years.min(), years.max()
    sin = np.sin(2*np.pi*doy/366.0)
    cos = np.cos(2*np.pi*doy/366.0)
    year_norm = (years - y0) / max(1, (y1 - y0))
    return {"sin": sin, "cos": cos, "year_norm": year_norm, "doy": doy, "years": years, "y0": int(y0), "y1": int(y1)}
