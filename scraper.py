import argparse, time, os, csv, json, logging
from typing import List, Dict, Optional
import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, urlencode, parse_qs
import urllib.robotparser as robotparser

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("scrapper")

HEADERS = {
    "User-Agent": "MyScapperBot/1.0 (+https://example.com/info) Python-requests"
}

def _canonical_url(u: str) -> str:
    try:
        p = urlparse(u)
        scheme = (p.scheme or "http").lower()
        netloc = (p.netloc or "").lower()
        path = p.path or "/"
        if len(path) > 1 and path.endswith('/'):
            path = path.rstrip('/')
        # keep query (some shops use it for variants), drop fragment
        return urlunparse((scheme, netloc, path, '', p.query, ''))
    except Exception:
        return u


def can_fetch(url: str, user_agent: str = HEADERS["User-Agent"]) -> bool:
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


def parse_items(html: str, base_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    quote_blocks = soup.select("div.quote")
    for qb in quote_blocks:
        text_el = qb.select_one("span.text")
        author_el = qb.select_one("small.author")
        tags = [t.get_text(strip=True) for t in qb.select("div.tags a.tag")]
        items.append({
            "text": text_el.get_text(strip=True) if text_el else "",
            "author": author_el.get_text(strip=True) if author_el else "",
            "tags": ";".join(tags),
        })
    return items


def find_next_page(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        return urljoin(base_url, next_link["href"])
    return None


def save_to_csv(filename: str, rows: List[Dict], fieldnames: List[str]):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Saved {len(rows)} rows in {filename}")


def parse_products_shop(html: str, base_url: str) -> List[Dict]:
    def _extract_products_from_ldjson(soup: BeautifulSoup) -> List[Dict]:
        products: List[Dict] = []
        for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(tag.string or "{}")
            except Exception:
                continue
            stack = [data]
            while stack:
                node = stack.pop()
                if isinstance(node, list):
                    stack.extend(node)
                    continue
                if not isinstance(node, dict):
                    continue
                t = node.get("@type") or node.get("type")
                if isinstance(t, list):
                    t = t[0] if t else None
                if t == "Product":
                    offer = node.get("offers") or {}
                    if isinstance(offer, list):
                        offer = offer[0] if offer else {}
                    brand = node.get("brand")
                    if isinstance(brand, dict):
                        brand = brand.get("name")
                    agg = node.get("aggregateRating") or {}
                    if isinstance(agg, list):
                        agg = agg[0] if agg else {}
                    rating = None
                    review_count = None
                    try:
                        rating = float(agg.get("ratingValue")) if agg.get("ratingValue") is not None else None
                    except Exception:
                        pass
                    try:
                        review_count = int(agg.get("reviewCount")) if agg.get("reviewCount") is not None else None
                    except Exception:
                        pass
                    products.append({
                        "title": node.get("name"),
                        "description": node.get("description"),
                        "sku": node.get("sku"),
                        "brand": brand,
                        "price": (offer.get("price") if isinstance(offer, dict) else None),
                        "currency": (offer.get("priceCurrency") if isinstance(offer, dict) else None),
                        "availability": (offer.get("availability") if isinstance(offer, dict) else None),
                        "url": node.get("url"),
                        "rating": rating,
                        "review_count": review_count,
                    })
                for _, v in node.items():
                    if isinstance(v, (list, dict)):
                        stack.append(v)
        return [p for p in products if any(v is not None for v in p.values())]

    soup = BeautifulSoup(html, "html.parser")
    return _extract_products_from_ldjson(soup)


def parse_reviews(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    reviews: List[Dict] = []
    product_name: Optional[str] = None
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            t = node.get("@type") or node.get("type")
            if isinstance(t, list):
                t = t[0] if t else None
            if t == "Product":
                if not product_name:
                    product_name = node.get("name")
                rv = node.get("review")
                if isinstance(rv, list):
                    for r in rv:
                        if not isinstance(r, dict):
                            continue
                        author = r.get("author")
                        if isinstance(author, dict):
                            author = author.get("name")
                        rating = None
                        rr = r.get("reviewRating")
                        if isinstance(rr, dict):
                            try:
                                rating = float(rr.get("ratingValue")) if rr.get("ratingValue") is not None else None
                            except Exception:
                                pass
                        body = r.get("reviewBody") or r.get("description")
                        reviews.append({
                            "product": product_name,
                            "author": author,
                            "rating": rating,
                            "body": body,
                        })
            for _, v in node.items():
                if isinstance(v, (list, dict)):
                    stack.append(v)
    return reviews


def next_page_url(current_url: str, current_page: int) -> str:
    parsed = urlparse(current_url)
    q = parse_qs(parsed.query)
    page = current_page + 1
    q["page"] = [str(page)]
    new_query = urlencode({k: v[0] if isinstance(v, list) and v else v for k, v in q.items()})
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def save_products_with_reviews_txt(filename: str, products: List[Dict]):
    with open(filename, "w", encoding="utf-8") as f:
        for p in products:
            title = p.get("title") or ""
            brand = p.get("brand") or ""
            price = p.get("price")
            currency = p.get("currency") or ""
            rating = p.get("rating")
            url = p.get("url") or ""
            f.write(f"Product: {title}\n")
            f.write(f"Brand: {brand}\n")
            f.write(f"Price: {price} {currency}\n")
            if rating is not None:
                f.write(f"Stars: {rating}/5\n")
            f.write(f"URL: {url}\n")
            f.write("Reviews:\n")
            for r in p.get("reviews", []) or []:
                author = r.get("author") or ""
                rr = r.get("rating")
                body = (r.get("body") or "").strip()
                f.write(f"- Author: {author}\n")
                if rr is not None:
                    f.write(f"  Rating: {rr}\n")
                if body:
                    f.write(f"  {body}\n")
                f.write("  ---\n")
            f.write("====\n")

def scrape(start_url: str, output: str, delay: float = 1.0, max_pages: int = 50, mode: str = "quotes", max_reviews_per_product: Optional[int] = None):
    if not can_fetch(start_url):
        logger.error("Conform robots.txt, scraping isn't allowed for thi URL. Stopping.")
        return

    session = requests_session_with_retries()
    url = start_url
    all_items: List[Dict] = []
    pages_scraped = 0
    seen_items = set()           # canonical product URLs already added to CSV list
    reviews_fetched = set()      # canonical product URLs already fetched for reviews

    while url and pages_scraped < max_pages:
        html = fetch_page(session, url)
        if html is None:
            logger.warning(f"Skipping page: {url}")
            break
        if mode == "shop":
            items = parse_products_shop(html, url)
            # filter duplicates by canonical URL
            filtered: List[Dict] = []
            for it in items:
                purl = it.get("url")
                if not purl:
                    continue
                if not (purl.startswith("http://") or purl.startswith("https://")):
                    purl = urljoin(url, purl)
                can = _canonical_url(purl)
                it["url"] = can
                if can in seen_items:
                    continue
                seen_items.add(can)
                filtered.append(it)
            items = filtered
        else:
            items = parse_items(html, url)
        logger.info(f"Extracted {len(items)} items from {url}")
        all_items.extend(items)
        pages_scraped += 1

        # finding the next page (if exists)
        if mode == "shop":
            if not items:
                logger.info("No items on this page. Stopping.")
                break
            # fetch reviews for product pages and attach to items
            for it in items:
                purl = it.get("url")
                if not purl:
                    continue
                can = _canonical_url(purl)
                if can in reviews_fetched:
                    continue
                product_html = fetch_page(session, can)
                if product_html:
                    revs = parse_reviews(product_html)
                    if isinstance(max_reviews_per_product, int) and max_reviews_per_product > 0:
                        revs = revs[:max_reviews_per_product]
                    it["reviews"] = revs
                reviews_fetched.add(can)
            next_url = next_page_url(url, pages_scraped)
            url = next_url
        else:
            next_url = find_next_page(html, url)
            if not next_url:
                logger.info("No next page. Stopping.")
                break
            url = next_url

        logger.debug(f"Waiting {delay} seconds before next request.")
        time.sleep(delay)

    if all_items:
        # final de-duplication by URL
        rows = all_items
        if mode == "shop":
            unique_by_url = {}
            for it in all_items:
                u = it.get("url")
                if not u:
                    continue
                cu = _canonical_url(u)
                if cu not in unique_by_url:
                    unique_by_url[cu] = it
            rows = list(unique_by_url.values())
            # output a single TXT with products and their reviews
            base, ext = os.path.splitext(output)
            output_txt = output if ext.lower() == ".txt" else f"{base}.txt"
            save_products_with_reviews_txt(output_txt, rows)
        else:
            fieldnames = list(rows[0].keys())
            save_to_csv(output, rows, fieldnames)
    else:
        logger.info("I didn't find any items to save.")

def main():
    parser = argparse.ArgumentParser(description="Simple scraper (requests + BeautifulSoup)")
    parser.add_argument("start_url", nargs="?", default="https://quotes.toscrape.com",
                        help="URL de început (ex: https://quotes.toscrape.com)")
    parser.add_argument("-o", "--output", default="output.csv", help="CSV file output")
    parser.add_argument("-d", "--delay", type=float, default=1.0, help="Delay bettwin requests (secunde)")
    parser.add_argument("-m", "--max-pages", type=int, default=50, help="Max pages of steps")
    parser.add_argument("--mode", choices=["quotes", "shop"], default="quotes",
                        help="Scraping mode: 'quotes' (default) or 'shop' for e-commerce pages")
    parser.add_argument("--max-reviews", type=int, default=None,
                        help="Max reviews per product (shop mode). 0 or negative = unlimited")
    args = parser.parse_args()

    try:
        mr = args.max_reviews if (args.max_reviews is None or args.max_reviews > 0) else None
        scrape(args.start_url, args.output, delay=args.delay, max_pages=args.max_pages, mode=args.mode, max_reviews_per_product=mr)
    except KeyboardInterrupt:
        logger.warning("Canceled by user (CTRL+C)")


if __name__ == "__main__":
    main()