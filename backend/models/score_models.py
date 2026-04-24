"""Internal scoring bucket models. Not exposed directly over the API — the
scoring engine reduces these into the public `AnalysisResponse` fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TechnicalBuckets:
    base_reversal: float = 0.0       # max 8
    candle_quality: float = 0.0      # max 5
    ma_structure: float = 0.0        # max 5
    breakout_confirm: float = 0.0    # max 6
    volume_quality: float = 0.0      # max 4
    overheat_penalty: float = 0.0    # subtracted, 0..2
    max_total: float = 30.0

    def total(self) -> float:
        raw = (
            self.base_reversal
            + self.candle_quality
            + self.ma_structure
            + self.breakout_confirm
            + self.volume_quality
            - self.overheat_penalty
        )
        return max(0.0, min(self.max_total, raw))


@dataclass
class FlowBuckets:
    stage_appropriateness: float = 0.0   # max 8
    continuity: float = 0.0              # max 6
    late_stage_penalty: float = 0.0      # subtracted, 0..6
    max_total: float = 20.0

    def total(self) -> float:
        raw = self.stage_appropriateness + self.continuity - self.late_stage_penalty
        return max(0.0, min(self.max_total, raw))


@dataclass
class TimeframeBuckets:
    monthly: float = 0.0     # max 5
    weekly: float = 0.0      # max 5
    daily: float = 0.0       # max 5
    max_total: float = 15.0

    def total(self) -> float:
        return max(0.0, min(self.max_total, self.monthly + self.weekly + self.daily))


@dataclass
class FundamentalBuckets:
    revenue_growth: float = 0.0          # max 3
    op_profit_growth: float = 0.0        # max 4
    op_gt_revenue: float = 0.0           # max 3
    margin: float = 0.0                  # max 2
    leverage: float = 0.0                # max 2
    estimate_revision: float = 0.0       # max 1
    max_total: float = 15.0

    def total(self) -> float:
        return max(
            0.0,
            min(
                self.max_total,
                self.revenue_growth
                + self.op_profit_growth
                + self.op_gt_revenue
                + self.margin
                + self.leverage
                + self.estimate_revision,
            ),
        )


@dataclass
class ThemeBuckets:
    sector_strength: float = 0.0     # max 3
    theme_momentum: float = 0.0      # max 3
    peer_confirmation: float = 0.0   # max 2
    leader_bonus: float = 0.0        # max 2
    max_total: float = 10.0

    def total(self) -> float:
        return max(
            0.0,
            min(
                self.max_total,
                self.sector_strength
                + self.theme_momentum
                + self.peer_confirmation
                + self.leader_bonus,
            ),
        )


@dataclass
class RiskBuckets:
    """Risk score is 0..10 with higher = more risk. It is NOT added to the
    total; it feeds a multiplicative gate in `scoring_engine.finalize`.
    """
    volatility: float = 0.0          # max 2
    overextension: float = 0.0       # max 3
    event_news: float = 0.0          # max 2
    liquidity: float = 0.0           # max 1
    crowding_failure: float = 0.0    # max 2
    max_total: float = 10.0
    flags: List[str] = field(default_factory=list)

    def total(self) -> float:
        return max(
            0.0,
            min(
                self.max_total,
                self.volatility
                + self.overextension
                + self.event_news
                + self.liquidity
                + self.crowding_failure,
            ),
        )


@dataclass
class AggregatedScore:
    technical: TechnicalBuckets
    flow: FlowBuckets
    timeframe: TimeframeBuckets
    fundamental: FundamentalBuckets
    theme: ThemeBuckets
    risk: RiskBuckets

    def raw_positive(self) -> float:
        """Sum of the 5 positive buckets, before risk gating."""
        return (
            self.technical.total()
            + self.flow.total()
            + self.timeframe.total()
            + self.fundamental.total()
            + self.theme.total()
        )

    def to_breakdown(self) -> Dict[str, float]:
        return {
            "technical": self.technical.total(),
            "flow": self.flow.total(),
            "timeframe": self.timeframe.total(),
            "fundamental": self.fundamental.total(),
            "theme": self.theme.total(),
            "risk": self.risk.total(),
        }
