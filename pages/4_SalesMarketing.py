import streamlit as st
import yfinance as yf
import uuid
from datetime import datetime
from sled_core import SLEDEngine

st.set_page_config(page_title="Sales & Marketing", layout="wide")
st.title("📈 Sales & Marketing")
st.caption("Market scans • SLED intelligence")

engine = SLEDEngine()

# ==================================================
# SAFETY
# ==================================================
for key in ["inputs_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ==================================================
# 10-MIN STOCK SCAN (MANUAL TRIGGER)
# ==================================================
st.subheader("⏱ SLED 10-Min Stock Scan")

tickers = st.text_input(
    "Tickers (comma-separated)",
    "AAPL,MSFT,NVDA"
)

lookback = st.selectbox(
    "Lookback Period",
    ["1mo", "3mo", "6mo"],
    index=1
)

if st.button("Run SLED Scan"):
    results = []

    for t in [x.strip().upper() for x in tickers.split(",")]:
        try:
            df = yf.download(
                t,
                period=lookback,
                progress=False
            )

            signal, metrics = engine.evaluate(df)

            price = df["Close"].iloc[-1]

            content = (
                f"SLED Scan | {t} | Price {price:.2f} | "
                f"Signal {signal} | "
                f"Z {metrics.get('Z_Trap')} | "
                f"Gate {metrics.get('Gate')}"
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
            }

            st.session_state.inputs_log.insert(0, entry)
            results.append(entry)

        except Exception as e:
            st.warning(f"{t}: failed to fetch data")

    if results:
        st.success("SLED scan complete — inputs sent to system")
        st.dataframe(results, use_container_width=True)

# ==================================================
# INDIVIDUAL BUSINESS REPORT
# ==================================================
st.markdown("---")
st.subheader("📄 Individual Business Report")

ticker = st.text_input("Stock ticker (optional)")
report = st.text_area(
    "Business information\n(stores, board, assets, investments)"
)

if st.button("Submit Business Report"):
    content = f"Business report {ticker}: {report}"

    entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
        "Input_Type": "BUSINESS_REPORT",
        "Status": "ARRIVED",
        "Preview": content[:120],
        "Raw": content,
        "Ticker": ticker,
        "Signal": "INFO",
    }

    st.session_state.inputs_log.insert(0, entry)

    st.success("Business report sent into system")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")