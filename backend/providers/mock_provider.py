"""Deterministic synthetic data for Phase 1.

Each sample ticker is crafted so that the engines land on a specific flow
stage, so the full pipeline can be demonstrated end-to-end without any
network dependency. Trajectories are built from piecewise segments that mimic
the PDF's flow vocabulary:

    T바닥 → 포킹 → 펌핑 → 랠리 → 역배열재매집 → 재랠리 → 과열

Deterministic seeds keep output stable for tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from backend.models.provider_models import (
    FundamentalsSnapshot,
    MacroSnapshot,
    NewsHeadline,
    OHLCVBundle,
    PeerSnapshot,
    SymbolMeta,
    ThemeSnapshot,
)
from backend.providers.base_provider import BaseProvider


@dataclass
class _Segment:
    days: int
    drift_pct_per_day: float   # average daily drift, %
    vol_pct: float             # daily stdev, %
    volume_mult: float = 1.0


@dataclass
class _MockDef:
    ticker: str
    name: str
    market: str
    sector: str
    theme: str
    aliases: List[str]
    start_price: float
    segments: List[_Segment]
    peers: List[str]
    fundamentals: FundamentalsSnapshot
    news: List[NewsHeadline]
    seed: int


def _gen_ohlcv(defn: _MockDef, end_date: datetime) -> pd.DataFrame:
    rng = np.random.default_rng(defn.seed)
    total_days = sum(s.days for s in defn.segments)
    # Use business-day calendar so weekly/monthly resampling lines up naturally.
    dates = pd.bdate_range(end=end_date, periods=total_days)
    closes = np.zeros(total_days)
    volumes = np.zeros(total_days, dtype=int)
    price = defn.start_price
    idx = 0
    for seg in defn.segments:
        for _ in range(seg.days):
            shock = rng.normal(seg.drift_pct_per_day, seg.vol_pct) / 100.0
            price = max(price * (1 + shock), 0.01)
            closes[idx] = price
            base_vol = 500_000
            vol_noise = rng.normal(1.0, 0.2)
            volumes[idx] = int(max(10_000, base_vol * seg.volume_mult * vol_noise))
            idx += 1
    opens = np.concatenate([[closes[0]], closes[:-1]])
    # Intrabar range scales with local volatility; keep lows reasonable.
    daily_vol = np.abs(np.diff(np.concatenate([[closes[0]], closes]))) / closes
    daily_vol = np.clip(daily_vol, 0.005, 0.08)
    highs = np.maximum(opens, closes) * (1 + daily_vol * rng.uniform(0.3, 0.8, total_days))
    lows = np.minimum(opens, closes) * (1 - daily_vol * rng.uniform(0.3, 0.8, total_days))
    df = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=dates,
    )
    df.index.name = "date"
    return df


# ---------- Sample catalogue ----------

_HIST = lambda drift=0.0, vol=1.3, mult=1.0: _Segment(260, drift, vol, mult)  # ~1y history


def _defs() -> List[_MockDef]:
    return [
        # 1) 주봉 포킹 돌파 + 월봉 베이스 완성 — best-case setup
        _MockDef(
            ticker="900001",
            name="샘플반도체",
            market="KOSPI",
            sector="반도체",
            theme="AI 반도체",
            aliases=["샘플반도", "sample semi"],
            start_price=30000,
            segments=[
                _HIST(),                          # 이력
                _Segment(60, -0.15, 1.5, 0.9),   # 하락
                _Segment(80, 0.02, 0.9, 0.8),    # 베이스 횡보
                _Segment(30, 0.05, 1.1, 1.0),    # T바닥 반전 시도
                _Segment(10, 0.8, 1.5, 1.8),     # 포킹 돌파
                _Segment(5, 0.1, 1.0, 1.2),      # 돌파 후 눌림 대기
            ],
            peers=["샘플반도체장비", "샘플소재"],
            fundamentals=FundamentalsSnapshot(
                revenue_yoy=[-5, -2, 3, 8, 14, 21],
                op_profit_yoy=[-20, -8, 2, 15, 30, 48],
                op_margin=[6, 7, 9, 11, 13, 15],
                net_margin=[4, 5, 7, 9, 10, 12],
                debt_to_equity=45.2,
                current_ratio=1.8,
                estimate_revision_pct=4.5,
                note="영업이익 증가율이 매출 증가율을 앞섬",
            ),
            news=[
                NewsHeadline("HBM 공급 계약 확대 보도", source="전자신문", sentiment="positive"),
                NewsHeadline("3분기 실적 가이던스 상향", source="연합뉴스", sentiment="positive"),
            ],
            seed=11,
        ),
        # 2) T바닥 형성 중 (일봉 도지) — early but constructive
        _MockDef(
            ticker="900002",
            name="샘플바이오",
            market="KOSDAQ",
            sector="제약·바이오",
            theme="비만치료제",
            aliases=["샘바", "샘플 바이오"],
            start_price=22000,
            segments=[
                _HIST(drift=-0.05),
                _Segment(80, -0.25, 2.2, 1.0),   # 긴 하락
                _Segment(60, -0.02, 1.2, 0.7),   # 완만한 바닥 다지기
                _Segment(20, 0.03, 0.8, 0.6),    # 압축 (T바닥 컴프레션)
                _Segment(3, 0.2, 0.9, 1.3),      # 도지 + 소폭 반등
            ],
            peers=["샘플제약", "샘플의료기기"],
            fundamentals=FundamentalsSnapshot(
                revenue_yoy=[-3, -1, 2, 4, 6, 8],
                op_profit_yoy=[-15, -9, -4, 0, 5, 10],
                op_margin=[-2, -1, 1, 2, 3, 4],
                net_margin=[-4, -3, -1, 0, 1, 2],
                debt_to_equity=70.1,
                current_ratio=1.2,
                estimate_revision_pct=1.0,
                note="흑자 전환 구간, 방향성 긍정적이나 레버리지 주의",
            ),
            news=[
                NewsHeadline("임상 2상 중간 결과 긍정적", source="이데일리", sentiment="positive"),
            ],
            seed=22,
        ),
        # 3) 과열 — parabolic, stretched from MAs
        _MockDef(
            ticker="900003",
            name="샘플2차전지",
            market="KOSDAQ",
            sector="2차전지",
            theme="LFP 배터리",
            aliases=["샘2차", "샘플배터리"],
            start_price=18000,
            segments=[
                _HIST(),
                _Segment(60, 0.0, 1.0, 0.8),
                _Segment(40, 0.15, 1.3, 1.1),    # 랠리 초입
                _Segment(30, 0.35, 1.6, 1.4),    # 펌핑
                _Segment(30, 0.9, 2.5, 2.2),     # 과열 구간
                _Segment(5, 1.2, 3.0, 3.0),      # 마지막 급등
            ],
            peers=["샘플양극재", "샘플음극재"],
            fundamentals=FundamentalsSnapshot(
                revenue_yoy=[10, 8, 5, 3, 1, -1],
                op_profit_yoy=[5, 2, -2, -5, -8, -12],
                op_margin=[10, 9, 8, 6, 5, 4],
                net_margin=[8, 7, 6, 5, 3, 2],
                debt_to_equity=95.3,
                current_ratio=1.05,
                estimate_revision_pct=-2.8,
                note="수급 주도 랠리, 펀더멘털 악화 구간",
            ),
            news=[
                NewsHeadline("과열 경고…단기 급등 부담", source="한국경제", sentiment="negative"),
            ],
            seed=33,
        ),
        # 4) 역배열 재매집 후 재랠리 진입
        _MockDef(
            ticker="900004",
            name="샘플조선",
            market="KOSPI",
            sector="조선",
            theme="친환경선박",
            aliases=["샘조선"],
            start_price=45000,
            segments=[
                _HIST(),
                _Segment(40, 0.1, 1.0, 0.9),
                _Segment(25, 0.4, 1.3, 1.3),     # 1차 랠리
                _Segment(35, -0.05, 1.1, 0.8),   # 역배열 재매집
                _Segment(15, 0.5, 1.4, 1.5),     # 재랠리 초입
            ],
            peers=["샘플엔진", "샘플기자재"],
            fundamentals=FundamentalsSnapshot(
                revenue_yoy=[5, 7, 9, 11, 13, 14],
                op_profit_yoy=[2, 8, 13, 19, 22, 26],
                op_margin=[4, 5, 6, 7, 8, 9],
                net_margin=[3, 4, 5, 6, 6, 7],
                debt_to_equity=55.0,
                current_ratio=1.4,
                estimate_revision_pct=2.0,
                note="수주잔고 꾸준히 증가, 영업이익 레버리지 양호",
            ),
            news=[
                NewsHeadline("LNG운반선 대규모 수주", source="매일경제", sentiment="positive"),
            ],
            seed=44,
        ),
        # 5) 초기 펌핑
        _MockDef(
            ticker="900005",
            name="샘플AI",
            market="KOSDAQ",
            sector="IT서비스",
            theme="온디바이스 AI",
            aliases=["샘AI"],
            start_price=12000,
            segments=[
                _HIST(drift=-0.05),
                _Segment(80, -0.1, 1.4, 0.8),
                _Segment(40, 0.03, 1.0, 0.8),    # 바닥 다지기
                _Segment(12, 0.6, 1.5, 1.7),     # 포킹 돌파
                _Segment(8, 0.35, 1.3, 1.4),     # 초기 펌핑
            ],
            peers=["샘플소프트", "샘플플랫폼"],
            fundamentals=FundamentalsSnapshot(
                revenue_yoy=[-2, 1, 5, 10, 18, 27],
                op_profit_yoy=[-30, -12, 5, 25, 45, 72],
                op_margin=[2, 4, 6, 9, 12, 15],
                net_margin=[1, 3, 5, 7, 9, 12],
                debt_to_equity=30.0,
                current_ratio=2.1,
                estimate_revision_pct=7.0,
                note="영업이익 증가율이 매출 증가율을 크게 상회",
            ),
            news=[
                NewsHeadline("대형 빅테크와 온디바이스 AI 파트너십", source="ZDNET", sentiment="positive"),
            ],
            seed=55,
        ),
    ]


class MockProvider(BaseProvider):
    mode = "mock"

    def __init__(self, as_of: Optional[datetime] = None):
        self._as_of = as_of or datetime(2026, 4, 22)
        self._defs: Dict[str, _MockDef] = {d.ticker: d for d in _defs()}
        self._by_name: Dict[str, _MockDef] = {d.name: d for d in _defs()}

    # ----- Catalogue -----

    def list_symbols(self) -> List[SymbolMeta]:
        return [
            SymbolMeta(
                ticker=d.ticker, name=d.name, market=d.market,
                sector=d.sector, theme=d.theme, aliases=d.aliases,
            )
            for d in self._defs.values()
        ]

    def resolve(self, query: str) -> Optional[SymbolMeta]:
        q = query.strip()
        # Exact ticker first, then exact name, then alias substring.
        if q in self._defs:
            d = self._defs[q]
        elif q in self._by_name:
            d = self._by_name[q]
        else:
            d = None
            for defn in self._defs.values():
                if q == defn.name or q in defn.aliases or q in defn.name:
                    d = defn
                    break
        if not d:
            return None
        return SymbolMeta(
            ticker=d.ticker, name=d.name, market=d.market,
            sector=d.sector, theme=d.theme, aliases=d.aliases,
        )

    # ----- OHLCV -----

    def get_ohlcv(self, ticker: str) -> Optional[OHLCVBundle]:
        d = self._defs.get(ticker)
        if not d:
            return None
        df = _gen_ohlcv(d, self._as_of)
        return OHLCVBundle(daily=df)

    # ----- Fundamentals -----

    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot:
        d = self._defs.get(ticker)
        if not d:
            return FundamentalsSnapshot(available=False, note="종목 없음")
        return d.fundamentals

    # ----- Theme / peers -----

    def get_theme(self, ticker: str) -> ThemeSnapshot:
        d = self._defs.get(ticker)
        if not d:
            return ThemeSnapshot(
                sector_name=None, theme_name=None,
                sector_perf_1m=None, theme_perf_1m=None,
                peers=[], available=False,
            )
        # Peer performance deterministically derived from seed so tests are stable.
        rng = np.random.default_rng(d.seed + 7)
        peers = [
            PeerSnapshot(
                name=p, ticker=f"{d.ticker[:3]}{i:03d}",
                perf_1m=float(rng.uniform(-3, 12)),
                perf_3m=float(rng.uniform(-5, 35)),
            )
            for i, p in enumerate(d.peers, start=1)
        ]
        # Sector / theme performance correlated with the stock's own stage.
        own_1m = self._own_perf(d, 20)
        return ThemeSnapshot(
            sector_name=d.sector,
            theme_name=d.theme,
            sector_perf_1m=float(own_1m * 0.6 + rng.uniform(-2, 2)),
            theme_perf_1m=float(own_1m * 0.8 + rng.uniform(-1, 2)),
            peers=peers,
            available=True,
        )

    def _own_perf(self, d: _MockDef, days: int) -> float:
        df = _gen_ohlcv(d, self._as_of)
        if len(df) <= days:
            return 0.0
        return float((df["close"].iloc[-1] / df["close"].iloc[-days - 1] - 1) * 100.0)

    # ----- News / macro -----

    def get_news(self, ticker: str) -> List[NewsHeadline]:
        d = self._defs.get(ticker)
        if not d:
            return []
        today = self._as_of.date()
        return [
            NewsHeadline(
                title=n.title,
                source=n.source,
                sentiment=n.sentiment,
                published_at=(today - timedelta(days=i)).isoformat(),
            )
            for i, n in enumerate(d.news)
        ]

    def get_macro(self) -> MacroSnapshot:
        return MacroSnapshot(
            base_rate=3.25,
            base_rate_direction="holding",
            usdkrw=1380.0,
            usdkrw_direction="holding",
            note="Mock 모드 매크로 상수값",
        )
