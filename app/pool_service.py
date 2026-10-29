from datetime import datetime

from sqlalchemy import select

from app import paypal
from app.db import Contribution, Pool, SessionLocal, add_contribution, log_event, pool_total


def _authorized(session, pool_id):
    return session.scalars(
        select(Contribution).where(
            Contribution.pool_id == pool_id,
            Contribution.status == "authorized",
        )
    ).all()


def start_contribution(pool_id, contributor, amount, return_url, cancel_url):
    """Create a PayPal order and return (contribution_id, approval_link)."""
    order = paypal.create_authorized_order(f"{amount:.2f}", return_url, cancel_url)
    link = next(l["href"] for l in order["links"] if l["rel"] in ("payer-action", "approve"))
    c = add_contribution(pool_id, contributor, amount, order_id=order["id"], status="pending")
    return c.id, link


def confirm_contribution(contribution_id):
    """After the buyer approves, place the hold (authorization) on their money."""
    with SessionLocal() as s:
        c = s.get(Contribution, contribution_id)
        auth = paypal.authorize_order(c.order_id)
        a = auth["purchase_units"][0]["payments"]["authorizations"][0]
        c.authorization_id = a["id"]
        c.status = "authorized"
        pool_id, who, amt = c.pool_id, c.contributor, c.amount
        s.commit()
    log_event(pool_id, "contribution_authorized", f"{who} ${amt:.2f} held")


def verify_before_capture(pool, contribs):
    """Plain-code safety checks that run before any money moves."""
    if pool.status != "open":
        return False, f"pool is {pool.status}, not open"
    if not contribs:
        return False, "no authorized contributions"
    if any(not c.authorization_id for c in contribs):
        return False, "a contribution is missing its authorization id"
    ids = [c.authorization_id for c in contribs]
    if len(ids) != len(set(ids)):
        return False, "duplicate authorization detected"
    total = sum(c.amount for c in contribs)
    if total < pool.target_amount:
        return False, f"total ${total:.2f} is below goal ${pool.target_amount:.2f}"
    return True, "ok"


def finalize_pool(pool_id):
    """Goal reached: verify, then capture every held payment."""
    events = []
    with SessionLocal() as s:
        pool = s.get(Pool, pool_id)
        contribs = _authorized(s, pool_id)
        ok, reason = verify_before_capture(pool, contribs)
        if not ok:
            events.append(("finalize_blocked", reason))
            result = (False, reason)
        else:
            for c in contribs:
                res = paypal.capture(c.authorization_id)
                done = res.get("status") == "COMPLETED"
                c.status = "captured" if done else "capture_failed"
                events.append((c.status, f"{c.contributor} ${c.amount:.2f}"))
            pool.status = "funded"
            events.append(("pool_funded", f"{pool.product_title}: goal ${pool.target_amount:.2f} reached"))
            result = (True, "funded")
        s.commit()
    for kind, detail in events:
        log_event(pool_id, kind, detail)
    return result


def expire_pool(pool_id):
    """Goal missed: void every held payment so nobody is charged."""
    events = []
    with SessionLocal() as s:
        pool = s.get(Pool, pool_id)
        contribs = _authorized(s, pool_id)
        for c in contribs:
            paypal.void(c.authorization_id)
            c.status = "voided"
            events.append(("voided", f"{c.contributor} ${c.amount:.2f} released"))
        pool.status = "expired"
        events.append(("pool_expired", "goal not reached, all holds released"))
        s.commit()
    for kind, detail in events:
        log_event(pool_id, kind, detail)
    return True, "expired"


def check_deadlines():
    """Run on a timer: close every pool whose deadline has passed."""
    with SessionLocal() as s:
        open_pools = s.scalars(
            select(Pool).where(Pool.status == "open", Pool.deadline <= datetime.now())
        ).all()
        ids = [p.id for p in open_pools]
    for pid in ids:
        if pool_total(pid) >= _target(pid):
            finalize_pool(pid)
        else:
            expire_pool(pid)
    return ids


def _target(pool_id):
    with SessionLocal() as s:
        return s.get(Pool, pool_id).target_amount