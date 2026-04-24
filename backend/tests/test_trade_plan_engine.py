"""Trade plan engine must produce reasonable structural levels or fail loudly."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.engines import trade_plan_engine as tp


def _df(closes):
    n = len(closes)
    idx = pd.bdate_range(end="2026-04-22", periods=n)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) * 1.015
    lows = np.minimum(opens, closes) * 0.985
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": [900_000] * n},
        index=idx,
    )


def test_plan_emits_prices_when_structure_is_clean():
    # Clean uptrend with pivots
    rng = np.random.default_rng(10)
    trend = np.linspace(10000, 12000, 200) + rng.normal(0, 120, 200)
    df = _df(trend)
    plan = tp.generate(df, stage="포킹", risk_score=2.0)

    assert plan.current_price > 0
    assert plan.buy_zone_1.price is not None
    assert plan.stop_loss.price is not None
    assert plan.take_profit_1.price is not None
    assert plan.stop_loss.price < plan.current_price
    assert plan.take_profit_1.price > plan.current_price


def test_plan_refuses_entry_in_overheated_stage():
    closes = np.concatenate([np.full(200, 10000.0), np.linspace(10100, 18000, 60)])
    df = _df(closes)
    plan = tp.generate(df, stage="과열", risk_score=7.0)
    assert "추격" in plan.one_line_strategy or plan.confidence_score < 0.35


def test_confidence_decreases_with_high_risk():
    closes = np.linspace(10000, 11000, 200)
    df = _df(closes)
    low = tp.generate(df, stage="포킹", risk_score=1.0).confidence_score
    high = tp.generate(df, stage="포킹", risk_score=9.0).confidence_score
    assert high <= low
