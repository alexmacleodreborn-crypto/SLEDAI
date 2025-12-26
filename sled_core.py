import numpy as np
import pandas as pd

class SLEDEngine:
    def __init__(self, window=14):
        self.window = window

    def evaluate(self, df: pd.DataFrame):
        """
        Returns: signal, metrics dict
        """
        if df is None or len(df) < self.window:
            return "WAIT", {}

        close = df["Close"]

        # --- Volatility (Trap proxy)
        returns = np.log(close / close.shift(1)).fillna(0)
        vol = returns.rolling(self.window).std()

        z_trap = 1 - (vol.iloc[-1] / (vol.max() + 1e-6))
        z_trap = float(np.clip(z_trap, 0, 1))

        # --- Momentum
        momentum = close.iloc[-1] - close.iloc[-self.window]

        # --- Gate (simple form)
        gate = abs(momentum) * (1 - z_trap)

        # --- Decision
        if gate > close.std() * 0.8 and momentum > 0:
            signal = "BUY"
        elif gate > close.std() * 0.8 and momentum < 0:
            signal = "SELL"
        else:
            signal = "WAIT"

        metrics = {
            "Z_Trap": round(z_trap, 3),
            "Momentum": round(float(momentum), 3),
            "Gate": round(float(gate), 3),
        }

        return signal, metrics