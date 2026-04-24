"""Orchestrates the full analysis pipeline.

Flow (matches docs/architecture.md):

    1. Resolve symbol
    2. Pull OHLCV / fundamentals / theme / news / macro
    3. Run engines (technical → flow → timeframe → fundamentals → theme → risk)
    4. Build trade plan from structure + stage
    5. Aggregate scoring, apply PDF-aligned overrides
    6. Return `AnalysisResponse`
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.engines import (
    flow_engine,
    fundamentals_engine,
    risk_engine,
    scoring_engine,
    technical_engine,
    theme_engine,
    timeframe_engine,
    trade_plan_engine,
)
from backend.models.analysis_models import (
    AnalysisResponse,
    AnalyzeRequest,
    MarketData,
    NewsItem,
    StockInfo,
    TechnicalAnalysis,
)
from backend.models.score_models import AggregatedScore
from backend.providers.base_provider import BaseProvider
from backend.services.symbol_resolver import SymbolResolver
from backend.utils import ta_utils as ta
from backend.utils.date_utils import now_iso
from backend.utils.logger import get_logger


logger = get_logger(__name__)


ENGINE_VERSION = "0.1.0"


class AnalysisService:
    def __init__(self, provider: BaseProvider):
        self.provider = provider
        self.resolver = SymbolResolver(provider)

    def analyze(self, req: AnalyzeRequest) -> Optional[AnalysisResponse]:
        meta = self.resolver.exact(req.query)
        if not meta:
            hits = self.resolver.search(req.query, limit=1)
            if not hits:
                logger.warning("resolve failed for query=%r", req.query)
                return None
            meta = self.resolver.exact(hits[0].ticker) or self.resolver.exact(hits[0].name)
            if not meta:
                return None

        bundle = self.provider.get_ohlcv(meta.ticker)
        if bundle is None or bundle.daily is None or bundle.daily.empty:
            logger.warning("no OHLCV for ticker=%s", meta.ticker)
            return None
        daily = bundle.daily

        fundamentals = self.provider.get_fundamentals(meta.ticker)
        theme_snap = self.provider.get_theme(meta.ticker)
        news = self.provider.get_news(meta.ticker)
        macro = self.provider.get_macro()

        # --- Engines ---
        tech = technical_engine.analyze(daily)
        flow = flow_engine.analyze(daily)
        tf = timeframe_engine.analyze(daily)
        fund = fundamentals_engine.analyze(fundamentals)
        own_perf_1m = ta.pct_return(daily["close"], 20)
        theme_res = theme_engine.analyze(theme_snap, own_perf_1m=own_perf_1m)
        news_negative = sum(1 for n in news if n.sentiment == "negative")
        risk = risk_engine.analyze(daily, macro, news_count=len(news), news_negative=news_negative)

        # --- Trade plan ---
        plan = trade_plan_engine.generate(
            daily, stage=flow.stage, risk_score=risk.buckets.total()
        )

        # --- Aggregate scoring ---
        agg = AggregatedScore(
            technical=tech.buckets,
            flow=flow.buckets,
            timeframe=tf.buckets,
            fundamental=fund.buckets,
            theme=theme_res.buckets,
            risk=risk.buckets,
        )
        final = scoring_engine.finalize(agg, stage=flow.stage, plan=plan)

        # --- Build response ---
        last_bar = daily.iloc[-1]
        prev_close = daily["close"].iloc[-2] if len(daily) >= 2 else last_bar["close"]
        change_pct = (last_bar["close"] - prev_close) / prev_close * 100.0 if prev_close else 0.0

        return AnalysisResponse(
            stock=StockInfo(
                name=meta.name, ticker=meta.ticker, market=meta.market,
                sector=meta.sector, theme=meta.theme,
            ),
            market_data=MarketData(
                current_price=round(float(last_bar["close"]), 2),
                change_pct=round(float(change_pct), 2),
                volume=int(last_bar["volume"]),
                as_of=pd.Timestamp(daily.index[-1]).date().isoformat(),
            ),
            stage_analysis=flow_engine.to_stage_analysis(flow),
            technical_analysis=TechnicalAnalysis(
                score=round(tech.buckets.total(), 2),
                patterns=tech.patterns,
                comment=tech.comment,
                sub_scores={
                    "base_reversal": round(tech.buckets.base_reversal, 2),
                    "candle_quality": round(tech.buckets.candle_quality, 2),
                    "ma_structure": round(tech.buckets.ma_structure, 2),
                    "breakout_confirm": round(tech.buckets.breakout_confirm, 2),
                    "volume_quality": round(tech.buckets.volume_quality, 2),
                    "overheat_penalty": round(tech.buckets.overheat_penalty, 2),
                },
            ),
            timeframe_analysis=timeframe_engine.to_timeframe_analysis(tf),
            fundamental_analysis=fundamentals_engine.to_fundamental_analysis(fund),
            theme_analysis=theme_engine.to_theme_analysis(theme_res),
            risk_analysis=risk_engine.to_risk_analysis(risk),
            trade_plan=plan,
            final_decision=scoring_engine.to_final_decision(final),
            news=[
                NewsItem(
                    title=n.title, url=n.url, source=n.source,
                    published_at=n.published_at, sentiment=n.sentiment,  # type: ignore[arg-type]
                )
                for n in news
            ],
            meta={
                "mode": self.provider.mode,
                "engine_version": ENGINE_VERSION,
                "generated_at": now_iso(),
            },
        )
