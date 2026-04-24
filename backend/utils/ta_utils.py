"""Technical-analysis helpers built on pandas/numpy only.

Kept intentionally dependency-light so the engines are portable and the tests
don't need a TA library. Every function assumes a DataFrame with columns
[open, high, low, close, volume] and a DatetimeIndex sorted ascending.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


# ---------- Resampling ----------

def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample daily OHLCV to weekly ('W-FRI') or monthly ('M')."""
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    out = df.resample(rule).agg(agg).dropna(subset=["close"])
    return out


# ---------- Moving averages / vol ----------

def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False, min_periods=n).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def pct_return(series: pd.Series, n: int) -> float:
    if len(series) <= n:
        return 0.0
    a, b = series.iloc[-n - 1], series.iloc[-1]
    if a == 0 or pd.isna(a) or pd.isna(b):
        return 0.0
    return float((b - a) / a * 100.0)


# ---------- MA alignment ----------

def ma_alignment_score(df: pd.DataFrame) -> float:
    """Returns 0..1 for how cleanly the stock sits in a bullish MA stack
    (5 > 20 > 60 > 120) with price above the short MA. NaN-aware.
    """
    close = df["close"]
    ma5, ma20, ma60, ma120 = sma(close, 5), sma(close, 20), sma(close, 60), sma(close, 120)
    try:
        c = close.iloc[-1]
        m5, m20, m60, m120 = ma5.iloc[-1], ma20.iloc[-1], ma60.iloc[-1], ma120.iloc[-1]
    except IndexError:
        return 0.0
    checks = [
        (c > m5, 0.15),
        (m5 > m20, 0.25),
        (m20 > m60, 0.25),
        (m60 > m120, 0.20),
        (c > m120, 0.15),  # price above long MA = structural
    ]
    score = 0.0
    for ok, w in checks:
        if pd.notna(ok) and bool(ok):
            score += w
    return float(score)


# ---------- Pivots / swing points ----------

@dataclass
class Pivot:
    idx: int
    date: pd.Timestamp
    price: float
    kind: str  # "low" or "high"


def find_pivots(series: pd.Series, left: int = 3, right: int = 3) -> List[Pivot]:
    """Classic fractal pivots: a low is lower than `left` bars before and
    `right` bars after (and symmetrically for highs). Uses close values, which
    is robust for the Korean market where wicks are inflated by auctions.
    """
    values = series.to_numpy()
    out: List[Pivot] = []
    for i in range(left, len(values) - right):
        window = values[i - left : i + right + 1]
        v = values[i]
        if v == window.min() and (window == v).sum() == 1:
            out.append(Pivot(i, series.index[i], float(v), "low"))
        elif v == window.max() and (window == v).sum() == 1:
            out.append(Pivot(i, series.index[i], float(v), "high"))
    return out


def recent_lows(pivots: List[Pivot], n: int = 3) -> List[Pivot]:
    return [p for p in pivots if p.kind == "low"][-n:]


def recent_highs(pivots: List[Pivot], n: int = 3) -> List[Pivot]:
    return [p for p in pivots if p.kind == "high"][-n:]


# ---------- Candles ----------

def body_ratio(bar: pd.Series) -> float:
    rng = bar["high"] - bar["low"]
    if rng == 0:
        return 0.0
    return abs(bar["close"] - bar["open"]) / rng


def lower_shadow_ratio(bar: pd.Series) -> float:
    rng = bar["high"] - bar["low"]
    if rng == 0:
        return 0.0
    return (min(bar["open"], bar["close"]) - bar["low"]) / rng


def is_doji(bar: pd.Series, body_max: float = 0.15) -> bool:
    return body_ratio(bar) <= body_max


def is_bullish(bar: pd.Series) -> bool:
    return bar["close"] > bar["open"]


# ---------- Volume ----------

def volume_ratio(df: pd.DataFrame, lookback: int = 20) -> float:
    if len(df) < lookback + 1:
        return 1.0
    recent = df["volume"].iloc[-1]
    avg = df["volume"].iloc[-lookback - 1 : -1].mean()
    if avg == 0 or pd.isna(avg):
        return 1.0
    return float(recent / avg)


# ---------- Distance from MA ----------

def distance_from_ma(df: pd.DataFrame, n: int = 20) -> float:
    """%. Positive = price above MA, negative = below."""
    close = df["close"]
    ma = sma(close, n)
    if pd.isna(ma.iloc[-1]) or ma.iloc[-1] == 0:
        return 0.0
    return float((close.iloc[-1] - ma.iloc[-1]) / ma.iloc[-1] * 100.0)


# ---------- Support / resistance ----------

def support_resistance_levels(
    df: pd.DataFrame, lookback: int = 120, left: int = 3, right: int = 3
) -> Tuple[List[float], List[float]]:
    """Derive support/resistance from close-based pivots within `lookback`."""
    window = df.tail(lookback)
    pivots = find_pivots(window["close"], left=left, right=right)
    lows = sorted({round(p.price, 2) for p in pivots if p.kind == "low"})
    highs = sorted({round(p.price, 2) for p in pivots if p.kind == "high"})
    return lows, highs


# ---------- Trend summaries ----------

def trend_state(df: pd.DataFrame) -> str:
    """Very rough trend classifier used by the timeframe engine."""
    if len(df) < 60:
        return "형성중"
    close = df["close"]
    ma20 = sma(close, 20).iloc[-1]
    ma60 = sma(close, 60).iloc[-1]
    ma120 = sma(close, 120).iloc[-1] if len(df) >= 120 else np.nan
    last = close.iloc[-1]
    if pd.notna(ma120) and ma20 > ma60 > ma120 and last > ma20:
        return "정배열상승"
    if pd.notna(ma120) and ma20 < ma60 < ma120 and last < ma20:
        return "역배열하락"
    if ma20 > ma60 and last > ma60:
        return "단기상승"
    if ma20 < ma60 and last < ma60:
        return "단기하락"
    return "횡보"


def compression_ratio(df: pd.DataFrame, n: int = 20) -> float:
    """Bollinger-like bandwidth proxy: stddev of close / mean of close. Low
    values mean tight compression (good for T-bottom / base detection)."""
    if len(df) < n:
        return 1.0
    w = df["close"].tail(n)
    mean = w.mean()
    if mean == 0:
        return 1.0
    return float(w.std() / mean)
