"""Technical pattern detection and sub-scoring.

Each detector returns a (confidence 0..1, evidence strings) tuple. The
caller — the analysis service — treats detectors as independent features and
combines them into `TechnicalBuckets`. This mirrors the PDF's practice of
reading many small signals rather than one definitive pattern.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd

from backend.models.analysis_models import DetectedPattern
from backend.models.score_models import TechnicalBuckets
from backend.utils import ta_utils as ta
from backend.utils.math_utils import clamp, rescale


@dataclass
class TechnicalResult:
    buckets: TechnicalBuckets
    patterns: List[DetectedPattern]
    comment: str
    distance_from_ma20: float
    volume_ratio: float


# ---------- Individual detectors ----------

def detect_t_bottom(df: pd.DataFrame) -> Tuple[float, List[str]]:
    """T-bottom = prior decline → compression → doji/exhaustion → reversal.
    Returns (confidence, evidence).
    """
    if len(df) < 80:
        return 0.0, []
    ev: List[str] = []
    score = 0.0

    decline = ta.pct_return(df["close"], 60)
    if decline < -15:
        score += 0.35
        ev.append(f"직전 60일 하락률 {decline:.1f}%")
    elif decline < -5:
        score += 0.15
        ev.append(f"직전 60일 하락률 {decline:.1f}%")

    comp = ta.compression_ratio(df.tail(30), 20)
    if comp < 0.035:
        score += 0.25
        ev.append(f"저변동 압축 (σ/μ={comp:.3f})")
    elif comp < 0.06:
        score += 0.10
        ev.append(f"압축 구간 진입 (σ/μ={comp:.3f})")

    last = df.iloc[-1]
    if ta.is_doji(last):
        score += 0.20
        ev.append("도지 캔들 확인")
    elif ta.body_ratio(last) < 0.35 and ta.lower_shadow_ratio(last) > 0.35:
        score += 0.12
        ev.append("밑꼬리 긴 약세->강세 전환 캔들")

    # Anchor near local low
    low_60 = df["low"].tail(60).min()
    if low_60 > 0 and (last["close"] - low_60) / low_60 < 0.08:
        score += 0.15
        ev.append("60일 저점 근접")

    return clamp(score, 0.0, 1.0), ev


def detect_double_bottom(df: pd.DataFrame) -> Tuple[float, List[str]]:
    if len(df) < 80:
        return 0.0, []
    pivots = ta.find_pivots(df["close"].tail(120), left=4, right=4)
    lows = [p for p in pivots if p.kind == "low"]
    if len(lows) < 2:
        return 0.0, []
    last_low, prev_low = lows[-1], lows[-2]
    tolerance = abs(last_low.price - prev_low.price) / max(prev_low.price, 1e-6)
    spacing = last_low.idx - prev_low.idx
    if tolerance < 0.05 and 10 <= spacing <= 80:
        neckline = df["close"].iloc[prev_low.idx + 1 : last_low.idx].max()
        above_neckline = df["close"].iloc[-1] > neckline * 0.98
        ev = [f"두 저점 차이 {tolerance*100:.1f}%, 간격 {spacing}봉"]
        conf = 0.55
        if above_neckline:
            conf += 0.25
            ev.append("넥라인 근접/돌파")
        return clamp(conf, 0.0, 1.0), ev
    return 0.0, []


def detect_poking_breakout(df: pd.DataFrame) -> Tuple[float, List[str]]:
    """Poking = 주요 이평·저항을 관통하며 상승한 직후 구간. 당일 돌파 뿐만
    아니라 최근 ~15봉 내 돌파 후 구조 유지 상태도 포함한다.
    """
    if len(df) < 60:
        return 0.0, []
    close = df["close"]
    ma20_s = ta.sma(close, 20)
    ma60_s = ta.sma(close, 60)
    ma120_s = ta.sma(close, 120) if len(df) >= 120 else None
    ma20 = ma20_s.iloc[-1]
    ma60 = ma60_s.iloc[-1]
    ma120 = ma120_s.iloc[-1] if ma120_s is not None else np.nan
    last = df.iloc[-1]
    prev_high_40 = df["high"].iloc[-42:-2].max() if len(df) >= 42 else np.nan

    ev: List[str] = []
    score = 0.0

    # Was price below MA20 in the last 20 bars and is now above?
    if pd.notna(ma20) and last["close"] > ma20 and len(df) >= 20:
        was_below = (close.iloc[-20:-1] < ma20_s.iloc[-20:-1]).any()
        if was_below:
            score += 0.25
            ev.append("최근 20봉 내 20이평 상향 돌파")

    if pd.notna(ma60) and last["close"] > ma60 and len(df) >= 20:
        was_below_60 = (close.iloc[-20:-1] < ma60_s.iloc[-20:-1]).any()
        if was_below_60:
            score += 0.25
            ev.append("최근 20봉 내 60이평 상향 돌파")

    if pd.notna(ma120) and last["close"] > ma120:
        score += 0.1
        ev.append("120이평 위")
    if pd.notna(prev_high_40) and last["close"] > prev_high_40:
        score += 0.2
        ev.append("40일 고점 돌파")

    # Strong recent body. Look at the strongest of the last 10 bodies.
    recent = df.tail(10)
    strong_bodies = 0
    for _, bar in recent.iterrows():
        if ta.is_bullish(bar) and ta.body_ratio(bar) > 0.55:
            strong_bodies += 1
    if strong_bodies >= 2:
        score += 0.15
        ev.append(f"최근 10봉 중 강양봉 {strong_bodies}개")

    # Volume: compare recent 10-day avg to 40-day avg (breakout often sustains).
    if len(df) >= 40:
        recent_avg = df["volume"].iloc[-10:].mean()
        base_avg = df["volume"].iloc[-40:-10].mean()
        if base_avg > 0:
            vr = recent_avg / base_avg
            if vr > 1.5:
                score += 0.15
                ev.append(f"최근 10봉 거래량 {vr:.1f}배")
            elif vr > 1.15:
                score += 0.08
                ev.append(f"최근 10봉 거래량 {vr:.1f}배")

    return clamp(score, 0.0, 1.0), ev


def detect_overheating(df: pd.DataFrame) -> Tuple[float, List[str]]:
    if len(df) < 30:
        return 0.0, []
    ev: List[str] = []
    score = 0.0

    dist20 = ta.distance_from_ma(df, 20)
    if dist20 > 30:
        score += 0.5
        ev.append(f"20이평 이격 +{dist20:.1f}%")
    elif dist20 > 15:
        score += 0.25
        ev.append(f"20이평 이격 +{dist20:.1f}%")

    # Consecutive expansion days
    closes = df["close"].tail(10).to_numpy()
    up = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i - 1] * 1.03)
    if up >= 4:
        score += 0.3
        ev.append(f"최근 10일 중 3% 이상 양봉 {up}회")

    ret_20 = ta.pct_return(df["close"], 20)
    if ret_20 > 40:
        score += 0.3
        ev.append(f"20일 상승률 +{ret_20:.1f}%")
    elif ret_20 > 20:
        score += 0.12
        ev.append(f"20일 상승률 +{ret_20:.1f}%")

    return clamp(score, 0.0, 1.0), ev


def detect_reverse_accumulation(df: pd.DataFrame) -> Tuple[float, List[str]]:
    """역배열재매집 = 이전 상승 이후 조정/횡보 중 거래량 수축, 주요 이평 지지."""
    if len(df) < 120:
        return 0.0, []
    ev: List[str] = []
    score = 0.0
    prior = ta.pct_return(df["close"].iloc[:-40], 60) if len(df) > 100 else 0.0
    recent = ta.pct_return(df["close"], 30)
    if prior > 15 and -15 < recent < 5:
        score += 0.4
        ev.append(f"선행 랠리 +{prior:.1f}% 후 최근 30일 {recent:+.1f}%")
    vr_recent = df["volume"].tail(20).mean()
    vr_prior = df["volume"].iloc[-60:-20].mean()
    if vr_prior > 0 and vr_recent / vr_prior < 0.8:
        score += 0.3
        ev.append("거래량 수축 구간")
    ma60 = ta.sma(df["close"], 60).iloc[-1]
    if pd.notna(ma60) and 0 <= (df["close"].iloc[-1] - ma60) / ma60 < 0.07:
        score += 0.3
        ev.append("60이평 지지 근접")
    return clamp(score, 0.0, 1.0), ev


# ---------- Aggregator ----------

def analyze(df: pd.DataFrame) -> TechnicalResult:
    """Run all detectors and collapse into `TechnicalBuckets` + patterns list."""
    buckets = TechnicalBuckets()
    patterns: List[DetectedPattern] = []

    t_conf, t_ev = detect_t_bottom(df)
    if t_conf > 0.2:
        patterns.append(DetectedPattern(name="T바닥", confidence=t_conf, evidence=t_ev))
    dbl_conf, dbl_ev = detect_double_bottom(df)
    if dbl_conf > 0.4:
        patterns.append(DetectedPattern(name="쌍바닥", confidence=dbl_conf, evidence=dbl_ev))
    poking_conf, poking_ev = detect_poking_breakout(df)
    if poking_conf > 0.3:
        patterns.append(DetectedPattern(name="포킹돌파", confidence=poking_conf, evidence=poking_ev))
    over_conf, over_ev = detect_overheating(df)
    if over_conf > 0.25:
        patterns.append(DetectedPattern(name="과열", confidence=over_conf, evidence=over_ev))
    rev_conf, rev_ev = detect_reverse_accumulation(df)
    if rev_conf > 0.3:
        patterns.append(DetectedPattern(name="역배열재매집", confidence=rev_conf, evidence=rev_ev))

    # Base reversal bucket: take max of T-bottom / double bottom, max 8.
    base = max(t_conf, dbl_conf * 0.9, rev_conf * 0.7) * 8.0
    buckets.base_reversal = clamp(base, 0.0, 8.0)

    # Candle quality
    last = df.iloc[-1]
    candle = 0.0
    if ta.is_bullish(last):
        candle += 1.5
    if ta.body_ratio(last) > 0.5:
        candle += 1.5
    if ta.lower_shadow_ratio(last) > 0.3:
        candle += 1.0
    if ta.is_doji(last) and t_conf > 0.3:
        candle += 2.0
    buckets.candle_quality = clamp(candle, 0.0, 5.0)

    # MA structure
    buckets.ma_structure = clamp(ta.ma_alignment_score(df) * 5.0, 0.0, 5.0)

    # Breakout + confirmation
    buckets.breakout_confirm = clamp(poking_conf * 6.0, 0.0, 6.0)

    # Volume quality: 10-day vs 40-day, which captures sustained breakouts.
    if len(df) >= 40:
        recent_avg = df["volume"].iloc[-10:].mean()
        base_avg = df["volume"].iloc[-40:-10].mean()
        vr = float(recent_avg / base_avg) if base_avg else 1.0
    else:
        vr = ta.volume_ratio(df, 20)
    buckets.volume_quality = clamp(rescale(vr, 0.9, 2.0, 0.0, 4.0), 0.0, 4.0)

    # Overheating penalty (max 2)
    buckets.overheat_penalty = clamp(over_conf * 2.0, 0.0, 2.0)

    dist20 = ta.distance_from_ma(df, 20)
    comment = _compose_comment(buckets, patterns, dist20, vr)

    return TechnicalResult(
        buckets=buckets,
        patterns=patterns,
        comment=comment,
        distance_from_ma20=dist20,
        volume_ratio=vr,
    )


def _compose_comment(
    buckets: TechnicalBuckets,
    patterns: List[DetectedPattern],
    dist20: float,
    vr: float,
) -> str:
    parts: List[str] = []
    if patterns:
        parts.append("감지 패턴: " + ", ".join(p.name for p in patterns))
    else:
        parts.append("유의미한 패턴 없음")
    parts.append(f"20이평 이격 {dist20:+.1f}%")
    parts.append(f"거래량 {vr:.1f}배")
    if buckets.overheat_penalty > 1.0:
        parts.append("과열 페널티 적용 — 진입 추격 자제")
    return " · ".join(parts)
