import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from sled_core import safe_history

st.set_page_config(page_title="Accounts", layout="wide")
st.title("💰 Accounts — Portfolio (Paper + Coupling + SLED)")
st.caption("Acts on: Bullseye OR Strong Coupling • Direction from SLED Signal + RiseScore")

# ==================================================
# STATE
# ==================================================
for key in ["portfolio", "trade_log", "sales_last_scan", "couplings_log", "inputs_log", "rooms_log"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ==================================================
# PORTFOLIO HELPERS
# ==================================================
def portfolio_df():
    if not st.session_state.portfolio:
        return pd.DataFrame(columns=["Ticker","Qty","Avg_Price","Date_Added"])
    df = pd.DataFrame(st.session_state.portfolio)
    df["Ticker"] = df["Ticker"].astype(str).str.upper()
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0.0)
    df["Avg_Price"] = pd.to_numeric(df["Avg_Price"], errors="coerce").fillna(0.0)
    if "Date_Added" not in df.columns:
        df["Date_Added"] = ""
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
            # weighted avg on buys; sells keep avg
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
        "Reason": reason[:160],
    })

# ==================================================
# COUPLING + NEWS SCORING
# ==================================================
def coupling_score_for_ticker(ticker: str):
    """
    Returns: (score_float, label)
    FULLY_COUPLED = 2.0, STRONGLY_COUPLED = 1.5, POTENTIAL = 0.5
    """
    t = ticker.upper().strip()
    score = 0.0

    for c in st.session_state.couplings_log:
        a = (c.get("Ticker_A") or "").upper().strip()
        b = (c.get("Ticker_B") or "").upper().strip()
        if t not in [a, b]:
            continue
        strength = (c.get("Strength") or "").upper()
        if strength == "FULLY_COUPLED":
            score += 2.0
        elif strength == "STRONGLY_COUPLED":
            score += 1.5
        elif strength == "POTENTIAL":
            score += 0.5

    if score >= 4.0:
        return score, "HEAVY"
    if score >= 2.0:
        return score, "STRONG"
    if score >= 0.5:
        return score, "LIGHT"
    return score, "NONE"

def news_count_for_ticker(ticker: str, window: int = 200):
    """
    Counts recent NEWS inputs in the last 'window' inputs_log rows.
    """
    t = ticker.upper().strip()
    recent = st.session_state.inputs_log[:window]
    return sum(1 for x in recent if (x.get("Input_Type") == "SALES_NEWS" and (x.get("Ticker","").upper().strip() == t)))

def in_house(ticker: str):
    t = ticker.upper().strip()
    return any((r.get("Ticker","").upper().strip() == t) for r in st.session_state.rooms_log)

