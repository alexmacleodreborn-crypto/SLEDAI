import streamlit as st
import uuid
from datetime import datetime
import pandas as pd

from sled_core import safe_history, safe_news, SLEDEngine

st.set_page_config(page_title="Sales & Marketing", layout="wide")
st.title("📈 Sales & Marketing — Full SLED + News")
st.caption("Scans market + pulls relevant news per ticker/room")

for key in ["inputs_log", "sales_last_scan", "rooms_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

engine = SLEDEngine(window=20, lookback=100, entropy_bins=10)

DEFAULT_UNIVERSE = [
    # Tech
    "AAPL","MSFT","NVDA","AMD","META","GOOGL","AMZN","TSLA","PLTR",
    # Finance
    "JPM","BAC","GS","MS","V","MA",
    # Energy
    "XOM","CVX","COP","SHEL","BP",
    # Healthcare
    "JNJ","PFE","LLY","MRK",
    # Consumer
    "KO","PEP","WMT","COST","NKE",
    # Industrials
    "CAT","BA","GE",
    # Index/Macro
    "SPY","QQQ","DIA"
]

st.subheader("📦 Universe")
universe_text = st.text_area("Tickers (comma-separated)", ", ".join(DEFAULT_UNIVERSE), height=70)
UNIVERSE = [t.strip().upper() for t in universe_text.split(",") if t.strip()]

lookback = st.selectbox("Lookback", ["1mo","3mo","6mo"], index=2)

c1, c2 = st.columns(2)
with c1:
    run_scan = st.button("🚀 Run Full SLED Scan")
with c2:
    run_news = st.button("📰 Pull News for In-House Rooms")

if run_scan:
    results = []
    for t in UNIVERSE:
        df = safe_history(t, lookback)
        if df is None:
            continue

        dfp = engine.calculate(df)
        if dfp is None:
            continue

        summary = engine.summarize(dfp)
        if not summary:
            continue

        content = (
            f"SLED Full | {t} | Price {summary['Price']} | "
            f"Signal {summary['Signal']} | RiseScore {summary['RiseScore_14d']} | "
            f"Z {summary['Z_Trap']} | Sigma {summary['Sigma']} | Gate {summary['Gate']}"
        )

        entry = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
            "Input_Type": "SALES_SLED_FULL",
            "Status": "ARRIVED",
            "Ticker": t,
            "Preview": content[:120],
            "Raw": content,
            **summary
        }

        st.session_state.inputs_log.insert(0, entry)
        results.append(entry)

    st.session_state.sales_last_scan = results

    st.success(f"Full scan complete: {len(results)} tickers")
    df_out = pd.DataFrame(results).sort_values("RiseScore_14d", ascending=False)
    st.dataframe(
        df_out[["Ticker","Signal","Price","RiseScore_14d","Gate","Sigma","Z_Trap","Bullseye_BUY","Bullseye_SELL"]],
        use_container_width=True
    )

if run_news:
    # Drive searches from “rooms in house” to stay relevant
    tickers_in_house = sorted(list({r.get("Ticker","") for r in st.session_state.rooms_log if r.get("Ticker","")}))
    if not tickers_in_house:
        st.warning("No in-house rooms/tickers yet. Allocate rooms first.")
    else:
        injected = 0
        for t in tickers_in_house:
            items = safe_news(t, limit=6)
            if not items:
                continue

            # Turn news into a structured business input
            headlines = " | ".join([x["title"] for x in items if x.get("title")][:4])
            content = f"NEWS | {t} | {headlines}"

            entry = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
                "Input_Type": "SALES_NEWS",
                "Status": "ARRIVED",
                "Ticker": t,
                "Preview": content[:120],
                "Raw": content
            }
            st.session_state.inputs_log.insert(0, entry)
            injected += 1

        st.success(f"Injected news inputs: {injected}")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")