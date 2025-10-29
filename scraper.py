import argparse, csv, time, logging, requests
from typing import List, Dict, Optional
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib.robotparser as robotparser

# config logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("scrapper")

HEADERS = {
    "User-Agent": "MyScapperBot/1.0 (+https://example.com/info) Python-requests"
}

def can_fetch(url: str, user_agent: str = HEADERS["User-Agent"]) -> bool:
    """Verifying if robots.txt is allowed for scraping for URL."""
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
        return True  # if we can't verify, we need to decide it to can (or it can return Flase)

def requests_session_with_retries(total_retries: int = 3, backoff: float = 0.3) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
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

def parse_items(html: str, base_url: str) -> List[Dict]:
    """It extracts data from URL. For example quotes.toscrape.com."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    quote_blocks = soup.select("div.quote")
    for qb in quote_blocks:
        text = qb.select_one("span.text").get_text(strip=True) if qb.select_one("span.text") else ""
        author = qb.select_one("small.author").get_text(strip=True) if qb.select_one("small.author") else ""
        tags = [t.get_text(strip=True) for t in qb.select("div.tags a.tag")]
        items.append({"text": text, "author": author, "tags": ";".join(tags)})
    return items

def find_next_page(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        return urljoin(base_url, next_link["href"])
    return None

def save_to_csv(filename: str, rows: List[Dict], fieldnames: List[str]):
    mode = "w"
    with open(filename, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Saved {len(rows)} rows in {filename}")

def scrape(start_url: str, output: str, delay: float = 1.0, max_pages: int = 50):
    if not can_fetch(start_url):
        logger.error("Conform robots.txt, scraping isn't allowed for thi URL. Stopping.")
        return

    session = requests_session_with_retries()
    url = start_url
    all_items: List[Dict] = []
    pages_scraped = 0

    while url and pages_scraped < max_pages:
        html = fetch_page(session, url)
        if html is None:
            logger.warning(f"Skipping page: {url}")
            break
        items = parse_items(html, url)
        logger.info(f"Extracted {len(items)} items from {url}")
        all_items.extend(items)
        pages_scraped += 1

        # finding the next page (if exists)
        next_url = find_next_page(html, url)
        if not next_url:
            logger.info("No next page. Stopping.")
            break

        logger.debug(f"Waiting {delay} seconds before next request.")
        time.sleep(delay)
        url = next_url

    if all_items:
        fieldnames = list(all_items[0].keys())
        save_to_csv(output, all_items, fieldnames)
    else:
        logger.info("I didn't find any items to save.")

def main():
    parser = argparse.ArgumentParser(description="Simple scraper (requests + BeautifulSoup)")
    parser.add_argument("start_url", nargs="?", default="https://quotes.toscrape.com",
                        help="URL de început (ex: https://quotes.toscrape.com)")
    parser.add_argument("-o", "--output", default="output.csv", help="CSV file output")
    parser.add_argument("-d", "--delay", type=float, default=1.0, help="Delay bettwin requests (secunde)")
    parser.add_argument("-m", "--max-pages", type=int, default=50, help="Max pages of steps")
    args = parser.parse_args()

    try:
        scrape(args.start_url, args.output, delay=args.delay, max_pages=args.max_pages)
    except KeyboardInterrupt:
        logger.warning("Canceled by user (CTRL+C)")


if __name__ == "__main__":
    main()