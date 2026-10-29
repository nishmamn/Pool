import json
from app.products import search_products, raw_search

results = search_products("hiking backpack", max_price=150)

if not results:
    print("No parsed results. Here is the raw first product so we can fix the code:")
    raw = raw_search("hiking backpack")
    if raw:
        first = raw[0]
        print(json.dumps({"keys": list(first.keys()),
                          "first_offer": (first.get("offers") or [None])[0]},
                         indent=2)[:1500])
    else:
        print("The API returned no products.")

for p in results:
    print(f'{p["title"]} | ${p["price"]} at {p["retailer"]} | {p["offer_count"]} offers')
    print("  ", p["url"])