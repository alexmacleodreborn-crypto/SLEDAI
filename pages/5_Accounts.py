import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Accounts", layout="wide")
st.title("💰 Accounts — Portfolio (Paper Trading)")
st.caption("Holdings • Average cost • Live price • Unrealized PnL")

# ---------------------------
# State
# ---------------------------
for key in ["portfolio", "trade_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

# Portfolio schema:
# {Ticker, Qty, Avg_Price, Date_Added}

def portfolio_df():
    if not st.session_state.portfolio:
        return pd.DataFrame(columns=["Ticker", "Qty", "Avg_Price", "Date_Added"])
    df = pd.DataFrame(st.session_state.portfolio)
    df["Ticker"] = df["Ticker"].astype(str).str.upper()
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0.0)
    df["Avg_Price"] = pd.to_numeric(df["Avg_Price"], errors="coerce").fillna(0.0)
    return df

def get_live_price(ticker: str):
    try:
        h = yf.download(ticker, period="5d", progress=False)
        if h is None or h.empty:
            return np.nan
        return float(h["Close"].iloc[-1])
    except Exception:
        return np.nan

def upsert_position(ticker: str, qty_delta: float, px: float):
    ticker = ticker.upper().strip()
    df = portfolio_df()

    if ticker in df["Ticker"].values:
        row = df[df["Ticker"] == ticker].iloc[0]
        old_qty = float(row["Qty"])
        old_avg = float(row["Avg_Price"])

        new_qty = old_qty + qty_delta

        if new_qty <= 0:
            # remove position
            df = df[df["Ticker"] != ticker]
        else:
            # weighted average on buys; on sells keep avg unchanged
            if qty_delta > 0:
                new_avg = ((old_qty * old_avg) + (qty_delta * px)) / new_qty
            else:
                new_avg = old_avg

            df.loc[df["Ticker"] == ticker, "Qty"] = new_qty
            df.loc[df["Ticker"] == ticker, "Avg_Price"] = new_avg
    else:
        if qty_delta > 0:
            df = pd.concat([df, pd.DataFrame([{
                "Ticker": ticker,
                "Qty": qty_delta,
                "Avg_Price": px,
                "Date_Added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])], ignore_index=True)

    st.session_state.portfolio = df.to_dict("records")

def log_trade(action: str, ticker: str, qty: float, px: float, reason: str):
    st.session_state.trade_log.insert(0, {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action": action,
        "Ticker": ticker.upper(),
        "Qty": qty,
        "Price": round(float(px), 4),
        "Reason": reason[:120],
    })

# ---------------------------
# Add / Edit position
# ---------------------------
st.subheader("➕ Add / Adjust Position")

c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
with c1:
    t = st.text_input("Ticker", "").upper().strip()
with c2:
    qty = st.number_input("Qty (+buy / -sell)", value=0.0, step=1.0)
with c3:
    px = st.number_input("Price", value=0.0, step=0.01)
with c4:
    reason = st.text_input("Reason", "Manual entry")

if st.button("Apply to Portfolio"):
    if not t or qty == 0 or px <= 0:
        st.warning("Enter Ticker, non-zero Qty, and Price > 0.")
    else:
        upsert_position(t, qty, px)
        log_trade("BUY" if qty > 0 else "SELL", t, qty, px, reason)
        st.success("Portfolio updated.")

st.markdown("---")

# ---------------------------
# Portfolio table + PnL
# ---------------------------
df = portfolio_df()

if df.empty:
    st.info("No holdings yet.")
else:
    st.subheader("📌 Holdings")

    # Live prices
    live_prices = []
    for ticker in df["Ticker"].tolist():
        live_prices.append(get_live_price(ticker))

    df["Live_Price"] = live_prices
    df["Market_Value"] = df["Qty"] * df["Live_Price"]
    df["Cost_Basis"] = df["Qty"] * df["Avg_Price"]
    df["Unreal_PnL"] = df["Market_Value"] - df["Cost_Basis"]
    df["Unreal_PnL_%"] = np.where(df["Cost_Basis"] == 0, 0, (df["Unreal_PnL"] / df["Cost_Basis"]) * 100)

    # Display
    show = df[["Ticker","Qty","Avg_Price","Live_Price","Market_Value","Cost_Basis","Unreal_PnL","Unreal_PnL_%","Date_Added"]]
    st.dataframe(show, use_container_width=True)

    # Summary
    total_mv = float(df["Market_Value"].sum(skipna=True))
    total_cb = float(df["Cost_Basis"].sum(skipna=True))
    total_pnl = float(df["Unreal_PnL"].sum(skipna=True))

    s1, s2, s3 = st.columns(3)
    s1.metric("Market Value", f"{total_mv:,.2f}")
    s2.metric("Cost Basis", f"{total_cb:,.2f}")
    s3.metric("Unrealized PnL", f"{total_pnl:,.2f}")

st.markdown("---")

# ---------------------------
# Trade log
# ---------------------------
st.subheader("🧾 Trade Log")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log), use_container_width=True)
else:
    st.caption("No trades logged yet.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")