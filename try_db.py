from datetime import datetime, timedelta

from app.db import add_contribution, create_pool, init_db, list_events, pool_total

init_db()

pool = create_pool(
    title="Gift for Priya",
    product_title="Test hiking backpack",
    product_url="https://example.com/backpack",
    target_amount=100.0,
    deadline=datetime.now() + timedelta(days=3),
)

add_contribution(pool.id, "Friend A", 40.0, status="authorized")
add_contribution(pool.id, "Friend B", 35.0, status="authorized")

print("Pool ID:", pool.id)
print("Total authorized: $", pool_total(pool.id))
print("Goal: $100.00 | Reached:", pool_total(pool.id) >= 100.0)
print("\nActivity log:")
for e in list_events(pool.id):
    print(" -", e.kind, "|", e.detail)