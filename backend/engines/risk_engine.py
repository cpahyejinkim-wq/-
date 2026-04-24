"""Risk engine.

Higher score here = MORE risk. In `scoring_engine.finalize` the 0..10 risk
total is converted into a multiplicative gate on the raw positive score, so a
technically beautiful setup in an overheated regime still lands at a modest
final score. This mirrors the PDF's practical stance that risk control
dominates signal quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from backend.models.analysis_models import RiskAnalysis
from backend.models.provider_models import MacroSnapshot
from backend.models.score_models import RiskBuckets
from backend.utils import ta_utils as ta
from backend.utils.math_utils import clamp, rescale


@dataclass
class RiskResult:
    buckets: RiskBuckets
    overextension_risk: str
    volatility_risk: str
    event_risk: str
    liquidity_risk: str
    breakout_failure_risk: str
    comment: str


def analyze(df: pd.DataFrame, macro: MacroSnapshot, news_count: int, news_negative: int) -> RiskResult:
    buckets = RiskBuckets()

    # Volatility (ATR % of price)
    atr = ta.atr(df, 14).iloc[-1] if len(df) > 15 else 0.0
    last = df["close"].iloc[-1]
    atr_pct = (atr / last * 100.0) if last > 0 else 0.0
    buckets.volatility = clamp(rescale(atr_pct, 1.5, 6.5, 0.0, 2.0), 0.0, 2.0)
    if atr_pct > 5:
        vol_tag = f"고변동 (ATR {atr_pct:.1f}%)"
    elif atr_pct > 3:
        vol_tag = f"변동성 보통 (ATR {atr_pct:.1f}%)"
    else:
        vol_tag = f"저변동 (ATR {atr_pct:.1f}%)"

    # Overextension
    dist20 = ta.distance_from_ma(df, 20)
    buckets.overextension = clamp(rescale(dist20, 5.0, 35.0, 0.0, 3.0), 0.0, 3.0)
    if dist20 > 25:
        over_tag = f"20이평 대비 과대 이격 (+{dist20:.1f}%)"
        buckets.flags.append("과열 이격")
    elif dist20 > 12:
        over_tag = f"이격 다소 확대 (+{dist20:.1f}%)"
    else:
        over_tag = f"이격 양호 ({dist20:+.1f}%)"

    # Event / news risk
    if news_negative >= 2:
        buckets.event_news = 2.0
        ev_tag = "부정 뉴스 다수 — 이벤트 리스크"
        buckets.flags.append("부정 뉴스 다수")
    elif news_negative == 1:
        buckets.event_news = 1.0
        ev_tag = "부정 뉴스 감지"
    elif news_count == 0:
        buckets.event_news = 0.5
        ev_tag = "뉴스 플로우 부재 — 촉매 불명확"
    else:
        buckets.event_news = 0.2
        ev_tag = "뉴스 플로우 정상"
    if macro.base_rate_direction == "hiking":
        buckets.event_news = min(2.0, buckets.event_news + 0.4)
        ev_tag += " · 금리 인상기 주의"
        buckets.flags.append("금리 인상기")

    # Liquidity
    avg_vol = df["volume"].tail(20).mean() if len(df) >= 20 else 0
    turnover = avg_vol * last
    if turnover < 1_000_000_000:  # ~10억원
        buckets.liquidity = 1.0
        liq_tag = "거래대금 낮음 — 슬리피지 주의"
        buckets.flags.append("거래대금 낮음")
    elif turnover < 5_000_000_000:
        buckets.liquidity = 0.5
        liq_tag = "거래대금 보통"
    else:
        buckets.liquidity = 0.1
        liq_tag = "거래대금 양호"

    # Crowded / failed breakout risk
    vr = ta.volume_ratio(df, 20)
    recent_ret_5 = ta.pct_return(df["close"], 5)
    if vr > 3.0 and recent_ret_5 > 15:
        buckets.crowding_failure = 2.0
        fail_tag = "급등 직후 — 실패 돌파 리스크"
        buckets.flags.append("실패 돌파 리스크")
    elif dist20 > 20 and vr > 2.0:
        buckets.crowding_failure = 1.5
        fail_tag = "과열 + 고거래량 — 피로 구간"
    elif dist20 < -10 and vr < 0.7:
        buckets.crowding_failure = 1.0
        fail_tag = "약세 + 거래 위축"
    else:
        buckets.crowding_failure = 0.3
        fail_tag = "정상 구간"

    comment = (
        f"{vol_tag} · {over_tag} · {ev_tag} · {liq_tag} · {fail_tag}"
    )
    return RiskResult(
        buckets=buckets,
        volatility_risk=vol_tag,
        overextension_risk=over_tag,
        event_risk=ev_tag,
        liquidity_risk=liq_tag,
        breakout_failure_risk=fail_tag,
        comment=comment,
    )


def to_risk_analysis(result: RiskResult) -> RiskAnalysis:
    return RiskAnalysis(
        score=result.buckets.total(),
        overextension_risk=result.overextension_risk,
        volatility_risk=result.volatility_risk,
        event_risk=result.event_risk,
        liquidity_risk=result.liquidity_risk,
        breakout_failure_risk=result.breakout_failure_risk,
        warning_flags=result.buckets.flags,
        comment=result.comment,
    )
