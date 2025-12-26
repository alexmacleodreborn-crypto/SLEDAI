import streamlit as st
import uuid
from datetime import datetime

st.set_page_config(
    page_title="Concierge",
    layout="wide",
)

st.title("🛎 Concierge")
st.caption("Input classification • Routing • Alerts")

# ==================================================
# SAFETY
# ==================================================
if "inputs_log" not in st.session_state:
    st.session_state.inputs_log = []

if "concierge_log" not in st.session_state:
    st.session_state.concierge_log = []

# ==================================================
# CLASSIFICATION LOGIC
# ==================================================
def classify_input(text: str):
    t = text.lower()

    if any(w in t for w in ["buy", "sell", "stock", "share", "price"]):
        return "SALES_MARKETING", "ROUTE_TO_SALES"

    if any(w in t for w in ["help", "reply", "question", "?"]):
        return "REQUIRES_REPLY", "REVIEW"

    if any(w in t for w in ["system", "error", "alert"]):
        return "SYSTEM_SIGNAL", "ESCALATE_MANAGER"

    if len(t.strip()) < 20:
        return "INFORMATION_ONLY", "NONE"

    return "UNKNOWN", "REVIEW"

# ==================================================
# PROCESS NEW INPUTS
# ==================================================
processed_ids = {c["Transaction_Code"] for c in st.session_state.concierge_log}

new_items = [
    i for i in st.session_state.inputs_log
    if i["Transaction_Code"] not in processed_ids
]

if not new_items:
    st.info("No new inputs to process.")
else:
    for item in new_items:
        category, action = classify_input(item["Raw"])

        room_id = f"RM-{uuid.uuid4().hex[:8].upper()}"

        entry = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Transaction_Code": item["Transaction_Code"],
            "Category": category,
            "Action_Required": action,
            "Room_ID": room_id,
            "Preview": item["Preview"],
        }

        st.session_state.concierge_log.insert(0, entry)

    st.success(f"Processed {len(new_items)} new input(s).")

# ==================================================
# DISPLAY FULL CONCIERGE LOG
# ==================================================
st.markdown("---")
st.subheader("📋 Concierge Register")

if st.session_state.concierge_log:
    df = st.session_state.concierge_log
    st.dataframe(df, use_container_width=True)
else:
    st.caption("No entries yet.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")