import streamlit as st
import pandas as pd

st.set_page_config(page_title="SLEDAI Console", layout="wide")

st.title("🧿 SLEDAI — Manager Console (A7DO)")
st.caption("Controlled flow of stock intelligence")

# ==================================================
# GLOBAL MEMORY
# ==================================================
for key in ["inputs_log", "concierge_log", "rooms_log", "couplings_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

cnav1, cnav2, cnav3, cnav4 = st.columns(4)
with cnav1:
    if st.button("🚪 Doorman"):
        st.switch_page("pages/1_Doorman.py")
with cnav2:
    if st.button("🛎 Concierge"):
        st.switch_page("pages/2_Concierge.py")
with cnav3:
    if st.button("🏨 Reception"):
        st.switch_page("pages/3_Reception.py")
with cnav4:
    if st.button("💰 Accounts"):
        st.switch_page("pages/5_Accounts.py")

# ==================================================
# DASHBOARD PANELS
# ==================================================
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("📈 Sales & Marketing Signals")
    sales = [r for r in st.session_state.rooms_log if r["Source"] == "SALES"]
    if sales:
        st.dataframe(pd.DataFrame(sales)[["Room_ID","Ticker","Signal"]], use_container_width=True)
    else:
        st.caption("No sales signals yet.")

with c2:
    st.subheader("🏨 Inputs In-House (Rooms)")
    if st.session_state.rooms_log:
        st.dataframe(pd.DataFrame(st.session_state.rooms_log)[["Room_ID","Category","Status"]], use_container_width=True)
    else:
        st.caption("No rooms yet.")

with c3:
    st.subheader("🔗 Active Couplings")
    if st.session_state.couplings_log:
        st.dataframe(pd.DataFrame(st.session_state.couplings_log), use_container_width=True)
    else:
        st.caption("No couplings detected.")

st.subheader("💼 Portfolio Snapshot")
if "portfolio" in st.session_state and st.session_state.portfolio:
    st.dataframe(pd.DataFrame(st.session_state.portfolio), use_container_width=True)
else:
    st.caption("No holdings yet.")
st.markdown("---")
st.caption("SLEDAI v0.3 • Reception & Sales active")