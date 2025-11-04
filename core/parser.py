from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def parse_items(html: str, base_url: str) -> List[Dict]:
    """Extract items from quotes.toscrape.com-like pages."""
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
