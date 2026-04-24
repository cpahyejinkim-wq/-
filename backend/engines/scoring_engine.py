"""Final score aggregation.

Applies the PDF-aligned overrides on top of the raw positive buckets:

    final_score = raw_positive × risk_multiplier - overheat_penalty + continuity_adj

where:
  - raw_positive = technical + flow + timeframe + fundamental + theme (max 90)
  - risk_multiplier maps risk_score 0..10 into 1.0..0.55
  - overheat_penalty = 15 if stage == 과열
  - continuity_adj = -10..+5 from flow continuity

and then action is chosen considering score + stage + stop-loss clarity.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.models.analysis_models import Action, FinalDecision, Stage, TradePlan
from backend.models.score_models import AggregatedScore
from backend.utils.math_utils import clamp, rescale


@dataclass
class FinalResult:
    total_score: float
    raw_score: float
    risk_multiplier: float
    overheat_penalty: float
    action: Action
    summary: str


def _action_for(score: float, stage: Stage, plan: TradePlan) -> Action:
    # Override 1: overheated → never Strong Buy
    if stage == "과열":
        if score >= 40:
            return "Hold / No Immediate Entry"
        return "Avoid / Overheated / Weak Setup"

    # Override 2: if no clean stop derivable, do not recommend Strong Buy
    stop_missing = plan.stop_loss.price is None
    if stop_missing and score >= 70:
        return "Watch for Confirmation"

    # Override 3: low confidence plan → downgrade
    if plan.confidence_score < 0.4 and score >= 55:
        return "Watch for Confirmation"

    if score >= 85:
        return "Strong Buy Setup"
    if score >= 70:
        return "Buy on Pullback"
    if score >= 55:
        return "Watch for Confirmation"
    if score >= 40:
        return "Hold / No Immediate Entry"
    return "Avoid / Overheated / Weak Setup"


def finalize(agg: AggregatedScore, stage: Stage, plan: TradePlan) -> FinalResult:
    raw_positive = agg.raw_positive()
    risk_score = agg.risk.total()
    # Map risk 0..10 → multiplier 1.0 down to 0.55
    risk_multiplier = clamp(rescale(risk_score, 0.0, 10.0, 1.0, 0.55), 0.55, 1.0)
    overheat_penalty = 15.0 if stage == "과열" else 0.0

    # Flow continuity adjustment: already baked into flow bucket, but we add
    # an extra small global adjustment so a broken flow signal also tilts the
    # final action.
    continuity_adj = 0.0
    if agg.flow.continuity <= 2.5:
        continuity_adj = -5.0
    elif agg.flow.continuity >= 5.5:
        continuity_adj = 2.0

    final = raw_positive * risk_multiplier - overheat_penalty + continuity_adj
    final = clamp(final, 0.0, 100.0)

    action = _action_for(final, stage, plan)
    summary = _compose_summary(final, raw_positive, risk_multiplier, overheat_penalty, action, stage)

    return FinalResult(
        total_score=round(final, 1),
        raw_score=round(raw_positive, 1),
        risk_multiplier=round(risk_multiplier, 2),
        overheat_penalty=overheat_penalty,
        action=action,
        summary=summary,
    )


def _compose_summary(
    final: float, raw: float, mult: float, penalty: float, action: Action, stage: Stage
) -> str:
    parts = [
        f"총점 {final:.1f} (원점수 {raw:.1f} × 리스크 게이트 {mult:.2f}",
    ]
    if penalty:
        parts[-1] += f" - 과열 {penalty:.0f}"
    parts[-1] += ")"
    parts.append(f"단계: {stage}")
    parts.append(f"판정: {action}")
    return " · ".join(parts)


def to_final_decision(result: FinalResult) -> FinalDecision:
    return FinalDecision(
        total_score=result.total_score,
        raw_score=result.raw_score,
        risk_multiplier=result.risk_multiplier,
        overheat_penalty=result.overheat_penalty,
        action=result.action,
        summary=result.summary,
    )
