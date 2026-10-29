from app.paypal import create_authorized_order, authorize_order, capture, void

order = create_authorized_order(
    "25.00", "https://example.com/return", "https://example.com/cancel"
)
print("Order ID:", order["id"], "| status:", order["status"])

link = next(l["href"] for l in order["links"] if l["rel"] in ("payer-action", "approve"))
print("\nOpen this link, log in with a sandbox PERSONAL account, and approve:\n", link)
input("\nAfter approving, press Enter here...")

auth = authorize_order(order["id"])
a = auth["purchase_units"][0]["payments"]["authorizations"][0]
print("Authorization ID:", a["id"], "| status:", a["status"])

choice = input("Type 'capture' or 'void': ").strip().lower()
result = capture(a["id"]) if choice == "capture" else void(a["id"])
print("Result:", result)