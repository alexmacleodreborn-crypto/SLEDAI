import pandas as pd
import numpy as np
from scipy.stats import entropy
import yfinance as yf
from datetime import datetime, timedelta

# ==================================================
# NEWS FILTERS (RELEVANT ONLY)
# ==================================================
NEWS_KEYWORDS = [
    "earnings", "revenue", "profit", "guidance",
    "acquisition", "acquire", "merger", "m&a", "divest", "sale", "sell",
    "regulation", "regulator", "lawsuit", "litigation", "investigation", "probe",
    "ceo", "cfo", "board", "executive", "resign", "appointed"
]

NEGATIVE_WORDS = {
    "miss", "cut", "downgrade", "loss", "decline", "drop", "fall",
    "investigation", "lawsuit", "fine", "probe", "recall", "delay",
    "weak", "warning", "slump"
}

POSITIVE_WORDS = {
    "beat", "growth", "upgrade", "record",
    "strong", "expand", "increase", "approval",
    "surge", "raise", "outperform"
}


def classify_news_sentiment(text: str) -> str:
    t = (text or "").lower()
    neg = sum(1 for w in NEGATIVE_WORDS if w in t)
    pos = sum(1 for w in POSITIVE_WORDS if w in t)

    if neg > pos:
        return "NEGATIVE"
    if pos > neg:
        return "POSITIVE"
    return "NEUTRAL"


def safe_news(ticker: str, limit: int = 8):
    """
    Returns ONLY relevant news items for this ticker.
    Output: list[{ticker,title,sentiment,publisher,link}]
    """
    try:
        tk = yf.Ticker(ticker)
        raw = tk.news or []
    except Exception:
        return []

    relevant = []
    for item in raw[:limit]:
        title = item.get("title", "") or ""
        summary = item.get("summary", "") or ""
        text = f"{title} {summary}"

        # Strict relevance filter
        if not any(k in text.lower() for k in NEWS_KEYWORDS):
            continue

        relevant.append({
            "ticker": ticker.upper(),
            "title": title,
            "sentiment": classify_news_sentiment(text),
            "publisher": item.get("publisher", "") or "",
            "link": item.get("link", "") or "",
        })

    return relevant


def apply_news_filter(sled_signal: str, news_items: list):
    """
    News can only confirm or cancel an action.
    It never creates a trade.
    """
    sig = (sled_signal or "WAIT").upper()

    if sig == "WAIT":
        return "WAIT", "No SLED signal"

    if not news_items:
        return sig, "No relevant news"

    sentiments = {n.get("sentiment", "NEUTRAL") for n in news_items}

    if sig == "BUY":
        if "NEGATIVE" in sentiments:
            return "WAIT", "Negative news risk (BUY cancelled)"
        return "BUY", "News confirms BUY"

    if sig == "SELL":
        if "POSITIVE" in sentiments:
            return "WAIT", "Positive news conflict (SELL cancelled)"
        return "SELL", "News confirms SELL"

    return "WAIT", "Default"


# ==================================================
# YFINANCE SAFE HISTORY
# ==================================================
def safe_history(ticker: str, period: str = "6mo"):
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        # fix multiindex columns
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df.columns = df.columns.droplevel(1)
            except Exception:
                df.columns = df.columns.get_level_values(0)
        df = df.loc[:, ~df.columns.duplicated()]
        if "Close" not in df.columns:
            return None
        return df
    except Exception:
        return None


# ==================================================
# SLED ENGINE
# ==================================================
class SLEDEngine:
    def __init__(self, window=20, lookback=100, entropy_bins=10):
        self.window = window
        self.lookback = lookback
        self.entropy_bins = entropy_bins

    def calculate(self, df: pd.DataFrame):
        try:
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            # Velocity
            df["Log_Return"] = np.log(close / close.shift(1)).fillna(0)

            # Trap (Z)
            df["Rolling_Std"] = df["Log_Return"].rolling(self.window).std()
            r_min = df["Rolling_Std"].rolling(self.lookback).min()
            r_max = df["Rolling_Std"].rolling(self.lookback).max()
            denom = (r_max - r_min)

            df["Norm_Vol"] = np.where(denom == 0, 0, (df["Rolling_Std"] - r_min) / denom)
            df["Z_Trap"] = 1 - df["Norm_Vol"]

            # Flow (Sigma) entropy
            has_vol = ("Volume" in df.columns) and (df["Volume"].sum() > 0)

            def get_ent(s):
                if len(s) < self.window:
                    return np.nan
                h, _ = np.histogram(s, bins=self.entropy_bins)
                if h.sum() == 0:
                    return 0.0
                p = h / h.sum()
                p = p[p > 0]
                return entropy(p, base=2)

            if has_vol:
                vol = df["Volume"]
                if isinstance(vol, pd.DataFrame):
                    vol = vol.iloc[:, 0]
                df["Sigma"] = vol.rolling(self.window).apply(get_ent)
            else:
                df["Sigma"] = df["Log_Return"].rolling(self.window).apply(get_ent) * 1.5

            # Gate
            df["Gate"] = (1 - df["Z_Trap"]) * df["Sigma"]

            # Relative Price Loc (0..1)
            low = close.rolling(50).min()
            high = close.rolling(50).max()
            denom_p = (high - low)
            df["Price_Loc"] = np.where(denom_p == 0, 0.5, (close - low) / denom_p)

            # Phase-0 threshold
            ent_thresh = df["Sigma"].rolling(200).quantile(0.85)
            is_phase_0 = (df["Z_Trap"] > 0.75) & (df["Sigma"] > ent_thresh)

            df["Signal_Buy"] = np.where(is_phase_0 & (df["Price_Loc"] < 0.4), 1, 0)
            df["Signal_Sell"] = np.where(is_phase_0 & (df["Price_Loc"] > 0.6), 1, 0)

            # Rise score (simple forward proxy): Gate strength + Sigma - Z (bounded)
            df["RiseScore_14d"] = (
                (df["Gate"].fillna(0) * 0.6)
                + (df["Sigma"].fillna(0) * 0.3)
                - (df["Z_Trap"].fillna(0) * 0.4)
            )

            return df
        except Exception:
            return None

    def summarize(self, df: pd.DataFrame):
        if df is None or df.empty:
            return None
        last = df.iloc[-1]

        price = float(last.get("Close", np.nan))
        z = float(last.get("Z_Trap", np.nan))
        gate = float(last.get("Gate", np.nan))
        rise = float(last.get("RiseScore_14d", 0.0))

        signal = "WAIT"
        if int(last.get("Signal_Buy", 0)) == 1:
            signal = "BUY"
        elif int(last.get("Signal_Sell", 0)) == 1:
            signal = "SELL"

        # Bullseye markers (tightened)
        bull_buy = (signal == "BUY") and (gate >= 1.6) and (z <= 0.85)
        bull_sell = (signal == "SELL") and (gate >= 1.6) and (z <= 0.85)

        return {
            "Price": round(price, 4) if np.isfinite(price) else np.nan,
            "Signal": signal,
            "Z_Trap": round(z, 4) if np.isfinite(z) else np.nan,
            "Gate": round(gate, 4) if np.isfinite(gate) else np.nan,
            "RiseScore_14d": round(rise, 4),
            "Bullseye_BUY": bool(bull_buy),
            "Bullseye_SELL": bool(bull_sell),
        }