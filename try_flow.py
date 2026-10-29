from datetime import datetime, timedelta

from app.db import create_pool, init_db, list_events, pool_total
from app.pool_service import confirm_contribution, expire_pool, finalize_pool, start_contribution

RETURN = "https://example.com/return"
CANCEL = "https://example.com/cancel"

init_db()
mode = input("Type 'fund' to reach the goal, or 'expire' to miss it: ").strip().lower()

pool = create_pool(
    "Gift for Priya", "Test hiking backpack", "https://example.com/backpack",
    50.0, datetime.now() + timedelta(hours=1),
)
amounts = [("Friend A", 30.0), ("Friend B", 25.0)] if mode == "fund" else [("Friend A", 20.0)]

for who, amt in amounts:
    cid, link = start_contribution(pool.id, who, amt, RETURN, CANCEL)
    print(f"\n{who} (${amt:.2f}): open this link in Incognito, log in as a sandbox PERSONAL account, and Pay:\n{link}")
    input("Press Enter after approving...")
    confirm_contribution(cid)

print("\nTotal held: $", pool_total(pool.id), "| Goal: $50.00")
if mode == "fund":
    print("Finalize:", finalize_pool(pool.id))
else:
    print("Expire:", expire_pool(pool.id))

print("\nActivity log:")
for e in list_events(pool.id):
    print(" -", e.kind, "|", e.detail)