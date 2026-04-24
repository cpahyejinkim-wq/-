"""Data-transfer models used between providers and engines. Keeping these
separate from the API response models means provider changes don't leak into
the public contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


@dataclass
class SymbolMeta:
    ticker: str
    name: str
    market: str               # e.g. "KOSPI", "KOSDAQ"
    sector: Optional[str] = None
    theme: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


@dataclass
class OHLCVBundle:
    """Daily OHLCV is the source of truth. Weekly / monthly are resampled from
    daily inside the timeframe engine, so providers only need to deliver daily.
    Index is DatetimeIndex; columns are open, high, low, close, volume.
    """
    daily: pd.DataFrame


@dataclass
class FundamentalsSnapshot:
    """Flexible container — real provider (OpenDartReader) fills what it can,
    mock provider fills all fields. Fields are `None` when unavailable.
    """
    revenue_yoy: Optional[List[float]] = None          # last 4-8 quarters, %YoY
    op_profit_yoy: Optional[List[float]] = None
    op_margin: Optional[List[float]] = None            # %
    net_margin: Optional[List[float]] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    estimate_revision_pct: Optional[float] = None      # e.g. +3.2 = +3.2% FY estimate up
    available: bool = True
    note: str = ""


@dataclass
class PeerSnapshot:
    name: str
    ticker: str
    perf_1m: float   # % over last ~20 trading days
    perf_3m: float


@dataclass
class ThemeSnapshot:
    sector_name: Optional[str]
    theme_name: Optional[str]
    sector_perf_1m: Optional[float]
    theme_perf_1m: Optional[float]
    peers: List[PeerSnapshot] = field(default_factory=list)
    available: bool = True


@dataclass
class MacroSnapshot:
    base_rate: Optional[float] = None       # 기준금리 %
    base_rate_direction: Optional[str] = None  # "hiking" / "holding" / "cutting"
    usdkrw: Optional[float] = None
    usdkrw_direction: Optional[str] = None
    note: str = ""


@dataclass
class NewsHeadline:
    title: str
    url: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[str] = None
    sentiment: Optional[str] = None
