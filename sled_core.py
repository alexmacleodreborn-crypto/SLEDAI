import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import entropy
from datetime import datetime, timedelta

def safe_history(ticker: str, period: str = "6mo"):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, auto_adjust=True)
        if df is None or df.empty or "Close" not in df.columns:
            return None
        # Ensure Volume exists
        if "Volume" not in df.columns:
            df["Volume"] = 0
        return df
    except Exception:
        return None

class SLEDEngine:
    """
    Full SLED Physics:
    - Z_Trap from normalized rolling volatility
    - Sigma from rolling entropy (Volume preferred)
    - Gate = (1-Z)*Sigma
    - Projected move % (3-day proxy) and RiseScore (14-day proxy ranking)
    - BUY/SELL signals using Phase-0 logic and price location
    """
    def __init__(self, window=20, lookback=100, entropy_bins=10):
        self.window = int(window)
        self.lookback = int(lookback)
        self.entropy_bins = int(entropy_bins)

    def calculate(self, df: pd.DataFrame):
        if df is None or df.empty or len(df) < max(self.lookback, self.window + 5):
            return None

        close = df["Close"].astype(float)

        # 1) Velocity
        df["Log_Return"] = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # 2) Trap (Z)
        df["Rolling_Std"] = df["Log_Return"].rolling(self.window).std()
        r_min = df["Rolling_Std"].rolling(self.lookback).min()
        r_max = df["Rolling_Std"].rolling(self.lookback).max()
        denom = (r_max - r_min).replace(0, np.nan)
        norm_vol = (df["Rolling_Std"] - r_min) / denom
        norm_vol = norm_vol.fillna(0.0).clip(0, 1)
        df["Z_Trap"] = (1.0 - norm_vol).clip(0, 1)

        # 3) Flow (Sigma) via entropy
        def ent_fn(series):
            series = series.dropna()
            if len(series) < self.window:
                return np.nan
            h, _ = np.histogram(series, bins=self.entropy_bins)
            if h.sum() == 0:
                return 0.0
            p = h / h.sum()
            p = p[p > 0]
            return float(entropy(p, base=2))

        has_vol = "Volume" in df.columns and df["Volume"].fillna(0).sum() > 0
        if has_vol:
            df["Sigma"] = df["Volume"].rolling(self.window).apply(ent_fn, raw=False)
        else:
            df["Sigma"] = df["Log_Return"].rolling(self.window).apply(ent_fn, raw=False) * 1.5

        df["Sigma"] = df["Sigma"].fillna(method="bfill").fillna(0.0)

        # 4) Gate
        df["Gate"] = (1.0 - df["Z_Trap"]) * df["Sigma"]

        # 5) Projected move (3-day proxy)
        current_vol = float(df["Rolling_Std"].iloc[-1]) if not np.isnan(df["Rolling_Std"].iloc[-1]) else 0.0
        energy_mult = float(df["Sigma"].iloc[-1])
        df["Proj_Move_Pct_3d"] = (current_vol * energy_mult * np.sqrt(3.0)) * 100.0

        # 6) Phase-0 signals
        ent_thresh = df["Sigma"].rolling(200).quantile(0.85).fillna(df["Sigma"].quantile(0.85))
        is_phase_0 = (df["Z_Trap"] > 0.75) & (df["Sigma"] > ent_thresh)

        r_low = close.rolling(50).min()
        r_high = close.rolling(50).max()
        denom_p = (r_high - r_low).replace(0, np.nan)
        price_loc = ((close - r_low) / denom_p).fillna(0.5).clip(0, 1)
        df["Price_Loc"] = price_loc

        df["Signal_Buy"]  = np.where(is_phase_0 & (df["Price_Loc"] < 0.4), 1, 0)
        df["Signal_Sell"] = np.where(is_phase_0 & (df["Price_Loc"] > 0.6), 1, 0)

        # 7) “14-day rising” proxy score
        # Use: Gate strength + positive drift - penalty for high trap
        drift = close.pct_change(14).iloc[-1]
        drift = float(drift) if not np.isnan(drift) else 0.0
        gate_last = float(df["Gate"].iloc[-1])
        z_last = float(df["Z_Trap"].iloc[-1])
        proj3 = float(df["Proj_Move_Pct_3d"].iloc[-1])

        rise_score = (gate_last * 2.0) + (drift * 100.0) + (proj3 * 0.25) - (z_last * 1.0)
        df["RiseScore_14d"] = rise_score

        return df

    def summarize(self, df: pd.DataFrame):
        if df is None or df.empty:
            return None

        last = df.iloc[-1]
        close = float(last["Close"])
        z = float(last["Z_Trap"])
        sigma = float(last["Sigma"])
        gate = float(last["Gate"])
        proj3 = float(last.get("Proj_Move_Pct_3d", 0.0))
        rise = float(last.get("RiseScore_14d", 0.0))

        signal = "WAIT"
        if int(last.get("Signal_Buy", 0)) == 1:
            signal = "BUY"
        elif int(last.get("Signal_Sell", 0)) == 1:
            signal = "SELL"

        bullseye_buy = (signal == "BUY") and (gate >= np.nanquantile(df["Gate"].tail(120), 0.85)) and (z < 0.75)
        bullseye_sell = (signal == "SELL") and (gate >= np.nanquantile(df["Gate"].tail(120), 0.85))

        return {
            "Price": round(close, 3),
            "Z_Trap": round(z, 3),
            "Sigma": round(sigma, 3),
            "Gate": round(gate, 3),
            "Proj_Move_Pct_3d": round(proj3, 3),
            "RiseScore_14d": round(rise, 3),
            "Signal": signal,
            "Bullseye_BUY": bool(bullseye_buy),
            "Bullseye_SELL": bool(bullseye_sell),
        }

def safe_news(ticker: str, limit: int = 8):
    """
    Uses Yahoo news via yfinance. Returns list of dicts with title/publisher/link/time.
    """
    try:
        t = yf.Ticker(ticker)
        items = t.news or []
        out = []
        for n in items[:limit]:
            out.append({
                "title": n.get("title", ""),
                "publisher": n.get("publisher", ""),
                "link": n.get("link", ""),
                "providerPublishTime": n.get("providerPublishTime", None)
            })
        return out
    except Exception:
        return []