import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SLEDAI Console",
    layout="wide",
)

st.title("🧿 SLEDAI — Manager Console (A7DO)")
st.caption("Controlled flow of stock intelligence")

# ==================================================
# GLOBAL MEMORY
# ==================================================
if "inputs_log" not in st.session_state:
    st.session_state.inputs_log = []

if "concierge_log" not in st.session_state:
    st.session_state.concierge_log = []

# ==================================================
# NAVIGATION
# ==================================================
col1, col2 = st.columns(2)
with col1:
    if st.button("🚪 Doorman"):
        st.switch_page("pages/1_Doorman.py")
with col2:
    if st.button("🛎 Concierge"):
        st.switch_page("pages/2_Concierge.py")

st.markdown("---")

# ==================================================
# DASHBOARD PANELS
# ==================================================
c1, c2, c3 = st.columns(3)

# --------------------------------------------------
# SALES & MARKETING (PLACEHOLDER)
# --------------------------------------------------
with c1:
    st.subheader("📈 Sales & Marketing Report")
    st.info("Awaiting Concierge routing…")
    st.caption("Buy / Sell / Hold signals will appear here")

# --------------------------------------------------
# ARRIVING INPUTS
# --------------------------------------------------
with c2:
    st.subheader("📥 Arriving Inputs")
    if st.session_state.inputs_log:
        df = pd.DataFrame(st.session_state.inputs_log)
        st.dataframe(
            df[["Timestamp", "Transaction_Code", "Input_Type"]],
            use_container_width=True,
        )
    else:
        st.caption("No incoming inputs yet.")

# --------------------------------------------------
# CONCIERGE ALERTS
# --------------------------------------------------
with c3:
    st.subheader("🚨 Concierge Alerts")
    alerts = [
        c for c in st.session_state.concierge_log
        if c["Action_Required"] != "NONE"
    ]

    if alerts:
        df = pd.DataFrame(alerts)
        st.dataframe(
            df[[
                "Transaction_Code",
                "Category",
                "Action_Required",
                "Room_ID"
            ]],
            use_container_width=True,
        )
    else:
        st.caption("No actions required.")

st.markdown("---")
st.caption("SLEDAI v0.2 • Concierge active")