import numpy as np
import pandas as pd
import yfinance as yf

def safe_history(ticker: str, period: str = "3mo"):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, auto_adjust=True)
        if df is None or df.empty or "Close" not in df.columns:
            return None
        return df
    except Exception:
        return None

class SLEDEngine:
    def __init__(self, window: int = 14):
        self.window = window

    def evaluate(self, df: pd.DataFrame):
        if df is None or len(df) < self.window:
            return "WAIT", {}

        close = df["Close"].astype(float)
        returns = np.log(close / close.shift(1)).fillna(0.0)
        vol = returns.rolling(self.window).std()

        vol_last = float(vol.iloc[-1])
        vol_max = float(vol.max()) if vol.max() > 0 else vol_last

        z_trap = 1.0 - (vol_last / (vol_max + 1e-9))
        z_trap = float(np.clip(z_trap, 0.0, 1.0))

        momentum = float(close.iloc[-1] - close.iloc[-self.window])
        gate = abs(momentum) * (1.0 - z_trap)

        price_std = float(close.tail(self.window).std())
        gate_thresh = max(price_std * 0.8, 0.0001)

        if gate > gate_thresh and momentum > 0:
            signal = "BUY"
        elif gate > gate_thresh and momentum < 0:
            signal = "SELL"
        else:
            signal = "WAIT"

        bullseye_buy = signal == "BUY" and gate > gate_thresh and z_trap < 0.6
        bullseye_sell = signal == "SELL" and gate > gate_thresh

        metrics = {
            "Price": round(float(close.iloc[-1]), 3),
            "Z_Trap": round(z_trap, 3),
            "Gate": round(gate, 3),
            "Gate_Thresh": round(gate_thresh, 3),
            "Bullseye_BUY": bullseye_buy,
            "Bullseye_SELL": bullseye_sell,
        }

        return signal, metrics