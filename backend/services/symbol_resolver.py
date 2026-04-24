"""Ticker resolution with fuzzy matching over the provider's catalogue."""
from __future__ import annotations

from typing import List

from rapidfuzz import fuzz, process

from backend.models.analysis_models import LookupCandidate
from backend.models.provider_models import SymbolMeta
from backend.providers.base_provider import BaseProvider


class SymbolResolver:
    def __init__(self, provider: BaseProvider):
        self.provider = provider
        self._cache: List[SymbolMeta] = provider.list_symbols()
        self._search_space: List[tuple[str, SymbolMeta]] = []
        for s in self._cache:
            self._search_space.append((s.name, s))
            self._search_space.append((s.ticker, s))
            for alias in s.aliases:
                self._search_space.append((alias, s))

    def exact(self, query: str) -> SymbolMeta | None:
        return self.provider.resolve(query)

    def search(self, query: str, limit: int = 8) -> List[LookupCandidate]:
        q = query.strip()
        if not q:
            return []
        keys = [k for k, _ in self._search_space]
        matches = process.extract(q, keys, scorer=fuzz.WRatio, limit=limit)
        out: List[LookupCandidate] = []
        seen: set[str] = set()
        for key, score, idx in matches:
            meta = self._search_space[idx][1]
            if meta.ticker in seen:
                continue
            seen.add(meta.ticker)
            out.append(
                LookupCandidate(
                    name=meta.name, ticker=meta.ticker, market=meta.market,
                    score=round(score / 100.0, 3),
                )
            )
        return out
