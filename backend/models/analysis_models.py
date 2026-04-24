"""Pydantic models that define the analysis API contract.

These mirror `shared/schemas/analysis_response.schema.json` and are the single
source of truth for the response shape the frontend consumes.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


Stage = Literal[
    "관찰",
    "T바닥",
    "포킹",
    "펌핑",
    "랠리",
    "역배열재매집",
    "재랠리",
    "과열",
]

Action = Literal[
    "Strong Buy Setup",
    "Buy on Pullback",
    "Watch for Confirmation",
    "Hold / No Immediate Entry",
    "Avoid / Overheated / Weak Setup",
]


class StockInfo(BaseModel):
    name: str
    ticker: str
    market: str
    sector: Optional[str] = None
    theme: Optional[str] = None


class MarketData(BaseModel):
    current_price: float
    change_pct: float
    volume: int
    as_of: str  # ISO date string the OHLCV bar ended on


class DetectedPattern(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)


class StageAnalysis(BaseModel):
    stage: Stage
    stage_score: float
    continuity_score: float
    comment: str


class TechnicalAnalysis(BaseModel):
    score: float
    patterns: List[DetectedPattern]
    comment: str
    sub_scores: dict  # {base_reversal, candle, ma, breakout, volume, overheat_penalty}


class TimeframeAnalysis(BaseModel):
    monthly_state: str
    weekly_state: str
    daily_state: str
    alignment_score: float
    comment: str


class FundamentalAnalysis(BaseModel):
    score: float
    revenue_trend: str
    op_profit_trend: str
    earnings_leverage: str  # whether op growth > revenue growth
    margin_trend: str
    debt_health: str
    estimate_revision: Optional[str] = None
    comment: str
    data_available: bool


class ThemeAnalysis(BaseModel):
    score: float
    sector_name: Optional[str] = None
    theme_name: Optional[str] = None
    sector_strength: str
    theme_strength: str
    peer_confirmation: str
    peer_names: List[str] = Field(default_factory=list)
    role_in_theme: Literal["leader", "follower", "isolated", "unknown"]
    comment: str


class RiskAnalysis(BaseModel):
    score: float
    overextension_risk: str
    volatility_risk: str
    event_risk: str
    liquidity_risk: str
    breakout_failure_risk: str
    warning_flags: List[str] = Field(default_factory=list)
    comment: str


class TradeLevel(BaseModel):
    price: Optional[float] = None  # None if no clean level derivable
    rationale: str


class TradePlan(BaseModel):
    current_price: float
    detected_stage: Stage
    support_levels: List[float]
    resistance_levels: List[float]
    buy_zone_1: TradeLevel
    buy_zone_2: TradeLevel
    stop_loss: TradeLevel
    take_profit_1: TradeLevel
    take_profit_2: TradeLevel
    invalidation_condition: str
    position_sizing_note: str
    one_line_strategy: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class FinalDecision(BaseModel):
    total_score: float
    raw_score: float
    risk_multiplier: float
    overheat_penalty: float
    action: Action
    summary: str


class NewsItem(BaseModel):
    title: str
    url: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[str] = None
    sentiment: Optional[Literal["positive", "neutral", "negative"]] = None


class AnalysisResponse(BaseModel):
    stock: StockInfo
    market_data: MarketData
    stage_analysis: StageAnalysis
    technical_analysis: TechnicalAnalysis
    timeframe_analysis: TimeframeAnalysis
    fundamental_analysis: FundamentalAnalysis
    theme_analysis: ThemeAnalysis
    risk_analysis: RiskAnalysis
    trade_plan: TradePlan
    final_decision: FinalDecision
    news: List[NewsItem] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)  # mode, generated_at, engine_version


class AnalyzeRequest(BaseModel):
    query: str
    market: Literal["KR"] = "KR"
    mode: Literal["mock", "live", "auto"] = "auto"


class LookupCandidate(BaseModel):
    name: str
    ticker: str
    market: str
    score: float = Field(ge=0.0, le=1.0)


class LookupResponse(BaseModel):
    query: str
    candidates: List[LookupCandidate]
