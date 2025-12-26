import streamlit as st
import uuid
from datetime import datetime
import pandas as pd

from sled_core import safe_history, SLEDEngine

st.set_page_config(page_title="Sales & Marketing", layout="wide")
st.title("📈 Sales & Marketing — SLED")
st.caption("Market scans • SLED intelligence • Signal injection")

# ==================================================
# STATE
# ==================================================
for key in ["inputs_log", "sales_last_scan"]:
    if key not in st.session_state:
        st.session_state[key] = []

engine = SLEDEngine()

# ==================================================
# STOCK UNIVERSE (SAFE + EDITABLE)
# ==================================================
DEFAULT_UNIVERSE = [
    # Tech
    "AAPL","MSFT","NVDA","AMD","META","GOOGL","AMZN","TSLA",
    # Finance
    "JPM","BAC","GS","MS","V",
    # Energy
    "XOM","CVX","COP",
    # Healthcare
    "JNJ","PFE","LLY",
    # Consumer
    "KO","PEP","WMT","COST",
    # Index / Macro
    "SPY","QQQ","DIA"
]

st.subheader("📦 Stock Universe")

universe_text = st.text_area(
    "Edit universe (comma-separated tickers)",
    ", ".join(DEFAULT_UNIVERSE),
    height=80
)

UNIVERSE = [t.strip().upper() for t in universe_text.split(",") if t.strip()]

st.caption(f"{len(UNIVERSE)} instruments loaded")

# ==================================================
# SCAN CONTROLS
# ==================================================
st.subheader("⏱ SLED Market Scan")

lookback = st.selectbox(
    "Lookback period",
    ["1mo", "3mo", "6mo"],
    index=1
)

run = st.button("🚀 Run SLED Scan")

# ==================================================
# RUN SCAN
# ==================================================
if run:
    results = []

    for t in UNIVERSE:
        df = safe_history(t, lookback)
        if df is None:
            results.append({
                "Ticker": t,
                "Status": "NO_DATA"
            })
            continue

        signal, metrics = engine.evaluate(df)

        content = (
            f"SLED Scan | {t} | Price {metrics['Price']} | "
            f"Signal {signal} | Z {metrics['Z_Trap']} | Gate {metrics['Gate']}"
        )

        entry = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
            "Input_Type": "SALES_SCAN",
            "Status": "ARRIVED",
            "Preview": content[:120],
            "Raw": content,
            "Ticker": t,
            "Signal": signal,
            **metrics,
        }

        # Inject into hotel flow
        st.session_state.inputs_log.insert(0, entry)
        results.append(entry)

    st.session_state.sales_last_scan = results

    st.success(f"SLED scan complete — {len(results)} instruments processed")

    # ==================================================
    # DISPLAY RESULTS
    # ==================================================
    df_out = pd.DataFrame(results)

    if not df_out.empty:
        cols = [
            c for c in [
                "Ticker","Signal","Price","Z_Trap","Gate",
                "Bullseye_BUY","Bullseye_SELL","Status"
            ]
            if c in df_out.columns
        ]
        st.dataframe(df_out[cols], use_container_width=True)
    else:
        st.info("No results returned.")

# ==================================================
# NAV
# ==================================================
st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")