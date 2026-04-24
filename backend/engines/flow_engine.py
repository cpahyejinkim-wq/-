"""Flow-stage engine.

Instead of tagging a chart as one pattern, we ask: where in the PDF's
canonical flow is this stock right now, and did it *arrive* here in a natural
sequence? The continuity score rewards stocks where the previous regime was
the natural predecessor of the current regime (e.g. T바닥 → 포킹), and
penalizes jumps that imply speculation or a broken flow.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd

from backend.models.analysis_models import Stage, StageAnalysis
from backend.models.score_models import FlowBuckets
from backend.utils import ta_utils as ta
from backend.utils.math_utils import clamp


# Canonical order per PDF philosophy. Used for continuity scoring.
_STAGE_ORDER: List[Stage] = [
    "관찰",
    "T바닥",
    "포킹",
    "펌핑",
    "랠리",
    "역배열재매집",
    "재랠리",
    "과열",
]

# Entry-quality weights. Early constructive stages get high weight; late and
# overheated stages get low weight.
_ENTRY_WEIGHTS = {
    "관찰": 0.30,
    "T바닥": 0.95,
    "포킹": 1.00,
    "펌핑": 0.80,
    "랠리": 0.55,
    "역배열재매집": 0.75,
    "재랠리": 0.85,
    "과열": 0.10,
}


@dataclass
class FlowResult:
    stage: Stage
    prior_stage: Stage
    buckets: FlowBuckets
    comment: str


def _classify_stage(df: pd.DataFrame, tail_from: int = 0) -> Stage:
    """Classify the stage at `df.iloc[-1 - tail_from]`."""
    if tail_from > 0:
        df = df.iloc[:-tail_from]
    if len(df) < 60:
        return "관찰"

    close = df["close"]
    ma5 = ta.sma(close, 5).iloc[-1]
    ma20 = ta.sma(close, 20).iloc[-1]
    ma60 = ta.sma(close, 60).iloc[-1]
    last = close.iloc[-1]

    dist20 = ta.distance_from_ma(df, 20)
    ret_5 = ta.pct_return(close, 5)
    ret_20 = ta.pct_return(close, 20)
    ret_60 = ta.pct_return(close, 60)
    comp = ta.compression_ratio(df.tail(30), 20)

    # Overheated: far from MA20 OR fast 20d momentum OR parabolic last 5 days OR
    # sustained 60d run-up (40%+). The last trigger captures cases where the
    # stock has clearly extended even if the final bar happens to be a pause.
    if (
        dist20 > 18
        or ret_20 > 22
        or (ret_5 > 12 and dist20 > 10)
        or ret_60 > 40
    ):
        return "과열"

    # Early reversal: compressed, near local low, post-decline
    low_60 = df["low"].tail(60).min()
    near_low = low_60 > 0 and (last - low_60) / low_60 < 0.10
    prior_decline = ret_60 < -8
    if near_low and prior_decline and comp < 0.06:
        return "T바닥"

    # Poking: price is above the structural MAs, crossed up within last 15 bars,
    # and the move is not yet a sustained rally. Tolerant of short post-break pauses.
    was_below_20 = (close.iloc[-20:-2] < ta.sma(close, 20).iloc[-20:-2]).any() if len(df) >= 25 else False
    if (
        pd.notna(ma20) and pd.notna(ma60)
        and last > ma20 and last > ma60
        and was_below_20
        and 3 < ret_20 < 15
    ):
        return "포킹"

    # Reverse accumulation during rally
    prior_rally = ta.pct_return(close.iloc[:-30], 60) > 15 if len(df) > 90 else False
    if prior_rally and -10 < ret_20 < 5 and pd.notna(ma60) and abs(last - ma60) / ma60 < 0.08:
        if ret_5 > 2 and ret_20 > 0:
            return "재랠리"
        return "역배열재매집"

    # Pumping: recent short-term acceleration, not yet overheated
    if ret_5 > 3 and ret_20 > 7 and pd.notna(ma5) and last > ma5:
        return "펌핑"

    # Rally: uptrend persistence without fresh acceleration
    if pd.notna(ma20) and ma20 > (ma60 if pd.notna(ma60) else ma20) and last > ma20 and ret_60 > 5:
        return "랠리"

    return "관찰"


def _continuity_score(current: Stage, prior: Stage) -> Tuple[float, str]:
    """Return (0..6, comment)."""
    # Natural transitions per PDF flow.
    natural = {
        "관찰": {"관찰", "T바닥"},
        "T바닥": {"관찰", "T바닥"},
        "포킹": {"T바닥", "관찰", "포킹"},
        "펌핑": {"포킹", "펌핑", "T바닥"},
        "랠리": {"펌핑", "포킹", "랠리"},
        "역배열재매집": {"랠리", "펌핑", "역배열재매집"},
        "재랠리": {"역배열재매집", "재랠리", "랠리"},
        "과열": {"랠리", "재랠리", "펌핑", "과열"},
    }
    if prior in natural.get(current, set()):
        return 6.0, f"{prior} → {current} 자연스러운 전개"
    if current == prior:
        return 4.5, f"{current} 지속 (정체)"
    return 2.0, f"{prior} → {current} 비정상 전환 — 흐름 단절 의심"


def analyze(df: pd.DataFrame) -> FlowResult:
    if len(df) < 80:
        return FlowResult(
            stage="관찰",
            prior_stage="관찰",
            buckets=FlowBuckets(stage_appropriateness=2.0, continuity=2.0),
            comment="데이터 부족 — 관찰",
        )

    current = _classify_stage(df)
    # Prior stage: look 10~15 trading days back to see where the flow came from.
    prior = _classify_stage(df, tail_from=12)

    buckets = FlowBuckets()
    buckets.stage_appropriateness = clamp(_ENTRY_WEIGHTS.get(current, 0.3) * 8.0, 0.0, 8.0)
    cont_score, cont_note = _continuity_score(current, prior)
    buckets.continuity = cont_score

    # Late-stage penalty
    if current == "과열":
        buckets.late_stage_penalty = 6.0
    elif current == "랠리":
        buckets.late_stage_penalty = 2.5
    elif current == "재랠리":
        buckets.late_stage_penalty = 1.5
    else:
        buckets.late_stage_penalty = 0.0

    comment = f"현재 단계: {current}. {cont_note}."
    if current == "과열":
        comment += " 추격 진입 금지, 리셋 대기."
    elif current in {"T바닥", "포킹"}:
        comment += " 저비용 진입 구간, 확인봉 대응 권장."
    elif current == "재랠리":
        comment += " 재매집 이후 재랠리 초입, 분할 진입 유효."

    return FlowResult(stage=current, prior_stage=prior, buckets=buckets, comment=comment)


def to_stage_analysis(result: FlowResult) -> StageAnalysis:
    return StageAnalysis(
        stage=result.stage,
        stage_score=result.buckets.stage_appropriateness,
        continuity_score=result.buckets.continuity,
        comment=result.comment,
    )
