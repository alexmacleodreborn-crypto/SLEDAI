import streamlit as st
import uuid
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

from sled_core import safe_history, SLEDEngine

st.set_page_config(page_title="Sales & Marketing", layout="wide")
st.title("📈 Sales & Marketing")
st.caption("Runs SLED scans and submits results into the system flow")

for key in ["inputs_log", "sales_last_scan"]:
    if key not in st.session_state:
        st.session_state[key] = []

engine = SLEDEngine(window=14)

def price_chart(df, title):
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(df.index, df["Close"])
    ax.set_title(title)
    ax.grid(True, alpha=0.2)
    return fig

st.subheader("⏱ SLED Market Scan")
tickers = st.text_input("Tickers (comma-separated)", "AAPL,MSFT,NVDA,SPY")
lookback = st.selectbox("Lookback Period", ["1mo", "3mo", "6mo"], index=1)

if st.button("Run SLED Scan Now"):
    out_rows = []
    for t in [x.strip().upper() for x in tickers.split(",") if x.strip()]:
        df = safe_history(t, lookback)
        if df is None:
            out_rows.append({"Ticker": t, "Status": "NO_DATA"})
            continue

        signal, metrics = engine.evaluate(df)
        price = float(df["Close"].iloc[-1])

        # Build business input for the hotel flow
        content = (
            f"SLED Scan | {t} | Price {price:.2f} | Signal {signal} | "
            f"Z {metrics.get('Z_Trap')} | Gate {metrics.get('Gate')}"
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

        out_rows.append({
            "Ticker": t,
            "Price": metrics.get("Price"),
            "Signal": signal,
            "Z_Trap": metrics.get("Z_Trap"),
            "Gate": metrics.get("Gate"),
        })

    st.session_state.sales_last_scan = out_rows
    st.success("Scan complete. Results injected into Doorman flow.")

    df_out = pd.DataFrame(out_rows)
    st.dataframe(df_out, use_container_width=True)

    # Visual: chart first valid ticker
    first_ok = next((r for r in out_rows if r.get("Signal") and r.get("Signal") != "NO_DATA"), None)
    if first_ok:
        df_chart = safe_history(first_ok["Ticker"], lookback)
        if df_chart is not None:
            st.pyplot(price_chart(df_chart.tail(60), f"{first_ok['Ticker']} Close (last ~60 sessions)"))

st.markdown("---")
st.subheader("📄 Individual Business Report")
ticker = st.text_input("Report ticker (optional)", "").upper().strip()
report = st.text_area("Business info (board, stores, assets, investments, capex, etc.)", height=140)

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
    st.success("Business report injected into flow.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")