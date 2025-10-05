# ClimaProb Backend (FastAPI)

Backend para estimar **probabilidades climatológicas de excedencia** (very hot / very cold / very windy / very wet / very uncomfortable) por **día del año** usando históricos de NASA (Earthdata Cloud). Está pensado para desplegarse en **Google Cloud Run** (o **AWS App Runner**) y para trabajar en paralelo por **dos personas** sin pisarse.

> ⚠️ Importante: este backend **no es un pronóstico**. Calcula probabilidades basadas en climatología histórica y (opcionalmente) una tendencia temporal.

---
#### Para ejecutar  
```
python -m uvicorn api.app.main:app --reload --port 8080
```

---

## Características

- **API REST** con FastAPI.
- **Extracción de datos** (CMR → OPeNDAP / Earthdata Cloud) con `earthaccess` + `xarray`.
- **Agregación diaria** y variables derivadas (Tmax/Tmin, WS, precip, Heat Index).
- **Motor ML idóneo**: **Logistic Regression** calibrada con *features* estacionales (sin/cos DOY) + tendencia (year_norm).
- **Modo OFFLINE** con datos sintéticos para demos o fallas de red.
- **Caché** (memoria/diskcache o Redis).
- **Listo para contenedor** (Docker) y despliegue en Cloud Run/App Runner.

---

## Estructura del proyecto

```
api/
  app/
    nasa/        # extracción CMR/OPeNDAP + synthetic fallback
    prob/        # features + motor de probabilidades (logistic/empirical)
    cache/       # capa de caché
    utils/       # geo / time helpers
    main.py      # FastAPI endpoints
  tests/         # pytest
  requirements.txt
  Dockerfile
  gunicorn_conf.py
environment.yml  # entorno conda
README.md
```

**Separación de responsabilidades (2 personas):**
- **BE-1 (Datos NASA):** `app/nasa/*`, `utils/geo.py`, caché de series crudas.
- **BE-2 (ML + API):** `app/prob/*`, `pipeline.py`, `main.py`, caché de respuesta.

---

## Requisitos

- **Miniconda/Conda** (recomendado) o Python 3.11 con `pip`.
- Cuenta de **Earthdata** (para modo *live*).  
- **Docker** (opcional, para contenedor y despliegue).

---

## Arranque rápido (desarrollo local)

### 1) Crear estructura (opcional)
Si usas el script de *bootstrap* (proporcionado aparte):
```bash
bash bootstrap_backend.sh
```

### 2) Crear entorno (Conda)
```bash
conda env create -f environment.yml
conda activate climaprob-api
python -m ipykernel install --user --name climaprob-api
```

### 3) Variables de entorno
Copia el ejemplo y ajusta:
```bash
cd api
cp .env.example .env
# Edita EARTHDATA_* si vas a usar modo live
```

`.env` (campos):
```
EARTHDATA_USERNAME=tu_usuario
EARTHDATA_PASSWORD=tu_password
OFFLINE_MODE=true          # true = usa datos sintéticos (recomendado para dev)
CACHE_URL=                 # p.ej. redis://...
CACHE_TTL=14400            # 4 horas
LOG_LEVEL=info
```

### 4) Ejecutar en modo desarrollo
```bash
cd api
uvicorn app.main:app --reload --port 8080
```
- `GET http://localhost:8080/health` → debe retornar `{"ok": true, "mode": "synthetic"}` hasta integrar datos reales.

---

## Contrato del API

### `POST /api/probabilities`

**Request**
```json
{
  "lat": 19.4326,
  "lon": -99.1332,
  "buffer_km": 25,
  "start_date": "2001-01-01",
  "end_date": "2023-12-31",
  "date_of_interest": "2023-07-15",
  "engine": "logistic",
  "window_days": 7,
  "thresholds": {
    "very_hot_Tmax_C": 32,
    "very_cold_Tmin_C": 0,
    "very_windy_speed_ms": 10,
    "very_wet_precip_mmday": 20,
    "very_uncomfortable_HI_C": 32
  }
}
```

