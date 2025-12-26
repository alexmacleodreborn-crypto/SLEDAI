import streamlit as st
import uuid
from datetime import datetime

st.set_page_config(page_title="Doorman", layout="wide")
st.title("🚪 Doorman")
st.caption("Passive intake • Transaction tagging • No interruption")

if "inputs_log" not in st.session_state:
    st.session_state.inputs_log = []

text_input = st.text_area("Text Input", height=160)
file_input = st.file_uploader("Attach File (optional)", type=["txt", "md"])

if st.button("Process Input"):
    if not text_input and not file_input:
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
            "Preview": content[:120],
            "Raw": content,
        }
        st.session_state.inputs_log.insert(0, entry)
        st.success("Input accepted")
        st.code(tx_code)

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")