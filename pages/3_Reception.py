import streamlit as st
from datetime import datetime
import re

st.set_page_config(page_title="Reception", layout="wide")
st.title("🏨 Reception")
st.caption("Rooms are ticker-based. Couplings connect rooms by overlap.")

for key in ["concierge_log", "rooms_log", "couplings_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

def keywords(s: str):
    words = re.findall(r"[a-zA-Z]{4,}", (s or "").lower())
    stop = {"this","that","with","from","have","will","your","into","they","them","when","what","also","just","more"}
    return set(w for w in words if w not in stop)

existing = {r["Transaction_Code"] for r in st.session_state.rooms_log}
new_items = [c for c in st.session_state.concierge_log if c["Transaction_Code"] not in existing]

if st.button("Allocate New Rooms"):
    for item in new_items:
        st.session_state.rooms_log.insert(0, {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Room_ID": item["Room_ID"],
            "Transaction_Code": item["Transaction_Code"],
            "Ticker": item.get("Ticker",""),
            "Category": item["Category"],
            "Status": "IN_HOUSE",
            "Source": "SALES" if item["Category"] == "SALES_MARKETING" else "EXTERNAL",
            "Preview": item.get("Preview","")[:120],
            "_kw": keywords(item.get("Preview","")),
        })
    st.success(f"Allocated {len(new_items)} room(s).")

def build_couplings():
    rooms = st.session_state.rooms_log
    couplings = []
    for i in range(len(rooms)):
        for j in range(i+1, len(rooms)):
            A = rooms[i].get("_kw", set())
            B = rooms[j].get("_kw", set())
            inter = A.intersection(B)

            if len(inter) >= 7:
                strength = "FULLY_COUPLED"
            elif len(inter) >= 4:
                strength = "STRONGLY_COUPLED"
            elif len(inter) >= 2:
                strength = "POTENTIAL"
            else:
                continue

            couplings.append({
                "Ticker_A": rooms[i].get("Ticker",""),
                "Room_A": rooms[i]["Room_ID"],
                "Ticker_B": rooms[j].get("Ticker",""),
                "Room_B": rooms[j]["Room_ID"],
                "Strength": strength,
                "Overlap": len(inter),
                "Keywords": ", ".join(sorted(list(inter))[:10]),
            })
    return couplings

if st.button("Recompute Couplings"):
    st.session_state.couplings_log = build_couplings()
    st.success(f"Couplings found: {len(st.session_state.couplings_log)}")

st.markdown("---")
st.subheader("Rooms In-House")
if st.session_state.rooms_log:
    view = [{k:v for k,v in r.items() if k != "_kw"} for r in st.session_state.rooms_log]
    st.dataframe(view, use_container_width=True)
else:
    st.caption("No rooms yet.")

st.subheader("Couplings")
if st.session_state.couplings_log:
    st.dataframe(st.session_state.couplings_log, use_container_width=True)
else:
    st.caption("No couplings yet.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")