# ==================================================
# DECISION ENGINE (MODE B)
# ==================================================
def build_action_plan():
    """
    Mode B:
      - Trigger if Bullseye OR Coupling >= STRONG (>=2.0 total)
      - Direction from SLED Signal + RiseScore
      - News count boosts size slightly
    """
    scan = st.session_state.sales_last_scan or []
    if not scan:
        return pd.DataFrame()

    plan = []
    for r in scan:
        ticker = (r.get("Ticker") or "").upper().strip()
        if not ticker:
            continue

        # Must be ticker-resolved and in-house preferred (but not required)
        # If you want hard enforcement, flip this to "continue" when not in_house()
        in_house_flag = in_house(ticker)

        signal = (r.get("Signal") or "WAIT").upper()
        rise = float(r.get("RiseScore_14d", 0.0) or 0.0)
        gate = float(r.get("Gate", 0.0) or 0.0)
        z = float(r.get("Z_Trap", 1.0) or 1.0)
        price = r.get("Price", None)

        bull_buy = bool(r.get("Bullseye_BUY", False))
        bull_sell = bool(r.get("Bullseye_SELL", False))

        cscore, clabel = coupling_score_for_ticker(ticker)
        ncount = news_count_for_ticker(ticker)

        # Trigger condition (Mode B)
        coupled_strong = cscore >= 2.0
        triggered = bull_buy or bull_sell or coupled_strong

        if not triggered:
            continue

        # Determine action using algorithm direction
        action = "WAIT"
        reason_bits = []

        if bull_buy:
            reason_bits.append("BULLSEYE_BUY")
        if bull_sell:
            reason_bits.append("BULLSEYE_SELL")
        if coupled_strong:
            reason_bits.append(f"COUPLED_{clabel}")
        if in_house_flag:
            reason_bits.append("IN_HOUSE")

        # Direction:
        # - BUY if signal BUY, or (coupled strong & rise positive)
        # - SELL if signal SELL, or (coupled strong & rise negative)
        # - otherwise WAIT
        if signal == "BUY" or (coupled_strong and rise > 0.5):
            action = "BUY"
            reason_bits.append(f"SLED:{signal}")
            reason_bits.append(f"Rise:{rise:.2f}")
        elif signal == "SELL" or (coupled_strong and rise < -0.5):
            action = "SELL"
            reason_bits.append(f"SLED:{signal}")
            reason_bits.append(f"Rise:{rise:.2f}")
        else:
            action = "WAIT"
            reason_bits.append(f"SLED:{signal}")
            reason_bits.append(f"Rise:{rise:.2f}")

        # Price requirement
        if price is None or (isinstance(price, float) and np.isnan(price)):
            # fallback live price later during execution
            price = None

        # Size logic (paper-trading):
        base_qty = 10
        # Coupling size multiplier
        mult = 1.0 + min(cscore, 6.0) * 0.10   # up to +60%
        # News multiplier (light)
        mult *= (1.0 + min(ncount, 10) * 0.03) # up to +30%

        # Gate bonus for buys if gate strong and Z not too high
        if action == "BUY" and gate > 1.5 and z < 0.85:
            mult *= 1.15

        qty = int(max(1, round(base_qty * mult)))

        plan.append({
            "Ticker": ticker,
            "Action": action,
            "Qty": qty,
            "Price": price,
            "Signal": signal,
            "RiseScore_14d": round(rise, 3),
            "Gate": round(gate, 3),
            "Z_Trap": round(z, 3),
            "CouplingScore": round(cscore, 2),
            "CouplingLabel": clabel,
            "NewsCount": ncount,
            "InHouse": in_house_flag,
            "Reason": " | ".join(reason_bits)
        })

    dfp = pd.DataFrame(plan)
    if not dfp.empty:
        # Prioritize BUYs with higher RiseScore and coupling; SELLs with lower RiseScore
        dfp["Priority"] = np.where(
            dfp["Action"] == "BUY",
            dfp["RiseScore_14d"] + dfp["CouplingScore"],
            (-dfp["RiseScore_14d"]) + dfp["CouplingScore"]
        )
        dfp = dfp.sort_values(["Action","Priority"], ascending=[True, False])
    return dfp

# ==================================================
# RISK LIMITS (SANE DEFAULTS)
# ==================================================
st.subheader("🛡 Risk Limits (Paper)")
r1, r2, r3 = st.columns(3)
with r1:
    max_positions = st.number_input("Max open positions", min_value=1, value=12, step=1)
with r2:
    max_qty_per_ticker = st.number_input("Max qty per ticker", min_value=1, value=200, step=10)
with r3:
    max_actions_per_run = st.number_input("Max trade actions per run", min_value=1, value=10, step=1)

st.markdown("---")

# ==================================================
# ACTION PLAN PREVIEW
# ==================================================
st.subheader("📌 Action Plan (Mode B)")
plan_df = build_action_plan()

if plan_df.empty:
    st.info("No triggered actions yet. Run Sales scan + Reception coupling + News first.")
else:
    st.dataframe(plan_df, use_container_width=True)

