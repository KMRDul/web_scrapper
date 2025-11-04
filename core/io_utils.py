import csv
from typing import List, Dict
from .logging_config import get_logger

logger = get_logger()


def save_to_csv(filename: str, rows: List[Dict], fieldnames: List[str]):
    mode = "w"
    with open(filename, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Saved {len(rows)} rows in {filename}")


def reset_file(path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write("")


def append_reviews_txt(filename: str, reviews: List[Dict]):
    if not reviews:
        return
    with open(filename, "a", encoding="utf-8") as f:
        for r in reviews:
            product = r.get("product") or ""
            author = r.get("author") or ""
            rating = r.get("rating")
            body = r.get("body") or ""
            f.write(f"Product: {product}\n")
            f.write(f"Author: {author}\n")
            f.write(f"Rating: {rating}\n")
            f.write("Review:\n")
            f.write(body.strip() + "\n")
            f.write("---\n")


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
