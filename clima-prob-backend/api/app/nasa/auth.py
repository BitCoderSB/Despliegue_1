import requests
from requests.auth import HTTPBasicAuth
from ..config.settings import settings

def giovanni_token() -> str:
    """
    Usa EARTHDATA_USERNAME/EARTHDATA_PASSWORD si están en .env;
    si no, puedes mantener fallback a ~/.netrc (opcional).
    """
    user, pwd = settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD
    if not (user and pwd):
        # (Opcional) Fallback a netrc si quieres mantenerlo:
        import netrc
        login, _, password = netrc.netrc().hosts['urs.earthdata.nasa.gov']
        user, pwd = login, password

    r = requests.get(
        settings.GIOVANNI_SIGNIN_URL,
        auth=HTTPBasicAuth(user, pwd),
        allow_redirects=True,
        timeout=30
    )
    r.raise_for_status()
    return r.text.replace('"','').strip()
