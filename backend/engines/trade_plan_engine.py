"""Trade-plan generation.

Produces concrete numbers — buy zones, stop-loss, take-profits — derived from
actual market structure (support/resistance pivots + moving averages + ATR),
not from constants. If a reliable structural stop cannot be derived, the plan
explicitly says so and lowers `confidence_score` rather than emitting a fake
number.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from backend.models.analysis_models import Stage, TradeLevel, TradePlan
from backend.utils import ta_utils as ta
from backend.utils.math_utils import nearest_above, nearest_below


def _round(price: Optional[float]) -> Optional[float]:
    if price is None:
        return None
    # Korean tick size approximation — one decimal is fine for display; real
    # tick table will plug in via formatters in the frontend.
    return round(float(price), 2)


def generate(df: pd.DataFrame, stage: Stage, risk_score: float) -> TradePlan:
    last = float(df["close"].iloc[-1])
    supports, resistances = ta.support_resistance_levels(df, lookback=120)
    ma5 = ta.sma(df["close"], 5).iloc[-1]
    ma20 = ta.sma(df["close"], 20).iloc[-1]
    ma60 = ta.sma(df["close"], 60).iloc[-1]
    atr14 = ta.atr(df, 14).iloc[-1] if len(df) > 15 else last * 0.02

    # Buy zone 1: immediate high-quality support (MA5/20 or recent pivot)
    buy1_candidates: List[float] = [v for v in [ma5, ma20] if pd.notna(v) and v < last]
    near_piv_support = nearest_below(supports, last)
    if near_piv_support:
        buy1_candidates.append(near_piv_support)
    buy1 = max(buy1_candidates) if buy1_candidates else None
    buy1_rationale = _buy1_rationale(buy1, ma5, ma20, near_piv_support)

    # Buy zone 2: deeper structural support (MA60 or further pivot)
    buy2_candidates: List[float] = [v for v in [ma60] if pd.notna(v) and v < (buy1 or last) * 0.99]
    further_support = None
    for s in sorted(supports, reverse=True):
        if buy1 and s < buy1 * 0.97:
            further_support = s
            break
        if not buy1 and s < last * 0.95:
            further_support = s
            break
    if further_support:
        buy2_candidates.append(further_support)
    buy2 = max(buy2_candidates) if buy2_candidates else None
    buy2_rationale = _buy2_rationale(buy2, ma60, further_support)

    # Stop loss: below the furthest-out support or 1.5 ATR below entry pivot
    stop_candidates: List[float] = []
    low_pivot = df["low"].tail(30).min()
    stop_candidates.append(float(low_pivot) * 0.98)
    if buy2:
        stop_candidates.append(buy2 - 1.5 * atr14)
    elif buy1:
        stop_candidates.append(buy1 - 1.5 * atr14)
    stop = min(stop_candidates) if stop_candidates else None
    # If stop is within 1% of entry, structure is too tight to trust.
    if stop and buy1 and (buy1 - stop) / buy1 < 0.01:
        stop = None
        stop_rationale = "구조적 손절가 도출 불가 — 진입 보류 권장"
    else:
        stop_rationale = (
            f"직전 30봉 저점 {low_pivot:.0f} 하방 또는 진입가 대비 1.5 ATR 이격"
            if stop else "손절 레벨 불명확 — 확신도 하향"
        )

    # Take profits: nearest resistance + next resistance or measured move.
    tp1 = nearest_above(resistances, last) if resistances else None
    if not tp1:
        tp1 = last * 1.08  # heuristic 8% if no structural target
    tp1_rationale = "최근 저항선" if nearest_above(resistances, last) else "기술적 목표 (+8%)"

    tp2 = None
    if resistances:
        above = sorted([r for r in resistances if r > (tp1 or last) * 1.02])
        if above:
            tp2 = above[0]
            tp2_rationale = "상위 저항선"
    if tp2 is None:
        # Measured move from nearest support to current
        support_ref = nearest_below(supports, last) or last * 0.9
        tp2 = last + (last - support_ref) * 1.5
        tp2_rationale = "측정이동 목표 (지지-현재 폭의 1.5배)"

    # Invalidation
    if stage == "과열":
        invalidation = "과열 구간 — 신규 진입 금지. 20이평까지 리셋 후 재평가."
    elif stop:
        invalidation = f"종가 {_round(stop):.0f} 이탈 시 셋업 무효"
    else:
        invalidation = "주요 지지 구조 붕괴 시 셋업 무효 (구체 레벨 없음)"

    # Position sizing
    if stage in {"T바닥", "포킹"}:
        sizing = "분할 매수 30/30/40 (확인봉, 눌림, 돌파 후 재테스트)"
    elif stage in {"펌핑", "재랠리"}:
        sizing = "눌림목 대응 40/60 — 추격 금지"
    elif stage == "과열":
        sizing = "신규 진입 금지 (기보유 시 트레일링 스탑)"
    elif stage == "역배열재매집":
        sizing = "관찰 매집 50% 선진입, 재랠리 확인 시 50% 추가"
    else:
        sizing = "관찰 대기 — 확인봉 출현 시 재평가"

    one_line = _one_line(stage, buy1, stop, tp1)

    # Confidence: penalized when stop missing, boosted when levels are clean
    confidence = 0.5
    if buy1 is not None:
        confidence += 0.15
    if stop is not None:
        confidence += 0.15
    if tp1 is not None and tp2 is not None:
        confidence += 0.1
    if stage in {"과열"}:
        confidence -= 0.35
    confidence -= min(0.25, (risk_score - 4.0) * 0.05) if risk_score > 4 else 0
    confidence = max(0.0, min(1.0, confidence))

    return TradePlan(
        current_price=_round(last) or last,
        detected_stage=stage,
        support_levels=[_round(s) for s in sorted(supports) if s is not None],  # type: ignore[misc]
        resistance_levels=[_round(r) for r in sorted(resistances) if r is not None],  # type: ignore[misc]
        buy_zone_1=TradeLevel(price=_round(buy1), rationale=buy1_rationale),
        buy_zone_2=TradeLevel(price=_round(buy2), rationale=buy2_rationale),
        stop_loss=TradeLevel(price=_round(stop), rationale=stop_rationale),
        take_profit_1=TradeLevel(price=_round(tp1), rationale=tp1_rationale),
        take_profit_2=TradeLevel(price=_round(tp2), rationale=tp2_rationale),
        invalidation_condition=invalidation,
        position_sizing_note=sizing,
        one_line_strategy=one_line,
        confidence_score=round(confidence, 2),
    )


def _buy1_rationale(buy1: Optional[float], ma5: float, ma20: float, support: Optional[float]) -> str:
    if buy1 is None:
        return "적정 1차 매수 구간 불분명"
    parts = []
    if pd.notna(ma5) and abs(buy1 - ma5) / ma5 < 0.01:
        parts.append("5일 이평 지지")
    if pd.notna(ma20) and abs(buy1 - ma20) / ma20 < 0.01:
        parts.append("20일 이평 지지")
    if support and abs(buy1 - support) / support < 0.01:
        parts.append("최근 피벗 지지")
    return (", ".join(parts) or "근접 구조적 지지") + " 근처 1차 진입"


def _buy2_rationale(buy2: Optional[float], ma60: float, support: Optional[float]) -> str:
    if buy2 is None:
        return "2차 매수 구간 없음 (구조적 추가 지지 부재)"
    parts = []
    if pd.notna(ma60) and abs(buy2 - ma60) / ma60 < 0.015:
        parts.append("60일 이평 지지")
    if support and abs(buy2 - support) / support < 0.015:
        parts.append("심층 피벗 지지")
    return (", ".join(parts) or "심층 지지") + " 근처 추가 매수"


def _one_line(stage: Stage, buy1: Optional[float], stop: Optional[float], tp1: Optional[float]) -> str:
    if stage == "과열":
        return "추격 금지. 20이평 리셋 후 재평가."
    if buy1 and stop and tp1:
        return f"{buy1:.0f} 분할 매수 / {stop:.0f} 손절 / 1차 목표 {tp1:.0f}"
    if buy1 and tp1:
        return f"{buy1:.0f} 분할 매수 / 1차 목표 {tp1:.0f} (손절 구조 불명확)"
    return "구조적 진입 레벨 불명확 — 확인봉 대기"
