from fastapi import FastAPI
from .routes.probabilities import router as prob_router
from fastapi.middleware.cors import CORSMiddleware
from .config.settings import settings

app = FastAPI(title="Weather Likelihood API", version="0.2.0")

@app.get("/health")  
def health():
    return {
        "ok": True, 
        "mode": "live",
        "earthdata_configured": bool(settings.EARTHDATA_USERNAME and settings.EARTHDATA_PASSWORD)
    }

app.include_router(prob_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
