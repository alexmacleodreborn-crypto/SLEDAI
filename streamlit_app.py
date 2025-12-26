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
st.caption("Autonomous market intelligence • coupling awareness • BUY / SELL overlay")

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
# FULL HOTEL CYCLE
# ==================================================
def run_full_hotel_cycle():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1) SALES — FULL SLED SCAN
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

        entry = {
            "Timestamp": now,
            "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
            "Input_Type": "SALES_SLED_FULL",
            "Status": "ARRIVED",
            "Ticker": t,
            **summary
        }

        st.session_state.sales_last_scan.append(entry)

    # 2) ROOMS (ticker-based)
    st.session_state.rooms_log = [
        {
            "Room_ID": f"RM-{r['Ticker']}",
            "Ticker": r["Ticker"],
            "Preview": f"{r['Signal']} {r['RiseScore_14d']} {r['Gate']}"
        }
        for r in st.session_state.sales_last_scan
    ]

    # 3) COUPLINGS (keyword overlap proxy)
    def kw(s):
        return set(re.findall(r"[A-Za-z]{3,}", (s or "").lower()))

    couplings = []
    rooms = st.session_state.rooms_log

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            A = kw(rooms[i]["Preview"])
            B = kw(rooms[j]["Preview"])
            inter = A & B

            if len(inter) >= 3:
                strength = "FULLY_COUPLED" if len(inter) >= 6 else "STRONGLY_COUPLED"
                couplings.append({
                    "Ticker_A": rooms[i]["Ticker"],
                    "Ticker_B": rooms[j]["Ticker"],
                    "Strength": strength
                })

    st.session_state.couplings_log = couplings

# ==================================================
# MANAGER BUTTON
# ==================================================
if st.button("🚀 RUN FULL CYCLE (A7DO)", type="primary"):
    run_full_hotel_cycle()
    st.success("Cycle complete")

st.markdown("---")

# ==================================================
# HOME COUPLING NETWORK — BUY / SELL OVERLAY
# ==================================================
st.subheader("🕸 Coupling Network — BUY / SELL Radar")

if not st.session_state.sales_last_scan:
    st.caption("Run a cycle to generate BUY / SELL signals.")
else:
    # Build lookup tables
    signal_map = {
        r["Ticker"]: r.get("Signal", "WAIT")
        for r in st.session_state.sales_last_scan
    }

    rise_map = {
        r["Ticker"]: r.get("RiseScore_14d", 0.0)
        for r in st.session_state.sales_last_scan
    }

    strength_rank = {
        "POTENTIAL": 1,
        "STRONGLY_COUPLED": 2,
        "FULLY_COUPLED": 3
    }

    # Build graph
    G = nx.Graph()

    for c in st.session_state.couplings_log:
        a = c["Ticker_A"]
        b = c["Ticker_B"]
        s = c["Strength"]

        w = strength_rank[s]
        G.add_edge(a, b, weight=w)

    # Add isolated nodes (important BUY/SELL even if uncoupled)
    for t in signal_map:
        if t not in G:
            G.add_node(t)

    # Node color by action
    node_colors = []
    node_sizes = []

    for n in G.nodes():
        sig = signal_map.get(n, "WAIT")
        rise = rise_map.get(n, 0.0)
        deg = G.degree(n)

        if sig == "BUY":
            node_colors.append("#00ff66")   # green
        elif sig == "SELL":
            node_colors.append("#ff4444")   # red
        else:
            node_colors.append("#cccccc")   # grey

        node_sizes.append(400 + deg * 250 + abs(rise) * 10)

    pos = nx.spring_layout(G, seed=42, k=0.8)

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.axis("off")

    nx.draw_networkx_nodes(
        G, pos,
        node_color=node_colors,
        node_size=node_sizes,
        ax=ax
    )

    nx.draw_networkx_edges(
        G, pos,
        width=[1.5 + G[u][v]["weight"] for u, v in G.edges()],
        alpha=0.6,
        ax=ax
    )

    nx.draw_networkx_labels(G, pos, font_size=9, ax=ax)

    ax.set_title(
        "BUY (Green) • SELL (Red) • WAIT (Grey)\n"
        "Node size = coupling + rise score"
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