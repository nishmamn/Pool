import os
import httpx
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.trychannel3.com/v1/search"


def raw_search(query: str):
    r = httpx.post(
        URL,
        headers={
            "x-api-key": os.environ["CHANNEL3_API_KEY"],
            "Content-Type": "application/json",
        },
        json={"query": query},
        timeout=30,
    )
    if r.status_code >= 400:
        print("Channel3 error:", r.status_code, r.text)
        r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("products", [])


def _amount(price):
    if isinstance(price, (int, float)):
        return float(price)
    if isinstance(price, dict):
        for key in ("amount", "price", "value"):
            v = price.get(key)
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    return float(v)
                except ValueError:
                    pass
    return None


def _currency(price):
    return price.get("currency", "USD") if isinstance(price, dict) else "USD"


def search_products(query: str, max_price: float | None = None, limit: int = 5):
    """Search Channel3 and return products with their cheapest in-stock offer."""
    results = []
    for p in raw_search(query):
        offers = []
        for o in p.get("offers", []):
            avail = str(o.get("availability", "")).lower()
            if "out" in avail or "sold" in avail:
                continue
            amt = _amount(o.get("price"))
            if amt is None:
                continue
            offers.append((amt, o))
        if not offers:
            continue
        amt, best = min(offers, key=lambda t: t[0])
        if max_price is not None and amt > max_price:
            continue
        results.append({
            "id": p.get("id"),
            "title": p.get("title"),
            "price": amt,
            "currency": _currency(best.get("price")),
            "retailer": best.get("domain"),
            "url": best.get("url"),
            "offer_count": len(offers),
        })
    return results[:limit]