import streamlit as st
import uuid
from datetime import datetime
import pandas as pd

from sled_core import safe_history, SLEDEngine

st.set_page_config(page_title="Sales & Marketing", layout="wide")
st.title("📈 Sales & Marketing — SLED")

for key in ["inputs_log", "sales_last_scan"]:
    if key not in st.session_state:
        st.session_state[key] = []

engine = SLEDEngine()

st.subheader("⏱ Market Scan (Expanded Universe)")
lookback = st.selectbox("Lookback", ["1mo","3mo","6mo"], index=1)

if st.button("Run Sales Scan"):
    out = []

    for t in UNIVERSE:
        df = safe_history(t, lookback)
        if df is None:
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
            **metrics
        }

        st.session_state.inputs_log.insert(0, entry)
        out.append(entry)

    st.session_state.sales_last_scan = out
    st.success(f"Scan complete: {len(out)} instruments")

    st.dataframe(
        pd.DataFrame(out)[
            ["Ticker","Signal","Price","Z_Trap","Gate","Bullseye_BUY","Bullseye_SELL"]
        ],
        use_container_width=True
    )

if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")