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

    # Intentar múltiples veces manualmente también
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔑 Attempting Giovanni token (attempt {attempt + 1}/{max_attempts})")
            
            r = session.get(
                settings.GIOVANNI_SIGNIN_URL,
                auth=HTTPBasicAuth(user, pwd),
                allow_redirects=True,
                timeout=60,  # Aumentar timeout
            )
            
            # Éxito - procesar respuesta
            break
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Giovanni token attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_attempts - 1:
                raise RuntimeError(f"Giovanni token failed after {max_attempts} attempts. Last error: {str(e)}")
            
            # Esperar antes del siguiente intento
            wait_time = (attempt + 1) * 3
            logger.info(f"⏱️ Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)

    # 401/403 => credenciales malas o app no autorizada
    if r.status_code in (401, 403):
        raise RuntimeError(f"EDL signin inválido ({r.status_code}). Revisa usuario/clave y autoriza GES DISC/Giovanni en tu cuenta.")

    r.raise_for_status()

    # Si mandan HTML (página de login), no es un token
    ctype = r.headers.get("Content-Type", "").lower()
    txt = r.text.strip()
    if "text/html" in ctype or txt.lower().startswith("<!doctype html") or "<html" in txt.lower():
        raise RuntimeError("EDL devolvió HTML (no token). Debes iniciar sesión y autorizar 'NASA GESDISC DATA ARCHIVE / Giovanni' en https://urs.earthdata.nasa.gov (Applications).")

    token = txt.replace('"', "").strip()
    if not token or " " in token or "<" in token:
        raise RuntimeError("Token EDL inesperado. Respuesta no parece un token válido.")

    return token
