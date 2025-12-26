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

st.caption("SLEDAI v0.4 • SLED integrated • Portfolio active")