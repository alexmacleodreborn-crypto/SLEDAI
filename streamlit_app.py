import streamlit as st
import uuid
from datetime import datetime
import re

import networkx as nx
import matplotlib.pyplot as plt

from sled_core import safe_history, safe_news, SLEDEngine

# ==================================================
# APP CONFIG
# ==================================================
st.set_page_config(
    page_title="SLEDAI — A7DO Manager",
    layout="wide",
    page_icon="🧿"
)

st.title("🧿 SLEDAI — A7DO MANAGER CONSOLE")
st.caption("Autonomous market intelligence • coupling awareness • SLED execution")

# ==================================================
# GLOBAL STATE INIT
# ==================================================
for key in [
    "inputs_log",
    "concierge_log",
    "rooms_log",
    "couplings_log",
    "sales_last_scan",
    "portfolio",
    "trade_log",
]:
    if key not in st.session_state:
        st.session_state[key] = []

engine = SLEDEngine(window=20, lookback=100, entropy_bins=10)

# ==================================================
# MANAGER UNIVERSE
# ==================================================
UNIVERSE = [
    "AAPL","MSFT","NVDA","AMD","META","GOOGL","AMZN","TSLA","PLTR",
    "JPM","BAC","GS","V","MA",
    "XOM","CVX","COP",
    "JNJ","LLY","PFE",
    "KO","PEP","WMT","COST",
    "CAT","BA","GE",
    "SPY","QQQ","DIA"
]

# ==================================================
# CORE PIPELINE (FULL HOTEL CYCLE)
# ==================================================
def run_full_hotel_cycle():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------
    # 1) SALES — FULL SLED SCAN
    # ------------------------------
    st.session_state.sales_last_scan = []

    for t in UNIVERSE:
        df = safe_history(t, "6mo")
        if df is None:
            continue

        dfp = engine.calculate(df)
        if dfp is None:
            continue

        summary = engine.summarize(dfp)
        if not summary:
            continue

        content = (
            f"SLED | {t} | Price {summary['Price']} | "
            f"Signal {summary['Signal']} | Rise {summary['RiseScore_14d']} | "
            f"Gate {summary['Gate']} | Z {summary['Z_Trap']}"
        )

        entry = {
            "Timestamp": now,
            "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
            "Input_Type": "SALES_SLED_FULL",
            "Status": "ARRIVED",
            "Ticker": t,
            "Preview": content[:120],
            "Raw": content,
            **summary
        }

        st.session_state.inputs_log.insert(0, entry)
        st.session_state.sales_last_scan.append(entry)

    # ------------------------------
    # 2) CONCIERGE — ROUTE
    # ------------------------------
    processed = {c["Transaction_Code"] for c in st.session_state.concierge_log}
    for item in st.session_state.inputs_log:
        if item["Transaction_Code"] in processed:
            continue

        st.session_state.concierge_log.insert(0, {
            "Timestamp": item["Timestamp"],
            "Transaction_Code": item["Transaction_Code"],
            "Ticker": item.get("Ticker",""),
            "Category": "SALES_MARKETING",
            "Action_Required": "ROUTE_TO_RECEPTION",
            "Room_ID": f"RM-{uuid.uuid4().hex[:8].upper()}",
            "Preview": item["Preview"],
            "Signal": item.get("Signal",""),
        })

    # ------------------------------
    # 3) RECEPTION — ROOMS
    # ------------------------------
    existing = {r["Transaction_Code"] for r in st.session_state.rooms_log}
    for c in st.session_state.concierge_log:
        if c["Transaction_Code"] in existing:
            continue

        st.session_state.rooms_log.append({
            "Timestamp": now,
            "Room_ID": c["Room_ID"],
            "Transaction_Code": c["Transaction_Code"],
            "Ticker": c.get("Ticker",""),
            "Category": c["Category"],
            "Status": "IN_HOUSE",
            "Preview": c["Preview"],
        })

    # ------------------------------
    # 4) COUPLINGS (KEYWORD OVERLAP)
    # ------------------------------
    def kw(s):
        return set(re.findall(r"[a-zA-Z]{4,}", (s or "").lower()))

    couplings = []
    rooms = st.session_state.rooms_log

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            A = kw(rooms[i].get("Preview",""))
            B = kw(rooms[j].get("Preview",""))
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
                "Ticker_A": rooms[i].get("Ticker",""),
                "Room_A": rooms[i]["Room_ID"],
                "Ticker_B": rooms[j].get("Ticker",""),
                "Room_B": rooms[j]["Room_ID"],
                "Strength": strength,
                "Overlap": len(inter),
            })

    st.session_state.couplings_log = couplings

    # ------------------------------
    # 5) SALES — NEWS FOR IN-HOUSE
    # ------------------------------
    tickers_in_house = sorted({r.get("Ticker","") for r in rooms if r.get("Ticker","")})
    for t in tickers_in_house:
        news = safe_news(t, limit=5)
        if not news:
            continue

        headlines = " | ".join([n["title"] for n in news if n.get("title")][:4])
        entry = {
            "Timestamp": now,
            "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
            "Input_Type": "SALES_NEWS",
            "Status": "ARRIVED",
            "Ticker": t,
            "Preview": f"NEWS | {t} | {headlines}"[:120],
            "Raw": headlines
        }
        st.session_state.inputs_log.insert(0, entry)

