import requests
from requests.auth import HTTPBasicAuth
from ..config.settings import settings

def giovanni_token() -> str:
    user, pwd = settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD
    if not (user and pwd):
        # Fallback opcional a ~/.netrc
        import netrc
        login, _, password = netrc.netrc().hosts['urs.earthdata.nasa.gov']
        user, pwd = login, password

    r = requests.get(
        settings.GIOVANNI_SIGNIN_URL,
        auth=HTTPBasicAuth(user, pwd),
        allow_redirects=True,
        timeout=30,
    )

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
