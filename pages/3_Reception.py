import streamlit as st
from datetime import datetime
import re
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

st.set_page_config(page_title="Reception", layout="wide")
st.title("🏨 Reception")
st.caption("Allocates rooms • computes ticker couplings • renders a network map")

for key in ["concierge_log", "rooms_log", "couplings_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ---------------------------
# Keyword extraction
# ---------------------------
def keywords(s: str):
    words = re.findall(r"[a-zA-Z]{4,}", (s or "").lower())
    stop = {
        "this","that","with","from","have","will","your","into","they","them",
        "when","what","also","just","more","news","scan","sled","price","signal"
    }
    return set(w for w in words if w not in stop)

# ---------------------------
# Allocate Rooms
# ---------------------------
existing = {r["Transaction_Code"] for r in st.session_state.rooms_log}
new_items = [c for c in st.session_state.concierge_log if c["Transaction_Code"] not in existing]

if st.button("Allocate New Rooms"):
    for item in new_items:
        st.session_state.rooms_log.insert(0, {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Room_ID": item["Room_ID"],
            "Transaction_Code": item["Transaction_Code"],
            "Ticker": (item.get("Ticker","") or "").upper().strip(),
            "Category": item.get("Category",""),
            "Status": "IN_HOUSE",
            "Source": "SALES" if item.get("Category") == "SALES_MARKETING" else "EXTERNAL",
            "Preview": (item.get("Preview","") or "")[:180],
            "_kw": keywords(item.get("Preview","") or ""),
        })
    st.success(f"Allocated {len(new_items)} room(s).")

# ---------------------------
# Coupling detection
# ---------------------------
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

# ---------------------------
# Rooms Table
# ---------------------------
st.subheader("Rooms In-House")
if st.session_state.rooms_log:
    view = [{k:v for k,v in r.items() if k != "_kw"} for r in st.session_state.rooms_log]
    st.dataframe(pd.DataFrame(view), use_container_width=True)
else:
    st.caption("No rooms yet.")

st.subheader("Couplings Table")
if st.session_state.couplings_log:
    st.dataframe(pd.DataFrame(st.session_state.couplings_log), use_container_width=True)
else:
    st.caption("No couplings yet.")

st.markdown("---")

# ==================================================
# NETWORK VISUALISATION
# ==================================================
st.subheader("🕸 Coupling Network Map")

mode = st.radio("Graph Mode", ["Ticker Graph", "Room Graph"], horizontal=True)
min_strength = st.selectbox("Minimum Strength", ["POTENTIAL", "STRONGLY_COUPLED", "FULLY_COUPLED"], index=1)

strength_rank = {"POTENTIAL": 1, "STRONGLY_COUPLED": 2, "FULLY_COUPLED": 3}
min_rank = strength_rank[min_strength]

def coupling_weight(s):
    s = (s or "").upper()
    if s == "FULLY_COUPLED":
        return 3.0
    if s == "STRONGLY_COUPLED":
        return 2.0
    return 1.0

def draw_graph():
    data = st.session_state.couplings_log or []
    if not data:
        st.info("No couplings to plot yet. Allocate rooms and recompute couplings.")
        return

    G = nx.Graph()

    # Build nodes/edges
    for c in data:
        s = (c.get("Strength") or "").upper()
        if strength_rank.get(s, 0) < min_rank:
            continue

        if mode == "Ticker Graph":
            a = (c.get("Ticker_A") or "").strip() or c.get("Room_A")
            b = (c.get("Ticker_B") or "").strip() or c.get("Room_B")
        else:
            a = c.get("Room_A")
            b = c.get("Room_B")

        if not a or not b:
            continue

        w = coupling_weight(s)
        G.add_node(a)
        G.add_node(b)

        # If edge exists, accumulate weight
        if G.has_edge(a, b):
            G[a][b]["weight"] += w
            # keep strongest label for display
            if strength_rank[s] > strength_rank.get(G[a][b].get("strength","POTENTIAL"), 1):
                G[a][b]["strength"] = s
        else:
            G.add_edge(a, b, weight=w, strength=s)

    if G.number_of_nodes() == 0:
        st.warning("No edges match the selected minimum strength.")
        return

    # Layout
    pos = nx.spring_layout(G, seed=7, k=0.6)

    # Size nodes by degree
    degrees = dict(G.degree())
    node_sizes = [300 + degrees[n]*220 for n in G.nodes()]

    # Edge widths by weight
    edge_widths = [1.0 + (G[u][v]["weight"] * 0.8) for u, v in G.edges()]

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.axis("off")

    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, ax=ax)
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.7, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=9, ax=ax)

    ax.set_title(f"{mode} • Min Strength: {min_strength} • Nodes: {G.number_of_nodes()} • Edges: {G.number_of_edges()}")
    st.pyplot(fig, use_container_width=True)

draw_graph()

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")