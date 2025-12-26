import streamlit as st
import uuid
from datetime import datetime

st.set_page_config(page_title="Reception", layout="wide")
st.title("🏨 Reception")
st.caption("Room allocation • In-house state • Coupling detection")

# ==================================================
# SAFETY
# ==================================================
for key in ["inputs_log", "concierge_log", "rooms_log", "couplings_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ==================================================
# ROOM ALLOCATION
# ==================================================
existing_rooms = {r["Transaction_Code"] for r in st.session_state.rooms_log}

new_items = [
    c for c in st.session_state.concierge_log
    if c["Transaction_Code"] not in existing_rooms
]

for item in new_items:
    room = {
        "Room_ID": f"ROOM-{uuid.uuid4().hex[:6].upper()}",
        "Transaction_Code": item["Transaction_Code"],
        "Category": item["Category"],
        "Status": "IN_HOUSE",
        "Source": "EXTERNAL",
        "Ticker": item.get("Ticker",""),
        "Signal": item.get("Signal",""),
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Keywords": set(item["Preview"].lower().split())
    }
    st.session_state.rooms_log.append(room)

# ==================================================
# COUPLING DETECTION
# ==================================================
def detect_couplings():
    rooms = st.session_state.rooms_log
    couplings = []

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            a = rooms[i]
            b = rooms[j]
            overlap = a["Keywords"].intersection(b["Keywords"])

            if len(overlap) >= 4:
                couplings.append({
                    "Room_A": a["Room_ID"],
                    "Room_B": b["Room_ID"],
                    "Strength": "STRONG" if len(overlap) >= 7 else "POTENTIAL",
                    "Keywords": ", ".join(list(overlap)[:8])
                })
    return couplings

st.session_state.couplings_log = detect_couplings()

# ==================================================
# DISPLAY
# ==================================================
st.subheader("🏨 Rooms In-House")
if st.session_state.rooms_log:
    st.dataframe(st.session_state.rooms_log, use_container_width=True)
else:
    st.caption("No rooms allocated yet.")

st.markdown("---")
st.subheader("🔗 Couplings")
if st.session_state.couplings_log:
    st.dataframe(st.session_state.couplings_log, use_container_width=True)
else:
    st.caption("No couplings found.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")