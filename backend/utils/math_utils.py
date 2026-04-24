"""Small numeric helpers with explicit behavior on edge cases."""
from __future__ import annotations

import math
from typing import Iterable, List, Optional


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    if b == 0 or b is None or (isinstance(b, float) and math.isnan(b)):
        return default
    return a / b


def pct_change(a: float, b: float) -> float:
    """Percent change from `a` to `b`, 0 if `a` is zero."""
    return safe_div(b - a, a, default=0.0) * 100.0


def rescale(value: float, in_lo: float, in_hi: float, out_lo: float, out_hi: float) -> float:
    """Linearly map `value` in [in_lo, in_hi] into [out_lo, out_hi] with clamp."""
    if in_hi == in_lo:
        return (out_lo + out_hi) / 2
    t = (value - in_lo) / (in_hi - in_lo)
    t = clamp(t, 0.0, 1.0)
    return out_lo + (out_hi - out_lo) * t


def nearest_below(levels: Iterable[float], price: float) -> Optional[float]:
    """Nearest level that is strictly below `price`. None if none."""
    below = [x for x in levels if x is not None and x < price]
    return max(below) if below else None


def nearest_above(levels: Iterable[float], price: float) -> Optional[float]:
    below = [x for x in levels if x is not None and x > price]
    return min(below) if below else None


def top_n_by(values: List[float], n: int, reverse: bool = True) -> List[float]:
    s = sorted(values, reverse=reverse)
    return s[:n]
