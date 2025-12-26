import numpy as np
import pandas as pd
import yfinance as yf

def safe_history(ticker: str, period: str = "3mo"):
    """
    Reliable history fetch for Streamlit Cloud.
    Returns DataFrame with at least 'Close' or None.
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, auto_adjust=True)
        if df is None or df.empty or "Close" not in df.columns:
            return None
        return df
    except Exception:
        return None

class SLEDEngine:
    """
    Minimal stable SLED v1:
    - Trap proxy Z from rolling volatility
    - Gate proxy from momentum scaled by (1-Z)
    - Signals: BUY / SELL / WAIT
    """
    def __init__(self, window: int = 14):
        self.window = int(window)

    def evaluate(self, df: pd.DataFrame):
        if df is None or len(df) < self.window or "Close" not in df.columns:
            return "WAIT", {}

        close = df["Close"].astype(float)

        # Returns & rolling volatility
        returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        vol = returns.rolling(self.window, min_periods=max(5, self.window // 2)).std()

        vol_last = float(vol.iloc[-1]) if not np.isnan(vol.iloc[-1]) else 0.0
        vol_max = float(vol.max()) if not np.isnan(vol.max()) else 0.0

        # Trap proxy: higher vol => lower Z
        z_trap = 1.0 - (vol_last / (vol_max + 1e-9))
        z_trap = float(np.clip(z_trap, 0.0, 1.0))

        # Momentum & Gate proxy
        momentum = float(close.iloc[-1] - close.iloc[-self.window])
        gate = float(abs(momentum) * (1.0 - z_trap))

        # Stability / “WAIT” detection
        price_std = float(close.tail(self.window).std()) if len(close) >= self.window else float(close.std())
        gate_thresh = max(price_std * 0.8, 0.0001)

        if gate > gate_thresh and momentum > 0:
            signal = "BUY"
        elif gate > gate_thresh and momentum < 0:
            signal = "SELL"
        else:
            signal = "WAIT"

        metrics = {
            "Z_Trap": round(z_trap, 3),
            "Momentum": round(momentum, 3),
            "Gate": round(gate, 3),
            "Gate_Thresh": round(gate_thresh, 3),
            "Price": round(float(close.iloc[-1]), 3),
        }
        return signal, metrics