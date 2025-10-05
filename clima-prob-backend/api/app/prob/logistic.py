import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from .features import add_time_features

def train(daily: pd.Series, threshold: float, side: str = ">="):
    s = daily.dropna()
    y = (s >= threshold).astype(int) if side == ">=" else (s <= threshold).astype(int)
    feats = add_time_features(s.index)
    X = np.column_stack([feats["sin"], feats["cos"], feats["year_norm"]])
    base = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf = CalibratedClassifierCV(base, method="sigmoid", cv=3)
    clf.fit(X, y.values)
    return {"model": clf, "y0": feats["y0"], "y1": feats["y1"]}

def predict_curve(bundle, year_for_inference: int | None = None) -> pd.DataFrame:
    clf, y0, y1 = bundle["model"], bundle["y0"], bundle["y1"]
    doy = np.arange(1, 367)
    X = np.column_stack([
        np.sin(2*np.pi*doy/366.0),
        np.cos(2*np.pi*doy/366.0),
        np.full_like(doy, ((year_for_inference or y1) - y0)/max(1,(y1-y0)), dtype=float)
    ])
    p = clf.predict_proba(X)[:,1]
    return pd.DataFrame({"doy": doy, "p_raw": p, "p_smooth": p})
