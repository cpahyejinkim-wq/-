"""Dependency wiring. Swapping provider = change this one file."""
from __future__ import annotations

import os
from functools import lru_cache

from backend.providers.base_provider import BaseProvider
from backend.providers.mock_provider import MockProvider
from backend.services.analysis_service import AnalysisService


@lru_cache(maxsize=1)
def _build_provider() -> BaseProvider:
    mode = os.environ.get("APP_MODE", "mock").lower()
    if mode == "mock":
        return MockProvider()
    if mode == "live":
        # Phase 2 — real provider. Falls back to mock until implemented.
        try:
            from backend.providers.market_provider_adapter import MarketProviderAdapter
            return MarketProviderAdapter()
        except NotImplementedError:
            return MockProvider()
    return MockProvider()


@lru_cache(maxsize=1)
def _build_service() -> AnalysisService:
    return AnalysisService(_build_provider())


def get_service() -> AnalysisService:
    return _build_service()