# ==================================================
# EXECUTE PLAN
# ==================================================
def execute_plan(plan: pd.DataFrame):
    if plan is None or plan.empty:
        st.warning("No plan to execute.")
        return

    p = portfolio_df()
    open_positions = set(p["Ticker"].tolist()) if not p.empty else set()

    actions_done = 0

    for _, row in plan.iterrows():
        if actions_done >= max_actions_per_run:
            break

        ticker = row["Ticker"]
        action = row["Action"]
        qty = int(row["Qty"])
        px = row["Price"]

        # Get live px if missing
        if px is None or (isinstance(px, float) and np.isnan(px)):
            lp = live_price(ticker)
            if np.isnan(lp):
                continue
            px = float(lp)

        # Enforce max positions (only for new BUYs)
        if action == "BUY" and ticker not in open_positions and len(open_positions) >= max_positions:
            continue

        # Enforce max qty per ticker
        p_now = portfolio_df()
        if ticker in p_now["Ticker"].values:
            current_qty = float(p_now[p_now["Ticker"] == ticker]["Qty"].iloc[0])
        else:
            current_qty = 0.0

        if action == "BUY":
            allowed = max_qty_per_ticker - current_qty
            if allowed <= 0:
                continue
            qty_to_do = min(qty, int(allowed))
            if qty_to_do <= 0:
                continue

            upsert(ticker, qty_delta=qty_to_do, px=px)
            log_trade("BUY", ticker, qty_to_do, px, row["Reason"])
            open_positions.add(ticker)
            actions_done += 1

        elif action == "SELL":
            # If no position, skip
            if current_qty <= 0:
                continue
            qty_to_do = min(int(abs(qty)), int(current_qty))
            if qty_to_do <= 0:
                continue

            upsert(ticker, qty_delta=-qty_to_do, px=px)
            log_trade("SELL", ticker, -qty_to_do, px, row["Reason"])
            # if closed, remove from open_positions
            p_after = portfolio_df()
            if ticker not in p_after["Ticker"].values:
                open_positions.discard(ticker)
            actions_done += 1

    st.success(f"Executed {actions_done} trade actions.")

if st.button("🤖 Execute Mode-B Trades (Bullseye OR Coupled)"):
    execute_plan(plan_df)

st.markdown("---")

# ==================================================
# MANUAL ENTRY
# ==================================================
st.subheader("➕ Manual Add / Adjust")
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
# PORTFOLIO VIEW + VISUALS
# ==================================================
df = portfolio_df()
if df.empty:
    st.info("No holdings yet.")
else:
    st.subheader("📊 Holdings & Live PnL")

    prices = [live_price(x) for x in df["Ticker"].tolist()]
    df["Live_Price"] = prices
    df["Market_Value"] = df["Qty"] * df["Live_Price"]
    df["Cost_Basis"] = df["Qty"] * df["Avg_Price"]
    df["Unreal_PnL"] = df["Market_Value"] - df["Cost_Basis"]
    df["Unreal_PnL_%"] = np.where(df["Cost_Basis"] == 0, 0, (df["Unreal_PnL"] / df["Cost_Basis"]) * 100)

    st.dataframe(df, use_container_width=True)

    m1,m2,m3 = st.columns(3)
    m1.metric("Market Value", f"{df['Market_Value'].sum(skipna=True):,.2f}")
    m2.metric("Cost Basis", f"{df['Cost_Basis'].sum(skipna=True):,.2f}")
    m3.metric("Unrealized PnL", f"{df['Unreal_PnL'].sum(skipna=True):,.2f}")

    st.subheader("📈 Visuals")
    fig1, ax1 = plt.subplots(figsize=(8,3))
    ax1.bar(df["Ticker"], df["Market_Value"])
    ax1.set_title("Market Value by Ticker")
    ax1.grid(True, alpha=0.2)
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots(figsize=(8,3))
    ax2.bar(df["Ticker"], df["Unreal_PnL"])
    ax2.set_title("Unrealized PnL by Ticker")
    ax2.grid(True, alpha=0.2)
    st.pyplot(fig2)

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