import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from sled_core import safe_history

st.set_page_config(page_title="Accounts", layout="wide")
st.title("💰 Accounts — Portfolio (Paper)")
st.caption("Holdings • Avg cost • Live price • Unrealized PnL + charts")

for key in ["portfolio", "trade_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

def portfolio_df():
    if not st.session_state.portfolio:
        return pd.DataFrame(columns=["Ticker","Qty","Avg_Price","Date_Added"])
    df = pd.DataFrame(st.session_state.portfolio)
    df["Ticker"] = df["Ticker"].astype(str).str.upper()
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0.0)
    df["Avg_Price"] = pd.to_numeric(df["Avg_Price"], errors="coerce").fillna(0.0)
    return df

def live_price(ticker: str):
    df = safe_history(ticker, "1mo")
    if df is None:
        return np.nan
    return float(df["Close"].iloc[-1])
def auto_trade_from_sales():
    if "sales_last_scan" not in st.session_state:
        return

    for r in st.session_state.sales_last_scan:
        t = r["Ticker"]
        price = r["Price"]

        if r.get("Bullseye_BUY"):
            upsert(t, qty_delta=10, px=price)
            log_trade("BUY", t, 10, price, "SLED Bullseye BUY")

        if r.get("Bullseye_SELL"):
            upsert(t, qty_delta=-10, px=price)
            log_trade("SELL", t, -10, price, "SLED Bullseye SELL")
def upsert(ticker: str, qty_delta: float, px: float):
    ticker = ticker.upper().strip()
    df = portfolio_df()

    if ticker in df["Ticker"].values:
        row = df[df["Ticker"] == ticker].iloc[0]
        old_qty = float(row["Qty"])
        old_avg = float(row["Avg_Price"])
        new_qty = old_qty + qty_delta

        if new_qty <= 0:
            df = df[df["Ticker"] != ticker]
        else:
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

def log_trade(action, ticker, qty, px, reason):
    st.session_state.trade_log.insert(0, {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action": action,
        "Ticker": ticker.upper(),
        "Qty": qty,
        "Price": round(float(px), 4),
        "Reason": reason[:120],
    })

# Manual entry
st.subheader("➕ Add / Adjust Position")
a,b,c,d = st.columns([1,1,1,2])
with a:
    t = st.text_input("Ticker", "").upper().strip()
with b:
    qty = st.number_input("Qty (+buy / -sell)", value=0.0, step=1.0)
with c:
    px = st.number_input("Price", value=0.0, step=0.01)
with d:
    reason = st.text_input("Reason", "Manual")

if st.button("Apply"):
    if not t or qty == 0 or px <= 0:
        st.warning("Enter Ticker, non-zero Qty, Price > 0.")
    else:
        upsert(t, qty, px)
        log_trade("BUY" if qty > 0 else "SELL", t, qty, px, reason)
        st.success("Portfolio updated.")

st.markdown("---")

df = portfolio_df()
if df.empty:
    st.info("No holdings yet.")
else:
    st.subheader("📌 Holdings + Live PnL")

    prices = [live_price(x) for x in df["Ticker"].tolist()]
    df["Live_Price"] = prices
    df["Market_Value"] = df["Qty"] * df["Live_Price"]
    df["Cost_Basis"] = df["Qty"] * df["Avg_Price"]
    df["Unreal_PnL"] = df["Market_Value"] - df["Cost_Basis"]
    df["Unreal_PnL_%"] = np.where(df["Cost_Basis"] == 0, 0, (df["Unreal_PnL"] / df["Cost_Basis"]) * 100)

    st.dataframe(df, use_container_width=True)

    total_mv = float(df["Market_Value"].sum(skipna=True))
    total_cb = float(df["Cost_Basis"].sum(skipna=True))
    total_pnl = float(df["Unreal_PnL"].sum(skipna=True))

    m1,m2,m3 = st.columns(3)
    m1.metric("Market Value", f"{total_mv:,.2f}")
    m2.metric("Cost Basis", f"{total_cb:,.2f}")
    m3.metric("Unrealized PnL", f"{total_pnl:,.2f}")

    # Visuals
    st.subheader("📊 Portfolio Visuals")
    fig1, ax1 = plt.subplots(figsize=(7,3))
    ax1.bar(df["Ticker"], df["Market_Value"])
    ax1.set_title("Market Value by Ticker")
    ax1.grid(True, alpha=0.2)
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots(figsize=(7,3))
    ax2.bar(df["Ticker"], df["Unreal_PnL"])
    ax2.set_title("Unrealized PnL by Ticker")
    ax2.grid(True, alpha=0.2)
    st.pyplot(fig2)

st.markdown("---")
st.subheader("🧾 Trade Log")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log), use_container_width=True)
else:
    st.caption("No trades logged yet.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")