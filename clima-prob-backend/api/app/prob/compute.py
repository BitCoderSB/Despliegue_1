import numpy as np
import pandas as pd
from typing import Dict
from .thresholds import Thresholds
from .empirical import empirical_probabilities

def compute_probabilities(
    df_daily: pd.DataFrame,
    date_of_interest: str,
    thresholds: Dict[str, float],
    window_days: int = 7,
    engine: str = "empirical",
) -> Dict[str, float]:

    thr = Thresholds(**thresholds)

    if engine == "logistic":

        try:
            from .logit import logistic_probabilities
        except Exception as e:
            raise RuntimeError("Logistic engine not available on this deploy") from e
        res = logistic_probabilities(df_daily, date_of_interest, thr, window_days=window_days)
    else:
        res = empirical_probabilities(df_daily, date_of_interest, thr, window_days=window_days)

    return {k: float(v.get("prob", np.nan)) for k, v in res.items()}
