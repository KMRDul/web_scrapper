import json
from typing import List, Dict, Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from bs4 import BeautifulSoup


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
                    "price": offer.get("price"),
                    "currency": offer.get("priceCurrency"),
                    "availability": offer.get("availability"),
                    "url": node.get("url"),
                    "rating": rating,
                    "review_count": review_count,
                })
            # walk nested nodes
            for k, v in node.items():
                if isinstance(v, (list, dict)):
                    stack.append(v)
    return [p for p in products if any(v is not None for v in p.values())]


def parse_products(html: str, base_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = _extract_products_from_ldjson(soup)
    return items


def next_page_url(url: str, current_page: int) -> str:
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    page = current_page + 1
    q["page"] = [str(page)]
    new_query = urlencode({k: v[0] if isinstance(v, list) and v else v for k, v in q.items()})
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def parse_reviews(html: str) -> List[Dict]:
    """Extract review entries from Product JSON-LD on a product page.
    Returns list of dicts: {product, author, rating, body}
    """
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
            # walk nested nodes
            for k, v in node.items():
                if isinstance(v, (list, dict)):
                    stack.append(v)
    return reviews
