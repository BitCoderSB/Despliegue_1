"""
Generador de datos sintéticos para fallback cuando NASA Giovanni no está disponible
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_synthetic_temperature(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.DataFrame:
    """Genera serie sintética de temperatura basada en ubicación geográfica"""
    # Conversión de fechas
    start_date = pd.to_datetime(start_iso[:10])
    end_date = pd.to_datetime(end_iso[:10])
    dates = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
    
    # Parámetros climáticos basados en latitud
    base_temp = 25 - abs(lat) * 0.7  # Más frío cerca de los polos
    seasonal_amplitude = 15 - abs(lat) * 0.2  # Menor variación estacional en el ecuador
    
    # Generar temperaturas con patrones realistas
    temps = []
    for i, date in enumerate(dates):
        # Ciclo estacional (día del año)
        day_of_year = date.dayofyear
        seasonal = seasonal_amplitude * np.sin((day_of_year - 80) * 2 * np.pi / 365)
        
        # Variación diaria aleatoria
        daily_variation = np.random.normal(0, 3)
        
        # Temperatura base + estacional + variación
        temp = base_temp + seasonal + daily_variation
        temps.append(temp)
    
    # Crear DataFrame con Tmax y Tmin
    temp_series = pd.Series(temps, index=dates)
    
    return pd.DataFrame({
        'Tmax_C': temp_series + np.random.uniform(2, 8, len(temps)),  # Tmax más alta
        'Tmin_C': temp_series - np.random.uniform(2, 8, len(temps)),  # Tmin más baja
        'WS_ms': np.random.exponential(3, len(temps)),  # Viento exponencial
        'RH_pct': np.random.beta(2, 2, len(temps)) * 100,  # Humedad beta
        'HI_C': temp_series + np.random.uniform(0, 5, len(temps))  # Heat index
    }, index=dates)

def generate_synthetic_precipitation(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.Series:
    """Genera serie sintética de precipitación"""
    start_date = pd.to_datetime(start_iso[:10])
    end_date = pd.to_datetime(end_iso[:10])
    dates = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
    
    # Probabilidad de lluvia basada en ubicación
    rain_prob = 0.3 + abs(lat) * 0.01  # Más lluvia en latitudes medias
    
    # Generar precipitación (muchos ceros, algunos valores altos)
    precip = []
    for date in dates:
        if np.random.random() < rain_prob:
            # Día lluvioso - distribución exponencial
            rain = np.random.exponential(5)
        else:
            # Día seco
            rain = 0.0
        precip.append(rain)
    
    return pd.Series(precip, index=dates, name='P_mmday')

def synthetic_gldas_daily(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.DataFrame:
    """Simula gldas_daily_series con datos sintéticos"""
    return generate_synthetic_temperature(lat, lon, start_iso, end_iso)

def synthetic_imerg_daily(lat: float, lon: float, start_iso: str, end_iso: str) -> pd.Series:
    """Simula imerg_daily_series con datos sintéticos"""
    return generate_synthetic_precipitation(lat, lon, start_iso, end_iso)