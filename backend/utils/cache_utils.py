"""Parquet 기반 OHLCV 디스크 캐시.

당일 캐시가 있으면 pykrx를 다시 호출하지 않는다.
장 마감(15:30 KST) 이후 요청은 당일 데이터를 신뢰하고,
장 중 요청은 4시간 이내 캐시를 신뢰한다.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from backend.utils.logger import get_logger

logger = get_logger(__name__)

KST = timezone(timedelta(hours=9))
CACHE_DIR = Path(os.environ.get("CACHE_DIR", ".cache/ohlcv"))


def _cache_path(ticker: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{ticker}.parquet"


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=KST)
    now = datetime.now(tz=KST)
    # 장 마감 후(15:30)면 오늘 갱신된 캐시를 무조건 신뢰
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now >= market_close and mtime.date() == now.date():
        return True
    # 장 중이면 4시간 이내 캐시만 신뢰
    return (now - mtime) < timedelta(hours=4)


def load(ticker: str) -> pd.DataFrame | None:
    path = _cache_path(ticker)
    if _is_fresh(path):
        try:
            df = pd.read_parquet(path)
            logger.debug("cache hit: %s (%d rows)", ticker, len(df))
            return df
        except Exception as e:
            logger.warning("cache read failed for %s: %s", ticker, e)
    return None


def save(ticker: str, df: pd.DataFrame) -> None:
    try:
        _cache_path(ticker).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(_cache_path(ticker))
        logger.debug("cache saved: %s (%d rows)", ticker, len(df))
    except Exception as e:
        logger.warning("cache write failed for %s: %s", ticker, e)
