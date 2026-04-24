"""Phase 2 — real market-data adapter.

Planned stack:
    pykrx: 일봉 OHLCV / 시가총액 / 업종 코드
    FinanceDataReader: 상장종목 마스터 (KRX, KOSPI, KOSDAQ, KONEX)

Wiring notes for when this is implemented:
    - `list_symbols` should cache the KRX listing on disk for the session.
    - `get_ohlcv` should write a per-ticker parquet into $CACHE_DIR and reuse
      intraday cache keyed on (ticker, trading_date).
    - pykrx is rate-sensitive; add a small polite delay between calls.
    - Business-day alignment must match MockProvider so engines don't branch.

See `docs/data-providers.md`.
"""
from __future__ import annotations

from typing import List, Optional

from backend.models.provider_models import OHLCVBundle, SymbolMeta
from backend.providers.base_provider import BaseProvider


class MarketProviderAdapter(BaseProvider):
    mode = "live-market"

    def __init__(self) -> None:
        raise NotImplementedError(
            "MarketProviderAdapter is a Phase 2 placeholder. "
            "See docs/data-providers.md for the planned implementation."
        )

    # Intentional stubs — all raise via __init__.
    def list_symbols(self) -> List[SymbolMeta]: ...  # pragma: no cover
    def resolve(self, query: str) -> Optional[SymbolMeta]: ...  # pragma: no cover
    def get_ohlcv(self, ticker: str) -> Optional[OHLCVBundle]: ...  # pragma: no cover
    def get_fundamentals(self, ticker): ...  # pragma: no cover
    def get_theme(self, ticker): ...  # pragma: no cover
    def get_news(self, ticker): ...  # pragma: no cover
    def get_macro(self): ...  # pragma: no cover
