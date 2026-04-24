"""Provider interface. Every data source must conform to this.

Phase 1 ships only the mock provider. Phase 2 will add pykrx /
FinanceDataReader / OpenDartReader / Naver news / BOK ECOS adapters behind
the same interface so the analysis pipeline never branches on provider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from backend.models.provider_models import (
    FundamentalsSnapshot,
    MacroSnapshot,
    NewsHeadline,
    OHLCVBundle,
    SymbolMeta,
    ThemeSnapshot,
)


class BaseProvider(ABC):
    """All methods may return `None` / empty payload when upstream is missing;
    engines must tolerate that and degrade gracefully."""

    mode: str = "base"

    @abstractmethod
    def list_symbols(self) -> List[SymbolMeta]: ...

    @abstractmethod
    def resolve(self, query: str) -> Optional[SymbolMeta]: ...

    @abstractmethod
    def get_ohlcv(self, ticker: str) -> Optional[OHLCVBundle]: ...

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot: ...

    @abstractmethod
    def get_theme(self, ticker: str) -> ThemeSnapshot: ...

    @abstractmethod
    def get_news(self, ticker: str) -> List[NewsHeadline]: ...

    @abstractmethod
    def get_macro(self) -> MacroSnapshot: ...
