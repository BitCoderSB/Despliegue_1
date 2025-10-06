import pandas as pd
import logging
from .gldas import gldas_daily_series
from .imerg import imerg_daily_series
from .synthetic import synthetic_gldas_daily, synthetic_imerg_daily
from ..config.settings import settings

logger = logging.getLogger(__name__)

def build_dataset(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.DataFrame:
    """
    Construye dataset combinando GLDAS + IMERG con fallback automático a datos sintéticos
    """
    

    if settings.OFFLINE_MODE:
        logger.info("🔄 OFFLINE_MODE enabled - using synthetic data")
        gldas = synthetic_gldas_daily(lat, lon, start_iso, end_iso)
        imerg = synthetic_imerg_daily(lat, lon, start_iso, end_iso)
        df = gldas.join(imerg, how="outer").sort_index()
        return df.loc[start_iso[:10]:end_iso[:10]]
    

    try:
        logger.info("🌍 Attempting to fetch real NASA data...")
        gldas = gldas_daily_series(lat, lon, start_iso, end_iso)
        logger.info("✅ GLDAS data fetched successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ GLDAS failed ({str(e)}), using synthetic data")
        gldas = synthetic_gldas_daily(lat, lon, start_iso, end_iso)
    
    try:
        imerg = imerg_daily_series(lat, lon, start_iso, end_iso)
        logger.info("✅ IMERG data fetched successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ IMERG failed ({str(e)}), using synthetic data")
        imerg = synthetic_imerg_daily(lat, lon, start_iso, end_iso)
    
    df = gldas.join(imerg, how="outer").sort_index()
    logger.info(f"📊 Final dataset shape: {df.shape}")
    return df.loc[start_iso[:10]:end_iso[:10]]
