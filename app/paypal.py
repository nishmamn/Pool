import os
import time
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api-m.sandbox.paypal.com"
AUTH = (os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_SECRET"])

_client = httpx.Client(
    timeout=httpx.Timeout(30.0, connect=30.0),
    transport=httpx.HTTPTransport(retries=3),
)
_token_cache = {"value": None, "expires": 0.0}


def _token() -> str:
    if _token_cache["value"] and time.time() < _token_cache["expires"]:
        return _token_cache["value"]
    r = _client.post(
        f"{BASE}/v1/oauth2/token",
        auth=AUTH,
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    data = r.json()
    _token_cache["value"] = data["access_token"]
    _token_cache["expires"] = time.time() + int(data.get("expires_in", 300)) - 60
    return _token_cache["value"]


def _call(method: str, path: str, body: dict | None = None):
    r = _client.request(
        method,
        f"{BASE}{path}",
        json=body if body is not None else {},
        headers={
            "Authorization": f"Bearer {_token()}",
            "PayPal-Request-Id": str(uuid.uuid4()),
        },
    )
    if r.status_code >= 400:
        print("PayPal error:", r.status_code, r.text)
        r.raise_for_status()
    if r.status_code == 204 or not r.content:
        return {"status": "OK (no content)"}
    return r.json()


def create_authorized_order(amount: str, return_url: str, cancel_url: str):
    return _call("POST", "/v2/checkout/orders", {
        "intent": "AUTHORIZE",
        "purchase_units": [{"amount": {"currency_code": "USD", "value": amount}}],
        "payment_source": {"paypal": {"experience_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
        }}},
    })


def authorize_order(order_id: str):
    return _call("POST", f"/v2/checkout/orders/{order_id}/authorize")


def capture(authorization_id: str):
    return _call("POST", f"/v2/payments/authorizations/{authorization_id}/capture")


def void(authorization_id: str):
    return _call("POST", f"/v2/payments/authorizations/{authorization_id}/void")