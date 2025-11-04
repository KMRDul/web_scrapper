import requests
from requests.adapters import HTTPAdapter, Retry
from .constants import HEADERS
from .logging_config import get_logger
from typing import Optional

logger = get_logger()


def requests_session_with_retries(total_retries: int = 3, backoff: float = 0.3) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(HEADERS)
    return s


def fetch_page(session: requests.Session, url: str, timeout: int = 10) -> Optional[str]:
    logger.info(f"Fetching {url}")
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.error(f"Eroare la get {url}: {e}")
        return None
