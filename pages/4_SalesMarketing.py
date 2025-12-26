import streamlit as st
import yfinance as yf
import uuid
from datetime import datetime

st.set_page_config(page_title="Sales & Marketing", layout="wide")
st.title("📈 Sales & Marketing")
st.caption("Market scans • Business reports")

# ==================================================
# SAFETY
# ==================================================
for key in ["inputs_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ==================================================
# 10-MIN STOCK SCAN (MANUAL TRIGGER)
# ==================================================
st.subheader("⏱ 10-Min Stock Scan")

tickers = st.text_input("Tickers (comma-separated)", "AAPL,MSFT,NVDA")

if st.button("Run Scan"):
    for t in [x.strip().upper() for x in tickers.split(",")]:
        try:
            price = yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
            signal = "WAIT"  # placeholder for SLED

            content = f"10-min scan: {t} price {price:.2f} → {signal}"

            st.session_state.inputs_log.insert(0,{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
                "Input_Type": "SALES_SCAN",
                "Status": "ARRIVED",
                "Preview": content[:120],
                "Raw": content
            })
        except:
            pass

    st.success("Sales scan inputs sent to Doorman flow.")

# ==================================================
# INDIVIDUAL BUSINESS REPORT
# ==================================================
st.markdown("---")
st.subheader("📄 Individual Business Report")

ticker = st.text_input("Stock ticker")
report = st.text_area("Business information (stores, board, assets, investments)")

if st.button("Submit Report"):
    content = f"Business report {ticker}: {report}"

    st.session_state.inputs_log.insert(0,{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Transaction_Code": f"TX-{uuid.uuid4().hex[:10].upper()}",
        "Input_Type": "BUSINESS_REPORT",
        "Status": "ARRIVED",
        "Preview": content[:120],
        "Raw": content
    })

    st.success("Business report sent to Doorman flow.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")