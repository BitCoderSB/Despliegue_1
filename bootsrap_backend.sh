#!/usr/bin/env bash
set -euo pipefail

PROJECT="clima-prob-backend"
echo "Creando estructura para ${PROJECT} ..."

# Directorios
mkdir -p ${PROJECT}/api/app/{nasa,prob,cache,utils}
mkdir -p ${PROJECT}/api/tests
mkdir -p ${PROJECT}/api/infra
mkdir -p ${PROJECT}/notebooks
mkdir -p ${PROJECT}/shared

# Placeholders .txt para trackear en Git
for d in \
  ${PROJECT}/api \
  ${PROJECT}/api/app \
  ${PROJECT}/api/app/nasa \
  ${PROJECT}/api/app/prob \
  ${PROJECT}/api/app/cache \
  ${PROJECT}/api/app/utils \
  ${PROJECT}/api/tests \
  ${PROJECT}/api/infra \
  ${PROJECT}/notebooks \
  ${PROJECT}/shared
do
  echo "placeholder for $d" > "$d/KEEP.txt"
done

# environment.yml (opcional: copiar el que te di arriba)
cat > ${PROJECT}/environment.yml <<'YML'
name: climaprob-api
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - numpy
  - pandas
  - xarray
  - netcdf4
  - cftime
  - bottleneck
  - dask-core
  - scipy
  - pip:
      - fastapi==0.115.5
      - uvicorn[standard]==0.30.6
      - gunicorn==22.0.0
      - pydantic-settings==2.4.0
      - python-dotenv==1.0.1
      - requests==2.32.3
      - pydap==3.4.1
      - earthaccess==0.9.1
      - scikit-learn==1.5.2
      - statsmodels==0.14.2
      - redis==5.0.8
      - diskcache==5.6.3
      - loguru==0.7.2
      - pytest==8.3.3
      - pytest-cov==5.0.0
      - ruff==0.6.9
      - black==24.8.0
      - ipykernel==6.29.5
      - jupyterlab==4.2.5
YML

# .gitignore básico
cat > ${PROJECT}/.gitignore <<'IGNORE'
__pycache__/
*.pyc
.env
.env.*
*.sqlite
.cache/
.DS_Store
.idea/
.vscode/
*.ipynb_checkpoints
IGNORE

# requirements.txt (útil para Docker slim)
cat > ${PROJECT}/api/requirements.txt <<'REQ'
fastapi==0.115.5
uvicorn[standard]==0.30.6
gunicorn==22.0.0
pydantic-settings==2.4.0
python-dotenv==1.0.1
numpy==2.1.1
pandas==2.2.3
xarray==2024.7.0
netCDF4==1.7.1
cftime==1.6.4.post1
bottleneck==1.4.0
dask==2024.8.2
scipy==1.13.1
requests==2.32.3
pydap==3.4.1
earthaccess==0.9.1
scikit-learn==1.5.2
statsmodels==0.14.2
redis==5.0.8
diskcache==5.6.3
loguru==0.7.2
REQ

# Dockerfile
cat > ${PROJECT}/api/Dockerfile <<'DOCKER'
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libnetcdf-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY app ./app
COPY gunicorn_conf.py .
ENV PORT=8080
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
DOCKER

# gunicorn_conf.py
cat > ${PROJECT}/api/gunicorn_conf.py <<'PY'
workers = 2
threads = 1
timeout = 120
bind = "0.0.0.0:8080"
worker_class = "uvicorn.workers.UvicornWorker"
PY

# .env.example
cat > ${PROJECT}/api/.env.example <<'ENV'
EARTHDATA_USERNAME=tu_usuario
EARTHDATA_PASSWORD=tu_password
OFFLINE_MODE=true
CACHE_URL=
CACHE_TTL=14400
LOG_LEVEL=info
ENV

# FastAPI scaffold mínimo
cat > ${PROJECT}/api/app/main.py <<'PY'
from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import date

app = FastAPI(title="Weather Likelihood API", version="0.1.0")

