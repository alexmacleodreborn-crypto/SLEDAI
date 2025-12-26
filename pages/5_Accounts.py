import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from sled_core import safe_history

st.set_page_config(page_title="Accounts", layout="wide")
st.title("💰 Accounts — Portfolio (Paper Trading)")
st.caption("Holdings • Average cost • Live price • Unrealized PnL")

# ==================================================
# STATE
# ==================================================
for key in ["portfolio", "trade_log", "sales_last_scan"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ==================================================
# HELPERS
# ==================================================
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

def auto_trade_from_sales():
    """
    Applies paper trades from last SLED scan.
    Only runs when user clicks the button.
    """
    if not st.session_state.sales_last_scan:
        st.warning("No sales scan data available.")
        return

    applied = 0
    for r in st.session_state.sales_last_scan:
        t = r.get("Ticker")
        px = r.get("Price")

        if not t or px is None:
            continue

        if r.get("Bullseye_BUY"):
            upsert(t, qty_delta=10, px=px)
            log_trade("BUY", t, 10, px, "SLED Bullseye BUY")
            applied += 1

        if r.get("Bullseye_SELL"):
            upsert(t, qty_delta=-10, px=px)
            log_trade("SELL", t, -10, px, "SLED Bullseye SELL")
            applied += 1

    st.success(f"Applied {applied} bullseye trade actions.")

# ==================================================
# ACTIONS
# ==================================================
st.subheader("🤖 Automation")

if st.button("Apply Bullseye Trades from Sales Scan"):
    auto_trade_from_sales()

st.markdown("---")

# ==================================================
# MANUAL ENTRY
# ==================================================
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

if st.button("Apply Manual Change"):
    if not t or qty == 0 or px <= 0:
        st.warning("Enter Ticker, non-zero Qty, Price > 0.")
    else:
        upsert(t, qty, px)
        log_trade("BUY" if qty > 0 else "SELL", t, qty, px, reason)
        st.success("Portfolio updated.")

st.markdown("---")

# ==================================================
# PORTFOLIO VIEW
# ==================================================
df = portfolio_df()

if df.empty:
    st.info("No holdings yet.")
else:
    st.subheader("📌 Holdings & PnL")

    prices = [live_price(x) for x in df["Ticker"].tolist()]
    df["Live_Price"] = prices
    df["Market_Value"] = df["Qty"] * df["Live_Price"]
    df["Cost_Basis"] = df["Qty"] * df["Avg_Price"]
    df["Unreal_PnL"] = df["Market_Value"] - df["Cost_Basis"]
    df["Unreal_PnL_%"] = np.where(df["Cost_Basis"] == 0, 0, (df["Unreal_PnL"] / df["Cost_Basis"]) * 100)

    st.dataframe(df, use_container_width=True)

    m1,m2,m3 = st.columns(3)
    m1.metric("Market Value", f"{df['Market_Value'].sum():,.2f}")
    m2.metric("Cost Basis", f"{df['Cost_Basis'].sum():,.2f}")
    m3.metric("Unrealized PnL", f"{df['Unreal_PnL'].sum():,.2f}")

    st.subheader("📊 Portfolio Visuals")
    fig, ax = plt.subplots(figsize=(8,3))
    ax.bar(df["Ticker"], df["Market_Value"])
    ax.set_title("Market Value by Ticker")
    ax.grid(True, alpha=0.2)
    st.pyplot(fig)

st.markdown("---")

# ==================================================
# TRADE LOG
# ==================================================
st.subheader("🧾 Trade Log")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log), use_container_width=True)
else:
    st.caption("No trades logged yet.")

st.markdown("---")
if st.button("⬅ Return to Console"):
    st.switch_page("streamlit_app.py")