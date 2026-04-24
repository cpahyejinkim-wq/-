"""Technical engine smoke tests against crafted synthetic OHLCV."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.engines import technical_engine as te


def _build(closes, volumes=None):
    n = len(closes)
    idx = pd.bdate_range(end="2026-04-22", periods=n)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) * 1.01
    lows = np.minimum(opens, closes) * 0.99
    vol = volumes if volumes is not None else [1_000_000] * n
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": vol},
        index=idx,
    )


def test_poking_detector_fires_on_clean_breakout():
    # 80 base + 20 dip below base + 20 strong rise. Last 20 bars start below
    # MA20 and end above → clean poking setup.
    base = np.full(80, 10000.0)
    dip = np.linspace(9900, 9200, 20)
    rise = np.linspace(9400, 11500, 20)
    closes = np.concatenate([base, dip, rise])
    volumes = [500_000] * 100 + [1_600_000] * 20
    df = _build(closes, volumes)
    conf, ev = te.detect_poking_breakout(df)
    assert conf > 0.4, f"expected poking confidence > 0.4, got {conf} / {ev}"


def test_overheating_detector_fires_when_stretched():
    # 60 flat base + 20 moderate ramp + 15 parabolic (3.5%/day) finish.
    base = np.full(60, 10000.0)
    ramp1 = np.linspace(10200, 13000, 20)
    ramp2 = [ramp1[-1] * (1.035 ** i) for i in range(1, 16)]
    closes = np.concatenate([base, ramp1, np.array(ramp2)])
    df = _build(closes)
    conf, ev = te.detect_overheating(df)
    assert conf > 0.4, f"expected overheating confidence > 0.4, got {conf} / {ev}"


def test_t_bottom_detector_needs_prior_decline():
    # Flat data must not trigger T-bottom
    closes = np.full(120, 10000.0) + np.random.default_rng(1).normal(0, 50, 120)
    df = _build(closes)
    conf, _ = te.detect_t_bottom(df)
    assert conf < 0.5


def test_t_bottom_detector_fires_after_decline_and_compression():
    decline = np.linspace(12000, 8500, 60)
    base = np.full(40, 8550) + np.random.default_rng(2).normal(0, 30, 40)
    tail = np.array([8560, 8555, 8540, 8570])  # tight range incl. doji-ish
    closes = np.concatenate([decline, base, tail])
    df = _build(closes)
    conf, ev = te.detect_t_bottom(df)
    assert conf > 0.3, f"expected T-bottom confidence > 0.3, got {conf} / {ev}"


def test_analyze_returns_buckets_in_range():
    closes = np.linspace(10000, 11000, 200) + np.random.default_rng(3).normal(0, 80, 200)
    df = _build(closes)
    result = te.analyze(df)
    assert 0.0 <= result.buckets.total() <= 30.0
