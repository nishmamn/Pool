import json
import os
import re
from datetime import datetime, timedelta

import boto3
from dotenv import load_dotenv

from app.db import Pool, SessionLocal, create_pool, log_event, pool_total
from app.products import search_products

load_dotenv()

MODEL = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-2"))

SYSTEM = (
    "You are Pool, an agent that helps groups buy a gift or item together. "
    "Use search_products to find items within the budget that suit the recipient "
    "(consider who it is for, including their gender and interests if stated), "
    "choose the best one, then call create_pool with that product's id. "
    "Never invent product ids or prices. You cannot move money. "
    "The pool's target is the product's price, and friends each contribute a share "
    "until that target is reached. After creating the pool, reply in two or three "
    "plain sentences with the pool id, the product, the target amount, and the deadline. "
    "Do not include reasoning tags."
)

TOOL_SPECS = [
    {"toolSpec": {
        "name": "search_products",
        "description": "Search for purchasable products. Returns up to 5 with the cheapest in-stock price.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for"},
                "max_price": {"type": "number", "description": "Maximum price in USD"},
            },
            "required": ["query"],
        }},
    }},
    {"toolSpec": {
        "name": "create_pool",
        "description": "Create a group funding pool for one product found by search_products.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "id from search_products"},
                "budget": {"type": "number", "description": "User's maximum budget in USD"},
                "deadline_hours": {"type": "integer", "description": "Hours until the pool closes (default 72)"},
                "title": {"type": "string", "description": "Short pool name"},
            },
            "required": ["product_id", "budget"],
        }},
    }},
    {"toolSpec": {
        "name": "get_pool_status",
        "description": "Get the status and funding progress of a pool.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {"pool_id": {"type": "integer"}},
            "required": ["pool_id"],
        }},
    }},
]


def tool_search_products(args, state):
    results = search_products(args["query"], args.get("max_price"), limit=5)
    for r in results:
        state["seen"][r["id"]] = r
    return {"products": [
        {"id": r["id"], "title": r["title"], "price": r["price"],
         "retailer": r["retailer"], "offers_in_stock": r["offer_count"]}
        for r in results
    ]}


def tool_create_pool(args, state):
    product = state["seen"].get(args["product_id"])
    if not product:
        return {"error": "Unknown product_id. Search first and use an id from the results."}
    budget = float(args["budget"])
    if product["price"] > budget:
        return {"error": f"Product costs ${product['price']:.2f}, over the ${budget:.2f} budget."}
    hours = int(args.get("deadline_hours") or 72)
    if not 1 <= hours <= 336:
        return {"error": "deadline_hours must be between 1 and 336."}
    pool = create_pool(
        title=args.get("title") or f"Pool for {product['title'][:60]}",
        product_title=product["title"],
        product_url=product["url"] or "",
        target_amount=product["price"],
        deadline=datetime.now() + timedelta(hours=hours),
    )
    log_event(pool.id, "agent_created_pool", f"{product['title']} at ${product['price']:.2f} from {product['retailer']}")
    return {"pool_id": pool.id, "product": product["title"],
            "target_amount": product["price"], "deadline_hours": hours}


def tool_get_pool_status(args, state):
    with SessionLocal() as s:
        pool = s.get(Pool, int(args["pool_id"]))
        if not pool:
            return {"error": "Pool not found."}
        return {"pool_id": pool.id, "status": pool.status,
                "target_amount": pool.target_amount,
                "total_held": pool_total(pool.id),
                "deadline": pool.deadline.isoformat()}


HANDLERS = {
    "search_products": tool_search_products,
    "create_pool": tool_create_pool,
    "get_pool_status": tool_get_pool_status,
}


def run_agent(user_text: str, max_steps: int = 6) -> str:
    state = {"seen": {}}
    messages = [{"role": "user", "content": [{"text": user_text}]}]
    for _ in range(max_steps):
        resp = client.converse(
            modelId=MODEL,
            system=[{"text": SYSTEM}],
            messages=messages,
            toolConfig={"tools": TOOL_SPECS},
            inferenceConfig={"maxTokens": 800, "temperature": 0},
        )
        msg = resp["output"]["message"]
        messages.append(msg)
        if resp["stopReason"] != "tool_use":
            text = "".join(b.get("text", "") for b in msg["content"])
            return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()
        results = []
        for block in msg["content"]:
            if "toolUse" not in block:
                continue
            tu = block["toolUse"]
            print(f"  [tool] {tu['name']} {json.dumps(tu['input'])}")
            try:
                out = HANDLERS[tu["name"]](tu["input"], state)
            except Exception as e:
                out = {"error": str(e)}
            results.append({"toolResult": {
                "toolUseId": tu["toolUseId"],
                "content": [{"json": out}],
            }})
        messages.append({"role": "user", "content": results})
    return "Stopped: too many steps."