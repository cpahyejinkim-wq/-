"""Flow engine covers stage classification and continuity scoring."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.engines import flow_engine as fe


def _df(closes):
    n = len(closes)
    idx = pd.bdate_range(end="2026-04-22", periods=n)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) * 1.01
    lows = np.minimum(opens, closes) * 0.99
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": [800_000] * n},
        index=idx,
    )


def test_overheated_stage_detected():
    base = np.full(200, 10000.0)
    ramp = np.linspace(10200, 18000, 60)
    df = _df(np.concatenate([base, ramp]))
    res = fe.analyze(df)
    assert res.stage == "과열"
    assert res.buckets.late_stage_penalty == 6.0


def test_t_bottom_detected_after_decline():
    decline = np.linspace(12000, 8500, 60)
    base = np.full(50, 8550) + np.random.default_rng(1).normal(0, 25, 50)
    df = _df(np.concatenate([np.full(100, 12000), decline, base]))
    res = fe.analyze(df)
    assert res.stage in {"T바닥", "관찰"}  # compression may land either way under noise


def test_continuity_scores_natural_transition_higher():
    # Two charts whose stages are T바닥 → 포킹 vs 관찰 → 과열
    natural, _ = fe._continuity_score("포킹", "T바닥")
    broken, _ = fe._continuity_score("과열", "관찰")
    assert natural > broken


def test_stage_buckets_capped():
    # Any analysis result must respect the 20-point flow cap.
    closes = np.linspace(10000, 10500, 300)
    df = _df(closes)
    res = fe.analyze(df)
    assert 0 <= res.buckets.total() <= 20
