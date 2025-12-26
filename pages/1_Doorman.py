import streamlit as st
import uuid
from datetime import datetime

st.set_page_config(page_title="Doorman", layout="wide")
st.title("🚪 Doorman")
st.caption("All inputs require a Ticker/ID for room allocation & coupling")

if "inputs_log" not in st.session_state:
    st.session_state.inputs_log = []

ticker = st.text_input("Ticker/ID (required)", "").upper().strip()
text_input = st.text_area("Text Input", height=160)
file_input = st.file_uploader("Attach File (optional)", type=["txt", "md"])

if st.button("Process Input"):
    if not ticker:
        st.error("Ticker/ID is required.")
    elif not text_input and not file_input:
        st.warning("No input provided.")
    else:
        tx_code = f"TX-{uuid.uuid4().hex[:10].upper()}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        input_type = "TEXT"
        content = text_input or ""

        if file_input:
            input_type = "FILE"
            content += "\n" + file_input.read().decode("utf-8", errors="ignore")

        entry = {
            "Timestamp": timestamp,
            "Transaction_Code": tx_code,
            "Input_Type": input_type,
            "Status": "ARRIVED",
            "Ticker": ticker,
            "Preview": content[:120],
            "Raw": content,
        }
        st.session_state.inputs_log.insert(0, entry)
        st.success("Input accepted")
        st.code(tx_code)

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")