class Thresholds(BaseModel):
    very_hot_Tmax_C: float = 32.0
    very_cold_Tmin_C: float = 0.0
    very_windy_speed_ms: float = 10.0
    very_wet_precip_mmday: float = 20.0
    very_uncomfortable_HI_C: float = 32.0

class ProbabilitiesRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    buffer_km: float = Field(25, ge=0, le=200)
    start_date: date
    end_date: date
    date_of_interest: date
    engine: str = Field("logistic", pattern="^(logistic|empirical)$")
    window_days: int = Field(7, ge=0, le=30)
    thresholds: Thresholds = Thresholds()

@app.get("/health")
def health():
    return {"ok": True, "mode": "synthetic"}  # cambia a 'live' cuando integres datos reales

@app.post("/api/probabilities")
def probabilities(req: ProbabilitiesRequest):
    # TODO: integrar pipeline real. Por ahora, respuesta dummy.
    doy = req.date_of_interest.timetuple().tm_yday
    def make_curve():
        return [{"doy": i, "p_raw": 0.1, "p_smooth": 0.1} for i in range(1, 367)]
    curves = {
        "very_hot": make_curve(),
        "very_cold": make_curve(),
        "very_windy": make_curve(),
        "very_wet": make_curve(),
        "very_uncomfortable": make_curve(),
    }
    snapshot = {k: c[doy-1]["p_smooth"] for k, c in curves.items()}
    return {
        "meta": {"lat": req.lat, "lon": req.lon, "period": f"{req.start_date}..{req.end_date}", "engine": req.engine, "source": "placeholder", "mode": "synthetic"},
        "snapshot_date": str(req.date_of_interest),
        "snapshot": snapshot,
        "curves": curves,
        "download": {"csv": None, "json": None},
    }
PY

# Stubs BE-1 (datos) y BE-2 (ML)
cat > ${PROJECT}/api/app/nasa/synthetic.py <<'PY'
import numpy as np, pandas as pd
def generate_synthetic(start: str, end: str, varname: str) -> pd.Series:
    idx = pd.date_range(start, end, freq="D", tz="UTC")
    doy = idx.dayofyear.values
    seasonal = 0.5 + 0.4*np.sin(2*np.pi*(doy/366.0))
    noise = 0.1*np.random.randn(len(idx))
    base = {
        "Tmax_C": 25 + 10*seasonal + 2*noise,
        "Tmin_C": 12 + 6*seasonal  + 2*noise,
        "WS_ms":  4  + 3*seasonal  + 1*noise,
        "P_mmday": np.maximum(0, 5*seasonal + 5*np.random.rand(len(idx))),
        "HI_C":   26 + 9*seasonal  + 2*noise,
    }[varname]
    return pd.Series(base, index=idx, name=varname)
PY

cat > ${PROJECT}/api/app/prob/features.py <<'PY'
import numpy as np, pandas as pd
def add_time_features(dates: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    doy = dates.dayofyear.values
    years = dates.year.values
    y0, y1 = years.min(), years.max()
    sin = np.sin(2*np.pi*doy/366.0)
    cos = np.cos(2*np.pi*doy/366.0)
    year_norm = (years - y0) / max(1, (y1 - y0))
    return {"sin": sin, "cos": cos, "year_norm": year_norm, "doy": doy, "years": years, "y0": int(y0), "y1": int(y1)}
PY

cat > ${PROJECT}/api/app/prob/logistic.py <<'PY'
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
PY

# Tests mínimos
cat > ${PROJECT}/api/tests/test_health.py <<'PY'
from fastapi.testclient import TestClient
from app.main import app

def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert "ok" in r.json()
PY

# README (lo rellenamos en el siguiente bloque de tu solicitud)
echo "README placeholder (ver bloque README.md en el mensaje)" > ${PROJECT}/README.md

echo "Listo. Siguiente paso: crea el entorno con conda y ejecuta uvicorn."
echo "cd ${PROJECT} && conda env create -f environment.yml && conda activate climaprob-api"
echo "cd api && uvicorn app.main:app --reload --port 8080"