**Response (resumen)**  
Los valores son ilustrativos; en producción se calculan con datos reales.
```json
{
  "meta": {
    "lat": 19.4326,
    "lon": -99.1332,
    "period": "2001-01-01..2023-12-31",
    "engine": "logistic",
    "source": "MERRA-2 + GPM IMERG (Earthdata Cloud)",
    "mode": "synthetic"
  },
  "snapshot_date": "2023-07-15",
  "snapshot": {
    "very_hot": 0.61,
    "very_cold": 0.01,
    "very_windy": 0.19,
    "very_wet": 0.23,
    "very_uncomfortable": 0.52
  },
  "curves": {
    "very_hot": [{"doy":1,"p_raw":0.08,"p_smooth":0.08}, "..."],
    "very_cold":  ["..."],
    "very_windy": ["..."],
    "very_wet":   ["..."],
    "very_uncomfortable": ["..."]
  },
  "download": {"csv": null, "json": null}
}
```

---

## Flujo de datos (pipeline)

1) **Entrada**: lat/lon, fecha de interés, rango histórico, umbrales, motor.  
2) **Extracción** (BE-1): CMR → OPeNDAP (Earthdata Cloud) con `earthaccess`; subsetting espacial/temporal con `xarray`.  
3) **Agregación diaria**: Tmax/Tmin (desde T2M/T10M), WS (desde U10/V10), precip diaria, Heat Index.  
4) **Probabilidades** (BE-2): Entrena **Logistic Regression** (y = excedencia) con `sin/cos(DOY)` + `year_norm`; genera **curva DOY** y **snapshot**.  
5) **Salida**: JSON con `meta`, `snapshot`, `curves` y (opcional) URLs de descarga.  
6) **Caché**: series crudas y respuestas finales por hash de parámetros.

---

## Tests

```bash
cd api
pytest -q
```

Tipos de pruebas:
- **Unitarias**: features de tiempo, DTOs, lógica del modelo con datos sintéticos.
- **E2E (offline)**: endpoint con `OFFLINE_MODE=true`.
- **Smoke (live)**: 1–2 casos pequeños con credenciales Earthdata (opcional).

---

## Docker

**Build & run local:**
```bash
cd api
docker build -t weather-api:local .
docker run -p 8080:8080 --env-file .env weather-api:local
```

---

## Despliegue

### Google Cloud Run (recomendado)
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/weather-api ./api

gcloud run deploy weather-api   --image gcr.io/PROJECT_ID/weather-api   --region us-east1 --platform managed   --allow-unauthenticated   --memory 2Gi --cpu 1 --concurrency 40   --min-instances 0 --max-instances 5   --timeout 120

# Env vars (usa Secret Manager para EARTHDATA_*) 
gcloud run services update weather-api --region us-east1   --update-env-vars OFFLINE_MODE=false,CACHE_TTL=14400
```

### AWS App Runner (alternativa)
- Empuja la imagen a **ECR**, crea servicio en App Runner (1 vCPU / 2 GiB típico).
- Variables de entorno equivalentes (`EARTHDATA_*`, `OFFLINE_MODE`, etc.).
- Logs en CloudWatch; secretos con AWS Secrets Manager.

---

## Solución de problemas

- **403/401 al acceder a Earthdata**: revisa `EARTHDATA_USERNAME/PASSWORD`; usa `.netrc` o variables de entorno. Si persiste, activa `OFFLINE_MODE=true` para seguir trabajando.
- **Requests lentos**: limita rango histórico y `buffer_km`; habilita caché y *prewarm* para ubicaciones/fechas comunes.
- **Memoria**: mantén bbox pequeño (10–25 km) y lee solo variables necesarias.
- **Tiempos de espera**: usa timeouts y reintentos exponenciales hacia OPeNDAP.

---

## Roadmap corto

- **Engine empírico** como alternativa explicable (LOWESS).
- Export zip (CSV/JSON + manifest).
- Diagnóstico de tendencia (odds ratio último quinquenio vs histórico).

---

## Créditos y aviso

- Datos de NASA Earthdata (GES DISC y otros centros). Respeta términos de uso y atribuciones.  
- Este proyecto es educativo y orientado a hackathon; valida supuestos antes de uso operativo.

---

## Licencia

MIT
