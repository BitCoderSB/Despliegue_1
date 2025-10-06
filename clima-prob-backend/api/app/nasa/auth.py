import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)

def giovanni_token() -> str:
    user, pwd = settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD
    if not (user and pwd):
        # Fallback opcional a ~/.netrc
        import netrc
        login, _, password = netrc.netrc().hosts['urs.earthdata.nasa.gov']
        user, pwd = login, password

    # URLs alternativas para probar
    signin_urls = [
        "https://api.giovanni.earthdata.nasa.gov/signin",
        "https://api.giovanni.earthdata.nasa.gov/gettoken", 
        "https://giovanni.gsfc.nasa.gov/signin"
    ]

    # Configurar sesión con reintentos
    session = requests.Session()
    
    # Estrategia de reintentos
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,  # 2, 4, 8 segundos
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Probar múltiples URLs automáticamente
    last_error = None
    token_received = False
    
    for url_idx, signin_url in enumerate(signin_urls):
        logger.info(f"🎯 Trying URL {url_idx + 1}/{len(signin_urls)}: {signin_url.split('/')[-1]}")
        
        max_attempts = 2  # Menos intentos por URL
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔑 Attempting token (URL {url_idx + 1}, attempt {attempt + 1}/{max_attempts})")
                
                r = session.get(
                    signin_url,
                    auth=HTTPBasicAuth(user, pwd),
                    allow_redirects=True,
                    timeout=90,  # Timeout más largo
                )
                
                # Verificar si la respuesta es un token válido (no HTML)
                logger.info(f"✅ Connection success with URL: {signin_url.split('/')[-1]}")
                
                # Verificar el contenido de la respuesta antes de aceptarla
                ctype = r.headers.get("Content-Type", "").lower()
                txt = r.text.strip()
                if "text/html" in ctype or txt.lower().startswith("<!doctype html") or "<html" in txt.lower():
                    logger.warning(f"⚠️ URL {signin_url.split('/')[-1]} returned HTML (authorization issue) - trying next URL")
                    # No hacer break, continuar con siguiente URL
                    break  # Sale del loop de attempts, continúa con siguiente URL
                
                logger.info(f"✅ Valid token received from: {signin_url.split('/')[-1]}")
                # Éxito real - marcar y salir de ambos loops
                token_received = True
                break
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ {signin_url.split('/')[-1]} attempt {attempt + 1} failed: {str(e)}")
                last_error = e
                
                if attempt < max_attempts - 1:
                    wait_time = 2
                    time.sleep(wait_time)
        else:
            # Si todos los intentos de esta URL fallaron, continuar con la siguiente
            continue
        
        # Si obtuvimos un token válido, salir del loop principal
        if token_received:
            break
    else:
        # Si todas las URLs fallaron
        raise RuntimeError(f"All Giovanni URLs failed. Last error: {str(last_error)}")
    
    # Si no obtuvimos token válido después de probar todas las URLs
    if not token_received:
        raise RuntimeError("All Giovanni URLs returned HTML (authorization issues). Check your NASA Earthdata account permissions.")

    # Procesar el token (r ya contiene la respuesta exitosa)
    if r.status_code in (401, 403):
        raise RuntimeError(f"EDL signin inválido ({r.status_code}). Revisa usuario/clave y autoriza GES DISC/Giovanni en tu cuenta.")

    r.raise_for_status()

    # Extraer y limpiar el token
    token = r.text.replace('"', "").strip()
    if not token or " " in token or "<" in token:
        raise RuntimeError("Token EDL inesperado. Respuesta no parece un token válido.")

    logger.info(f"🎉 Token obtained successfully: {token[:20]}...")
    return token
