from urllib.parse import urlparse
import urllib.robotparser as robotparser
from .constants import HEADERS
from .logging_config import get_logger

logger = get_logger()


def can_fetch(url: str, user_agent: str = HEADERS["User-Agent"]) -> bool:
    """Check robots.txt permissions for a URL."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        allowed = rp.can_fetch(user_agent, url)
        logger.debug(f"robots.txt verificat la {robots_url}: allowed={allowed}")
        return allowed
    except Exception as e:
        logger.warning(f"Nu s-a putut citi robots.txt ({robots_url}): {e}. Continuăm cu precauție.")
        return True
