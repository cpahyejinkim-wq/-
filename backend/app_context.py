"""Dependency wiring. Swapping provider = change this one file."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# .env 로드 (app.py보다 먼저 import될 수 있으므로 여기서도 처리)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from backend.providers.base_provider import BaseProvider
from backend.providers.mock_provider import MockProvider
from backend.services.analysis_service import AnalysisService
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _build_provider() -> BaseProvider:
    mode = os.environ.get("APP_MODE", "mock").lower()
    logger.info("APP_MODE=%s → 프로바이더 초기화", mode)

    if mode == "live":
        try:
            from backend.providers.live_provider import LiveProvider
            provider = LiveProvider()
            logger.info("LiveProvider 초기화 완료")
            return provider
        except Exception as e:
            logger.error("LiveProvider 초기화 실패 (%s) → MockProvider 폴백", e)
            return MockProvider()

    if mode == "auto":
        # pykrx import 가능하면 live, 아니면 mock
        try:
            from pykrx import stock  # noqa: F401
            from backend.providers.live_provider import LiveProvider
            return LiveProvider()
        except ImportError:
            logger.warning("pykrx 없음 → MockProvider 폴백")
            return MockProvider()

    return MockProvider()


@lru_cache(maxsize=1)
def _build_service() -> AnalysisService:
    return AnalysisService(_build_provider())


def get_service() -> AnalysisService:
    return _build_service()
