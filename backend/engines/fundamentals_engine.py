"""Fundamental direction engine.

The PDF's stance is that *direction* beats *level*: a company improving from
mediocre is often a better setup than a company with high-but-decelerating
metrics. The dominant signal is "영업이익 증가율이 매출 증가율을 상회하는가"
(operating leverage kicking in).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from backend.models.analysis_models import FundamentalAnalysis
from backend.models.provider_models import FundamentalsSnapshot
from backend.models.score_models import FundamentalBuckets
from backend.utils.math_utils import clamp


@dataclass
class FundamentalResult:
    buckets: FundamentalBuckets
    snapshot_available: bool
    revenue_trend: str
    op_profit_trend: str
    earnings_leverage: str
    margin_trend: str
    debt_health: str
    estimate_revision: Optional[str]
    comment: str


def _slope(seq: Optional[List[float]]) -> Tuple[float, str]:
    """Return (last value, textual trend) for a YoY series."""
    if not seq:
        return 0.0, "데이터 없음"
    last = seq[-1]
    if len(seq) >= 3:
        earlier = sum(seq[:-2]) / max(1, len(seq) - 2)
        delta = last - earlier
    else:
        delta = last
    if last > 15 and delta > 0:
        tag = "가속 성장"
    elif last > 5 and delta >= 0:
        tag = "상승"
    elif last > 0:
        tag = "완만한 상승"
    elif last > -5:
        tag = "정체"
    else:
        tag = "감소"
    return last, f"{tag} ({last:+.1f}% YoY)"


def analyze(snap: FundamentalsSnapshot) -> FundamentalResult:
    buckets = FundamentalBuckets()
    if not snap.available:
        return FundamentalResult(
            buckets=buckets,
            snapshot_available=False,
            revenue_trend="데이터 없음",
            op_profit_trend="데이터 없음",
            earnings_leverage="데이터 없음",
            margin_trend="데이터 없음",
            debt_health="데이터 없음",
            estimate_revision=None,
            comment="재무 데이터 미제공 — 펀더멘털 점수 보수적으로 0 처리",
        )

    rev_last, rev_trend = _slope(snap.revenue_yoy)
    op_last, op_trend = _slope(snap.op_profit_yoy)

    # Revenue growth bucket (max 3)
    if rev_last > 15:
        buckets.revenue_growth = 3.0
    elif rev_last > 5:
        buckets.revenue_growth = 2.2
    elif rev_last > 0:
        buckets.revenue_growth = 1.2
    elif rev_last > -5:
        buckets.revenue_growth = 0.5

    # Op profit growth bucket (max 4)
    if op_last > 25:
        buckets.op_profit_growth = 4.0
    elif op_last > 10:
        buckets.op_profit_growth = 3.0
    elif op_last > 0:
        buckets.op_profit_growth = 1.5
    elif op_last > -10:
        buckets.op_profit_growth = 0.5

    # Operating leverage bucket (max 3)
    if op_last - rev_last > 10:
        buckets.op_gt_revenue = 3.0
        leverage_note = "영업이익 증가율이 매출 증가율을 크게 상회 — 레버리지 발현"
    elif op_last > rev_last:
        buckets.op_gt_revenue = 2.0
        leverage_note = "영업이익 증가율 > 매출 증가율"
    elif op_last >= rev_last - 3:
        buckets.op_gt_revenue = 0.8
        leverage_note = "성장률 균형"
    else:
        buckets.op_gt_revenue = 0.0
        leverage_note = "수익성 악화 (매출 대비 영업이익 둔화)"

    # Margin (max 2)
    margin_trend_str = "데이터 없음"
    if snap.op_margin and len(snap.op_margin) >= 2:
        margin_diff = snap.op_margin[-1] - snap.op_margin[0]
        if margin_diff > 3:
            buckets.margin = 2.0
            margin_trend_str = f"마진 확대 (+{margin_diff:.1f}%p)"
        elif margin_diff > 0:
            buckets.margin = 1.2
            margin_trend_str = f"마진 개선 (+{margin_diff:.1f}%p)"
        elif margin_diff > -2:
            buckets.margin = 0.5
            margin_trend_str = "마진 보합"
        else:
            buckets.margin = 0.0
            margin_trend_str = f"마진 악화 ({margin_diff:.1f}%p)"

    # Leverage / balance sheet (max 2)
    debt_note = "데이터 없음"
    if snap.debt_to_equity is not None:
        dte = snap.debt_to_equity
        if dte < 50:
            buckets.leverage = 2.0
            debt_note = f"부채비율 양호 ({dte:.1f}%)"
        elif dte < 100:
            buckets.leverage = 1.2
            debt_note = f"부채비율 보통 ({dte:.1f}%)"
        elif dte < 200:
            buckets.leverage = 0.5
            debt_note = f"부채비율 부담 ({dte:.1f}%)"
        else:
            buckets.leverage = 0.0
            debt_note = f"부채비율 과다 ({dte:.1f}%)"

    # Estimate revision (max 1)
    est_note: Optional[str] = None
    if snap.estimate_revision_pct is not None:
        er = snap.estimate_revision_pct
        if er > 2:
            buckets.estimate_revision = 1.0
            est_note = f"추정치 상향 (+{er:.1f}%)"
        elif er > 0:
            buckets.estimate_revision = 0.5
            est_note = f"추정치 소폭 상향 (+{er:.1f}%)"
        elif er > -2:
            buckets.estimate_revision = 0.2
            est_note = "추정치 보합"
        else:
            buckets.estimate_revision = 0.0
            est_note = f"추정치 하향 ({er:.1f}%)"

    comment_parts = [
        f"매출 {rev_trend}",
        f"영업이익 {op_trend}",
        leverage_note,
        margin_trend_str,
        debt_note,
    ]
    if est_note:
        comment_parts.append(est_note)
    if snap.note:
        comment_parts.append(snap.note)

    return FundamentalResult(
        buckets=buckets,
        snapshot_available=True,
        revenue_trend=rev_trend,
        op_profit_trend=op_trend,
        earnings_leverage=leverage_note,
        margin_trend=margin_trend_str,
        debt_health=debt_note,
        estimate_revision=est_note,
        comment=" · ".join(comment_parts),
    )


def to_fundamental_analysis(result: FundamentalResult) -> FundamentalAnalysis:
    return FundamentalAnalysis(
        score=result.buckets.total(),
        revenue_trend=result.revenue_trend,
        op_profit_trend=result.op_profit_trend,
        earnings_leverage=result.earnings_leverage,
        margin_trend=result.margin_trend,
        debt_health=result.debt_health,
        estimate_revision=result.estimate_revision,
        comment=result.comment,
        data_available=result.snapshot_available,
    )
