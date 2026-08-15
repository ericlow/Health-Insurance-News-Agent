import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; HealthInsuranceNewsAgent/1.0)'}

_session = requests.Session()
_session.headers.update(HEADERS)
_retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
_session.mount('https://', HTTPAdapter(max_retries=_retry))
_session.mount('http://', HTTPAdapter(max_retries=_retry))


def get(url: str, timeout: int = 30) -> requests.Response:
    """GET with 3 retries on transient errors (5xx, 429, connection errors)."""
    resp = _session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp
