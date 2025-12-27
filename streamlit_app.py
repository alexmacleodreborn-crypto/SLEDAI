import streamlit as st
import uuid
from datetime import datetime
import re

import networkx as nx
import matplotlib.pyplot as plt

from sled_core import safe_history, safe_news, apply_news_filter, SLEDEngine

# ==================================================
# APP CONFIG
# ==================================================
st.set_page_config(page_title="SLEDAI — A7DO Manager", layout="wide", page_icon="🧿")
st.title("🧿 SLEDAI — A7DO MANAGER CONSOLE")
st.caption("SLED scan • relevant news filter • couplings • FINAL BUY/SELL radar")

# ==================================================
# STATE INIT
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
# UNIVERSE
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

    # 1) SALES — SLED SCAN + NEWS FILTER
    st.session_state.sales_last_scan = []
    st.session_state.inputs_log = st.session_state.inputs_log[:2000]  # keep bounded

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

        # Relevant news only
        news_items = safe_news(t, limit=10)
        final_action, news_reason = apply_news_filter(summary["Signal"], news_items)

        # Store in scan
        entry = {
            "Timestamp": now,
            "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
            "Input_Type": "SALES_SLED_FULL",
            "Status": "ARRIVED",
            "Ticker": t,
            **summary,
            "Final_Action": final_action,
            "News_Reason": news_reason,
            "News_Count": len(news_items),
        }
        st.session_state.sales_last_scan.append(entry)

        # Log scan input
        st.session_state.inputs_log.insert(0, {
            "Timestamp": now,
            "Transaction_Code": entry["Transaction_Code"],
            "Input_Type": "SALES_SLED_FULL",
            "Status": "ARRIVED",
            "Ticker": t,
            "Preview": f"SLED {t} | {summary['Signal']} -> {final_action} | Price {summary['Price']} | Gate {summary['Gate']} | Z {summary['Z_Trap']}"[:140],
        })

        # Log news items (only relevant ones)
        for n in news_items[:6]:
            st.session_state.inputs_log.insert(0, {
                "Timestamp": now,
                "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
                "Input_Type": "SALES_NEWS",
                "Status": "ARRIVED",
                "Ticker": t,
                "Sentiment": n.get("sentiment"),
                "Preview": f"NEWS {t} [{n.get('sentiment')}] | {n.get('title','')}"[:140],
            })

    # 2) ROOMS — ticker-centric rooms from sales scan
    st.session_state.rooms_log = []
    for r in st.session_state.sales_last_scan:
        st.session_state.rooms_log.append({
            "Timestamp": now,
            "Room_ID": f"RM-{r['Ticker']}",
            "Ticker": r["Ticker"],
            "Status": "IN_HOUSE",
            # Preview used for coupling keyword overlap
            "Preview": f"{r.get('Final_Action','WAIT')} {r.get('Signal','WAIT')} Gate {r.get('Gate',0)} Z {r.get('Z_Trap',1)} Rise {r.get('RiseScore_14d',0)} News {r.get('News_Reason','')}"
        })

    # 3) COUPLINGS — keyword overlap proxy (stable, cheap)
    def kw(s):
        return set(re.findall(r"[A-Za-z]{4,}", (s or "").lower()))

    couplings = []
    rooms = st.session_state.rooms_log

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            A = kw(rooms[i]["Preview"])
            B = kw(rooms[j]["Preview"])
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
            })

    st.session_state.couplings_log = couplings


# ==================================================
# CONTROLS
# ==================================================
st.subheader("🚀 Autonomous Control")
if st.button("RUN FULL HOTEL CYCLE (A7DO)", type="primary"):
    run_full_hotel_cycle()
    st.success("Cycle complete (SLED + relevant news filter + couplings).")

st.markdown("---")

# ==================================================
# PANELS
# ==================================================
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("📥 Arriving Inputs")
    st.dataframe(st.session_state.inputs_log[:12], use_container_width=True)
with c2:
    st.subheader("🏨 Rooms In-House")
    st.dataframe(st.session_state.rooms_log[:12], use_container_width=True)
with c3:
    st.subheader("🔗 Couplings")
    st.dataframe(st.session_state.couplings_log[:12], use_container_width=True)

st.markdown("---")

# ==================================================
# HOME NETWORK — FINAL BUY/SELL AFTER NEWS FILTER
# ==================================================
st.subheader("🕸 Coupling Network — FINAL BUY/SELL Radar (News filtered)")

if not st.session_state.sales_last_scan:
    st.caption("Run a cycle to generate FINAL actions.")
else:
    # Lookups
    final_map = {r["Ticker"]: r.get("Final_Action", "WAIT") for r in st.session_state.sales_last_scan}
    rise_map = {r["Ticker"]: float(r.get("RiseScore_14d", 0.0) or 0.0) for r in st.session_state.sales_last_scan}

    strength_rank = {"POTENTIAL": 1, "STRONGLY_COUPLED": 2, "FULLY_COUPLED": 3}

    cA, cB = st.columns(2)
    with cA:
        min_strength = st.selectbox("Minimum coupling strength", ["POTENTIAL", "STRONGLY_COUPLED", "FULLY_COUPLED"], index=1)
    with cB:
        max_nodes = st.slider("Max tickers to display", 5, 40, 18, step=1)

    G = nx.Graph()

    # Add edges from couplings_log
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
            G.add_edge(a, b, weight=w)

    # Ensure isolated nodes still show
    for t in final_map.keys():
        if t not in G:
            G.add_node(t)

    # Keep top connected tickers
    deg = dict(G.degree())
    top_nodes = sorted(deg, key=lambda x: deg[x], reverse=True)[:max_nodes]
    G = G.subgraph(top_nodes)

    # Node colors by FINAL action
    node_colors = []
    node_sizes = []
    for n in G.nodes():
        act = (final_map.get(n, "WAIT") or "WAIT").upper()
        rscore = rise_map.get(n, 0.0)
        d = G.degree(n)

        if act == "BUY":
            node_colors.append("#00ff66")
        elif act == "SELL":
            node_colors.append("#ff4444")
        else:
            node_colors.append("#cccccc")

        node_sizes.append(420 + d * 240 + abs(rscore) * 10)

    pos = nx.spring_layout(G, seed=42, k=0.8)

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.axis("off")

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
    nx.draw_networkx_edges(
        G, pos,
        width=[1.3 + G[u][v].get("weight", 1) for u, v in G.edges()],
        alpha=0.65,
        ax=ax
    )
    nx.draw_networkx_labels(G, pos, font_size=9, ax=ax)

    ax.set_title("BUY (Green) • SELL (Red) • WAIT (Grey) — after relevant-news filter")
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