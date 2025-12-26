import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SLEDAI Console",
    layout="wide",
)

st.title("🧿 SLEDAI — Manager Console (A7DO)")
st.caption("Controlled flow of stock intelligence")

# ==================================================
# SESSION STATE (GLOBAL MEMORY)
# ==================================================
if "inputs_log" not in st.session_state:
    st.session_state.inputs_log = []

# ==================================================
# NAV
# ==================================================
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🚪 Doorman"):
        st.switch_page("pages/1_Doorman.py")

st.markdown("---")

# ==================================================
# CONSOLE LAYOUT
# ==================================================
c1, c2, c3 = st.columns(3)

# --------------------------------------------------
# SALES & MARKETING REPORT (PLACEHOLDER)
# --------------------------------------------------
with c1:
    st.subheader("📈 Sales & Marketing Report")
    st.info("Awaiting 10-minute research cycles…")
    st.markdown("""
    - Buy signals: —
    - Sell signals: —
    - Hold / Trapped: —
    """)

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
# INPUTS IN HOUSE
# --------------------------------------------------
with c3:
    st.subheader("🏨 Inputs In-House")
    if st.session_state.inputs_log:
        df = pd.DataFrame(st.session_state.inputs_log)
        st.dataframe(
            df[["Transaction_Code", "Status", "Preview"]],
            use_container_width=True,
        )
    else:
        st.caption("No active inputs.")

st.markdown("---")
st.caption("SLEDAI v0.1 • System online")