"""Multi-timeframe alignment.

Resamples daily OHLCV to weekly (Fri-close) and monthly, then classifies each
timeframe with a shared set of labels. Final alignment_score rewards the
configuration where higher timeframes (monthly / weekly) are supportive and
daily timing is early, which is the PDF's core stance: "진입은 일봉, 방향은
주·월봉".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pandas as pd

from backend.models.analysis_models import TimeframeAnalysis
from backend.models.score_models import TimeframeBuckets
from backend.utils import ta_utils as ta
from backend.utils.math_utils import clamp


@dataclass
class TimeframeResult:
    buckets: TimeframeBuckets
    monthly_state: str
    weekly_state: str
    daily_state: str
    comment: str


def _score_higher_frame(df: pd.DataFrame) -> Tuple[float, str]:
    """Score 0..5 for monthly / weekly 'supportive reversal or uptrend'."""
    if len(df) < 8:
        return 0.0, "데이터 부족"
    state = ta.trend_state(df)
    comp = ta.compression_ratio(df, 20) if len(df) >= 20 else 0.1
    close = df["close"]
    ret_recent = ta.pct_return(close, min(6, len(df) - 1))
    if state == "정배열상승":
        return 5.0, "정배열 상승 지지"
    if state == "단기상승" and ret_recent > 0:
        return 3.8, "단기 상승 지지"
    if state == "횡보" and comp < 0.06:
        return 3.0, "베이스 형성 (압축)"
    if state == "단기하락":
        return 1.5, "단기 약세 — 제한적"
    if state == "역배열하락":
        return 0.5, "역배열 약세 — 상위 타임프레임 부담"
    return 2.0, "혼조 구간"


def _score_daily(df: pd.DataFrame) -> Tuple[float, str]:
    if len(df) < 20:
        return 0.0, "데이터 부족"
    ev_score = 0.0
    state = ta.trend_state(df)
    last = df.iloc[-1]
    body = ta.body_ratio(last)
    bullish = ta.is_bullish(last)
    vr = ta.volume_ratio(df, 20)

    if state in {"정배열상승", "단기상승"}:
        ev_score += 2.0
    if bullish and body > 0.5:
        ev_score += 1.2
    if vr > 1.5:
        ev_score += 1.0
    if ta.is_doji(last):
        ev_score += 0.8  # doji near support is a valid timing signal
    ev_score = clamp(ev_score, 0.0, 5.0)
    state_label = {
        2.0: "진입 타이밍 양호",
        1.5: "관찰 대기",
    }
    if ev_score >= 3.5:
        label = "확인봉 출현 — 진입 타이밍 양호"
    elif ev_score >= 2.0:
        label = "확인봉 대기"
    else:
        label = "진입 타이밍 부적합"
    return ev_score, label


def analyze(daily: pd.DataFrame) -> TimeframeResult:
    weekly = ta.resample(daily, "W-FRI")
    monthly = ta.resample(daily, "ME")

    m_score, m_label = _score_higher_frame(monthly)
    w_score, w_label = _score_higher_frame(weekly)
    d_score, d_label = _score_daily(daily)

    buckets = TimeframeBuckets(monthly=m_score, weekly=w_score, daily=d_score)

    # Penalty: daily hot but higher frames unsupportive.
    downgrade = ""
    if d_score >= 3.5 and (m_score < 2.0 or w_score < 2.0):
        buckets.daily = max(0.0, buckets.daily - 1.5)
        downgrade = " 상위 타임프레임 부정적 — 일봉 타이밍 신뢰도 하향."

    comment = (
        f"월봉 [{m_label}] · 주봉 [{w_label}] · 일봉 [{d_label}]."
        + downgrade
    )
    return TimeframeResult(
        buckets=buckets,
        monthly_state=m_label,
        weekly_state=w_label,
        daily_state=d_label,
        comment=comment,
    )


def to_timeframe_analysis(result: TimeframeResult) -> TimeframeAnalysis:
    return TimeframeAnalysis(
        monthly_state=result.monthly_state,
        weekly_state=result.weekly_state,
        daily_state=result.daily_state,
        alignment_score=result.buckets.total(),
        comment=result.comment,
    )
