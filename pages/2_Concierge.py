import streamlit as st
import uuid
from datetime import datetime

st.set_page_config(page_title="Concierge", layout="wide")
st.title("🛎 Concierge")
st.caption("Classifies inputs • sets action required • issues Room_ID")

for key in ["inputs_log", "concierge_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

def classify(text: str):
    t = (text or "").lower()

    if any(w in t for w in ["buy", "sell", "stock", "share", "ticker", "price"]):
        return "SALES_MARKETING", "ROUTE_TO_SALES"
    if any(w in t for w in ["reply", "respond", "urgent", "asap", "?"]):
        return "REQUIRES_REPLY", "REVIEW"
    if any(w in t for w in ["error", "alert", "system"]):
        return "SYSTEM_SIGNAL", "ESCALATE_MANAGER"
    if len(t.strip()) < 20:
        return "INFORMATION_ONLY", "NONE"
    return "UNKNOWN", "REVIEW"

processed = {c["Transaction_Code"] for c in st.session_state.concierge_log}
new_items = [i for i in st.session_state.inputs_log if i["Transaction_Code"] not in processed]

if st.button("Process New Arrivals"):
    n = 0
    for item in new_items:
        category, action = classify(item["Raw"])
        entry = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Transaction_Code": item["Transaction_Code"],
            "Category": category,
            "Action_Required": action,
            "Room_ID": f"RM-{uuid.uuid4().hex[:8].upper()}",
            "Preview": item["Preview"],
            # carry optional fields if present
            "Ticker": item.get("Ticker", ""),
            "Signal": item.get("Signal", ""),
        }
        st.session_state.concierge_log.insert(0, entry)
        n += 1
    st.success(f"Processed {n} new input(s).")

st.markdown("---")
st.subheader("Concierge Register")
if st.session_state.concierge_log:
    st.dataframe(st.session_state.concierge_log, use_container_width=True)
else:
    st.caption("No concierge entries yet.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")