"""Scoring engine overrides and gating behavior."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.engines import scoring_engine as se
from backend.engines import trade_plan_engine as tp
from backend.models.score_models import (
    AggregatedScore,
    FlowBuckets,
    FundamentalBuckets,
    RiskBuckets,
    TechnicalBuckets,
    ThemeBuckets,
    TimeframeBuckets,
)


def _plan():
    closes = np.linspace(10000, 11000, 200)
    idx = pd.bdate_range(end="2026-04-22", periods=200)
    df = pd.DataFrame(
        {
            "open": closes, "high": closes * 1.01, "low": closes * 0.99,
            "close": closes, "volume": [800_000] * 200,
        },
        index=idx,
    )
    return tp.generate(df, stage="포킹", risk_score=1.0)


def _agg(risk=1.0):
    return AggregatedScore(
        technical=TechnicalBuckets(base_reversal=7, candle_quality=4, ma_structure=4, breakout_confirm=5, volume_quality=3),
        flow=FlowBuckets(stage_appropriateness=8, continuity=6),
        timeframe=TimeframeBuckets(monthly=5, weekly=5, daily=5),
        fundamental=FundamentalBuckets(revenue_growth=3, op_profit_growth=4, op_gt_revenue=3, margin=2, leverage=2, estimate_revision=1),
        theme=ThemeBuckets(sector_strength=3, theme_momentum=3, peer_confirmation=2, leader_bonus=2),
        risk=RiskBuckets(volatility=risk * 0.2, overextension=risk * 0.3, event_news=risk * 0.2, liquidity=risk * 0.1, crowding_failure=risk * 0.2),
    )


def test_overheated_never_strong_buy():
    plan = _plan()
    result = se.finalize(_agg(risk=1.0), stage="과열", plan=plan)
    assert result.action != "Strong Buy Setup"


def test_high_risk_gates_total_score_down():
    plan = _plan()
    low_risk = se.finalize(_agg(risk=0.5), stage="포킹", plan=plan).total_score
    high_risk = se.finalize(_agg(risk=9.0), stage="포킹", plan=plan).total_score
    assert high_risk < low_risk
    # Should still produce some score, just meaningfully lower
    assert low_risk - high_risk > 15


def test_missing_stop_downgrades_action():
    plan = _plan()
    plan.stop_loss.price = None
    result = se.finalize(_agg(risk=0.5), stage="포킹", plan=plan)
    # Raw score high enough to hit Strong Buy, but missing stop must downgrade.
    assert result.action in {"Watch for Confirmation", "Buy on Pullback", "Hold / No Immediate Entry"}


def test_total_score_is_bounded_0_to_100():
    plan = _plan()
    result = se.finalize(_agg(risk=1.0), stage="포킹", plan=plan)
    assert 0.0 <= result.total_score <= 100.0
