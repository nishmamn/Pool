import os
import threading
import time
from datetime import datetime

import streamlit as st
from sqlalchemy import select

from app.agent import run_agent
from app.db import Contribution, Pool, SessionLocal, init_db, list_events, pool_total
from app.pool_service import (
    check_deadlines,
    confirm_contribution,
    finalize_pool,
    start_contribution,
)

BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501")

st.set_page_config(page_title="Pool", layout="wide")
init_db()


@st.cache_resource
def start_scheduler():
    def loop():
        while True:
            try:
                check_deadlines()
            except Exception as e:
                print("scheduler error:", e)
            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


start_scheduler()


def all_pools():
    with SessionLocal() as s:
        return s.scalars(select(Pool).order_by(Pool.id.desc())).all()


# Handle the buyer coming back from PayPal
params = st.query_params
if "token" in params:
    order_id = params["token"]
    with SessionLocal() as s:
        c = s.scalars(
            select(Contribution).where(Contribution.order_id == order_id)
        ).first()
    if c and c.status == "pending":
        try:
            confirm_contribution(c.id)
            st.success(
                f"Thanks {c.contributor}! ${c.amount:.2f} is on hold. "
                "You are only charged if the goal is reached."
            )
            with SessionLocal() as s:
                pool_obj = s.get(Pool, c.pool_id)
            if pool_obj.status == "open" and pool_total(c.pool_id) >= pool_obj.target_amount:
                ok, why = finalize_pool(c.pool_id)
                if ok:
                    st.balloons()
                    st.success("Goal reached! The agent verified the pool and captured every payment.")
        except Exception as e:
            st.error(f"Could not confirm the payment: {e}")
    if c:
        st.session_state["selected_pool"] = c.pool_id
    st.query_params.clear()
elif "cancelled" in params:
    st.warning("Payment cancelled. Nothing was charged.")
    st.query_params.clear()

st.title("Pool")
st.caption(
    "An AI agent that finds a gift, pools money from friends through PayPal, "
    "and only charges when the goal is met."
)

tab1, tab2 = st.tabs(["Ask the agent", "Pools"])

with tab1:
    request = st.text_area(
        "What do you want to buy together?",
        placeholder="Gift for my friend Priya, a woman who loves hiking, $150 budget",
    )
    if st.button("Find a gift and start a pool", type="primary"):
        if request.strip():
            with st.spinner("The agent is searching and creating a pool..."):
                answer = run_agent(request.strip())
            st.success(answer)
            st.info("Open the Pools tab to share the pool and collect contributions.")
        else:
            st.warning("Tell the agent what you want to buy.")

with tab2:
    pools = all_pools()
    if not pools:
        st.info("No pools yet. Ask the agent to create one.")
    else:
        labels = {p.id: f"#{p.id} {p.title} ({p.status})" for p in pools}
        ids = list(labels)
        default = st.session_state.get("selected_pool")
        index = ids.index(default) if default in ids else 0
        pid = st.selectbox("Choose a pool", ids, index=index, format_func=lambda i: labels[i])
        pool = next(p for p in pools if p.id == pid)
        total = pool_total(pid)
        progress = min(total / pool.target_amount, 1.0) if pool.target_amount else 0.0

        st.subheader(pool.title)
        st.write(f"**Product:** {pool.product_title}")
        if pool.product_url:
            st.markdown(f"[View product]({pool.product_url})")
            st.progress(progress, text=f"\\${total:.2f} held of \\${pool.target_amount:.2f}")
        st.write(f"Deadline: {pool.deadline:%b %d, %Y %I:%M %p} | Status: **{pool.status}**")

        if pool.status == "open":
            with st.form(f"contribute_{pid}"):
                name = st.text_input("Your name")
                remaining = max(pool.target_amount - total, 1.0)
                amount = st.number_input(
                    "Amount (USD)", min_value=1.0, value=float(min(25.0, remaining)), step=1.0
                )
                submit = st.form_submit_button("Contribute with PayPal")
            if submit:
                if not name.strip():
                    st.warning("Please enter your name.")
                else:
                    _, link = start_contribution(
                        pid, name.strip(), float(amount),
                        f"{BASE_URL}/", f"{BASE_URL}/?cancelled=1",
                    )
                    st.link_button("Continue to PayPal (sandbox)", link)
        elif pool.status == "funded":
            st.success("Funded. Every payment was captured.")
        elif pool.status == "expired":
            st.info("The goal was not reached, so every hold was released.")

        with SessionLocal() as s:
            rows = s.scalars(select(Contribution).where(Contribution.pool_id == pid)).all()
        if rows:
            st.markdown("### Contributions")
            st.table([
                {"Name": c.contributor, "Amount": f"${c.amount:.2f}", "Status": c.status}
                for c in rows
            ])

        st.markdown("### Agent activity log")
        for e in list_events(pid):
            st.write(f"`{e.created_at:%H:%M:%S}` **{e.kind}**: {e.detail}")

        with st.expander("Demo controls"):
            st.caption("Ends the pool now, as if the deadline had passed.")
            if st.button("Close this pool now"):
                with SessionLocal() as s:
                    p = s.get(Pool, pid)
                    p.deadline = datetime.now()
                    s.commit()
                check_deadlines()
                st.rerun()