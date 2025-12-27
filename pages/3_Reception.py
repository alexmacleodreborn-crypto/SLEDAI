import streamlit as st
from datetime import datetime
import re
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

st.set_page_config(page_title="Reception", layout="wide")
st.title("🏨 Reception")
st.caption("Allocates rooms • computes ticker couplings • renders network map")

# ==================================================
# STATE SAFETY
# ==================================================
for key in ["rooms_log", "couplings_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ==================================================
# KEYWORD EXTRACTION
# ==================================================
def keywords(text: str):
    words = re.findall(r"[a-zA-Z]{4,}", (text or "").lower())
    stop = {
        "this","that","with","from","have","will","your","into","they","them",
        "when","what","also","just","more","news","scan","sled","price","signal"
    }
    return set(w for w in words if w not in stop)

# ==================================================
# ROOM NORMALISATION (SAFE)
# ==================================================
def normalise_rooms():
    seen = set()
    clean = []

    for r in st.session_state.rooms_log:
        key = r.get("Room_ID") or r.get("Ticker")
        if not key or key in seen:
            continue
        seen.add(key)

        clean.append({
            "Timestamp": r.get("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "Room_ID": r.get("Room_ID", f"RM-{r.get('Ticker','UNK')}"),
            "Ticker": (r.get("Ticker") or "").upper(),
            "Status": r.get("Status", "IN_HOUSE"),
            "Preview": r.get("Preview", ""),
            "_kw": keywords(r.get("Preview",""))
        })

    st.session_state.rooms_log = clean

normalise_rooms()

# ==================================================
# COUPLING DETECTION
# ==================================================
def compute_couplings():
    rooms = st.session_state.rooms_log
    couplings = []

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            A = rooms[i]["_kw"]
            B = rooms[j]["_kw"]
            inter = A & B

            if len(inter) >= 7:
                strength = "FULLY_COUPLED"
            elif len(inter) >= 4:
                strength = "STRONGLY_COUPLED"
            elif len(inter) >= 2:
                strength = "POTENTIAL"
            else:
                continue

            couplings.append({
                "Ticker_A": rooms[i]["Ticker"],
                "Room_A": rooms[i]["Room_ID"],
                "Ticker_B": rooms[j]["Ticker"],
                "Room_B": rooms[j]["Room_ID"],
                "Strength": strength,
                "Overlap": len(inter),
                "Keywords": ", ".join(sorted(list(inter))[:8]),
            })

    return couplings

if st.button("🔄 Recompute Couplings"):
    st.session_state.couplings_log = compute_couplings()
    st.success(f"Computed {len(st.session_state.couplings_log)} couplings.")

st.markdown("---")

# ==================================================
# ROOMS TABLE
# ==================================================
st.subheader("🏨 Rooms In-House")

if st.session_state.rooms_log:
    view = [{k:v for k,v in r.items() if not k.startswith("_")} for r in st.session_state.rooms_log]
    st.dataframe(pd.DataFrame(view), use_container_width=True)
else:
    st.caption("No rooms available.")

# ==================================================
# COUPLINGS TABLE
# ==================================================
st.subheader("🔗 Couplings")

if st.session_state.couplings_log:
    st.dataframe(pd.DataFrame(st.session_state.couplings_log), use_container_width=True)
else:
    st.caption("No couplings computed yet.")

st.markdown("---")

# ==================================================
# NETWORK GRAPH
# ==================================================
st.subheader("🕸 Coupling Network")

if not st.session_state.couplings_log:
    st.caption("No couplings to display.")
else:
    G = nx.Graph()

    rank = {"POTENTIAL":1, "STRONGLY_COUPLED":2, "FULLY_COUPLED":3}

    for c in st.session_state.couplings_log:
        a, b = c["Ticker_A"], c["Ticker_B"]
        w = rank[c["Strength"]]
        if G.has_edge(a, b):
            G[a][b]["weight"] += w
        else:
            G.add_edge(a, b, weight=w)

    pos = nx.spring_layout(G, seed=42, k=0.7)

    deg = dict(G.degree())
    node_sizes = [400 + deg[n]*240 for n in G.nodes()]
    edge_widths = [1.4 + G[u][v]["weight"] for u,v in G.edges()]

    fig, ax = plt.subplots(figsize=(11,7))
    ax.axis("off")

    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, ax=ax)
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.7, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=9, ax=ax)

    ax.set_title("Ticker Coupling Network")
    st.pyplot(fig, use_container_width=True)

st.markdown("---")

if st.button("⬅ Back to Console"):
    st.switch_page("streamlit_app.py")