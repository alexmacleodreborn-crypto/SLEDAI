import streamlit as st
import pandas as pd

st.set_page_config(page_title="SLEDAI Console", layout="wide")
st.title("🧿 SLEDAI — Manager Console (A7DO)")
st.caption("Controlled flow of stock intelligence")

# Shared state
for key in ["inputs_log", "concierge_log", "rooms_log", "couplings_log", "portfolio", "trade_log", "sales_last_scan"]:
    if key not in st.session_state:
        st.session_state[key] = []

# Nav
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    if st.button("🚪 Doorman"): st.switch_page("pages/1_Doorman.py")
with c2:
    if st.button("🛎 Concierge"): st.switch_page("pages/2_Concierge.py")
with c3:
    if st.button("🏨 Reception"): st.switch_page("pages/3_Reception.py")
with c4:
    if st.button("📈 Sales"): st.switch_page("pages/4_SalesMarketing.py")
with c5:
    if st.button("💰 Accounts"): st.switch_page("pages/5_Accounts.py")

st.markdown("---")

left, mid, right = st.columns(3)

with left:
    st.subheader("📥 Arriving Inputs")
    if st.session_state.inputs_log:
        df = pd.DataFrame(st.session_state.inputs_log)
        st.dataframe(df[["Timestamp", "Transaction_Code", "Input_Type"]].head(30), use_container_width=True)
    else:
        st.caption("No incoming inputs yet.")

with mid:
    st.subheader("🚨 Concierge Alerts")
    alerts = [c for c in st.session_state.concierge_log if c.get("Action_Required", "NONE") != "NONE"]
    if alerts:
        df = pd.DataFrame(alerts)
        st.dataframe(df[["Transaction_Code", "Category", "Action_Required", "Room_ID"]].head(30), use_container_width=True)
    else:
        st.caption("No actions required.")

with right:
    st.subheader("🏨 Inputs In-House")
    if st.session_state.rooms_log:
        df = pd.DataFrame(st.session_state.rooms_log)
        st.dataframe(df[["Room_ID", "Category", "Status", "Source"]].head(30), use_container_width=True)
    else:
        st.caption("No rooms yet.")

st.markdown("---")

cA, cB = st.columns(2)
with cA:
    st.subheader("🔗 Couplings")
    if st.session_state.couplings_log:
        st.dataframe(pd.DataFrame(st.session_state.couplings_log).head(30), use_container_width=True)
    else:
        st.caption("No couplings detected.")

with cB:
    st.subheader("📈 Latest Sales Scan Signals")
    if st.session_state.sales_last_scan:
        st.dataframe(pd.DataFrame(st.session_state.sales_last_scan).head(30), use_container_width=True)
    else:
        st.caption("No sales scan yet.")

from sled_core import SLEDEngine, safe_history
import uuid
from datetime import datetime

engine = SLEDEngine()

def run_full_cycle():
    # 1. SALES SCAN
    st.session_state.sales_last_scan = []
    for t in ["AAPL","MSFT","NVDA","SPY","AMZN","META","TSLA"]:
        df = safe_history(t, "3mo")
        if df is None:
            continue
        signal, metrics = engine.evaluate(df)

        entry = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
            "Input_Type": "SALES_SCAN",
            "Status": "ARRIVED",
            "Preview": f"SLED Scan {t} {signal}",
            "Raw": f"SLED Scan {t}",
            "Ticker": t,
            "Signal": signal,
            **metrics
        }
        st.session_state.inputs_log.insert(0, entry)
        st.session_state.sales_last_scan.append(entry)

    # 2. CONCIERGE
    processed = {c["Transaction_Code"] for c in st.session_state.concierge_log}
    for item in st.session_state.inputs_log:
        if item["Transaction_Code"] in processed:
            continue
        st.session_state.concierge_log.insert(0, {
            "Timestamp": item["Timestamp"],
            "Transaction_Code": item["Transaction_Code"],
            "Category": "SALES_MARKETING",
            "Action_Required": "ROUTE_TO_SALES",
            "Room_ID": f"RM-{uuid.uuid4().hex[:8].upper()}",
            "Preview": item["Preview"],
            "Ticker": item.get("Ticker",""),
            "Signal": item.get("Signal",""),
        })

    # 3. RECEPTION + COUPLING
    existing = {r["Transaction_Code"] for r in st.session_state.rooms_log}
    for c in st.session_state.concierge_log:
        if c["Transaction_Code"] in existing:
            continue
        st.session_state.rooms_log.append({
            "Room_ID": c["Room_ID"],
            "Transaction_Code": c["Transaction_Code"],
            "Category": c["Category"],
            "Status": "IN_HOUSE",
            "Source": "SALES",
            "Ticker": c.get("Ticker",""),
            "Signal": c.get("Signal",""),
            "Preview": c["Preview"]
        })

# Button
if st.button("🚀 RUN FULL CYCLE (A7DO)"):
    run_full_cycle()
    st.success("Full cycle completed.")
    
st.caption("SLEDAI v0.4 • SLED integrated • Portfolio active")