# ==================================================
# MANAGER CONTROLS
# ==================================================
st.subheader("🚀 Autonomous Control")

if st.button("RUN FULL HOTEL CYCLE (A7DO)", type="primary"):
    run_full_hotel_cycle()
    st.success("Full autonomous cycle completed.")

st.markdown("---")

# ==================================================
# DASHBOARD PANELS
# ==================================================
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("📥 Arriving Inputs")
    st.dataframe(st.session_state.inputs_log[:10], use_container_width=True)

with c2:
    st.subheader("🏨 Rooms In-House")
    st.dataframe(st.session_state.rooms_log[:10], use_container_width=True)

with c3:
    st.subheader("🔗 Couplings")
    st.dataframe(st.session_state.couplings_log[:10], use_container_width=True)

st.markdown("---")

# ==================================================
# HOME COUPLING NETWORK MAP (TICKER VIEW)
# ==================================================
st.subheader("🕸 Live Coupling Network (Tickers)")

if not st.session_state.couplings_log:
    st.caption("No couplings yet. Run a cycle first.")
else:
    strength_rank = {
        "POTENTIAL": 1,
        "STRONGLY_COUPLED": 2,
        "FULLY_COUPLED": 3
    }

    cA, cB = st.columns(2)
    with cA:
        min_strength = st.selectbox(
            "Minimum coupling strength",
            list(strength_rank.keys()),
            index=1
        )
    with cB:
        max_nodes = st.slider(
            "Max tickers to display",
            5, 30, 15, step=5
        )

    G = nx.Graph()

    for c in st.session_state.couplings_log:
        s = (c.get("Strength") or "").upper()
        if strength_rank.get(s, 0) < strength_rank[min_strength]:
            continue

        a = (c.get("Ticker_A") or "").strip()
        b = (c.get("Ticker_B") or "").strip()
        if not a or not b or a == b:
            continue

        w = strength_rank[s]

        if G.has_edge(a, b):
            G[a][b]["weight"] += w
        else:
            G.add_edge(a, b, weight=w, strength=s)

    if G.number_of_nodes() == 0:
        st.warning("No couplings meet selected strength.")
    else:
        deg = dict(G.degree())
        top_nodes = sorted(deg, key=lambda x: deg[x], reverse=True)[:max_nodes]
        G = G.subgraph(top_nodes)

        pos = nx.spring_layout(G, seed=42, k=0.7)

        node_sizes = [300 + deg.get(n, 1) * 220 for n in G.nodes()]
        edge_widths = [1.2 + G[u][v]["weight"] * 0.9 for u, v in G.edges()]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axis("off")

        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, ax=ax)
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.7, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=9, ax=ax)

        ax.set_title(
            f"Ticker Couplings • Min: {min_strength} • "
            f"Tickers: {G.number_of_nodes()} • Links: {G.number_of_edges()}"
        )

        st.pyplot(fig, use_container_width=True)

st.markdown("---")

# ==================================================
# NAVIGATION
# ==================================================
nav1, nav2, nav3, nav4, nav5 = st.columns(5)

with nav1:
    if st.button("🚪 Doorman"):
        st.switch_page("pages/1_Doorman.py")
with nav2:
    if st.button("🛎 Concierge"):
        st.switch_page("pages/2_Concierge.py")
with nav3:
    if st.button("🏨 Reception"):
        st.switch_page("pages/3_Reception.py")
with nav4:
    if st.button("📈 Sales"):
        st.switch_page("pages/4_SalesMarketing.py")
with nav5:
    if st.button("💰 Accounts"):
        st.switch_page("pages/5_Accounts.py")