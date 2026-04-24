"""Phase 2 실 데이터 프로바이더.

데이터 소스:
  - pykrx              : 일봉 OHLCV (KRX 스크래핑)
  - FinanceDataReader  : 전종목 마스터 (종목명→코드 변환)
  - OpenDartReader     : DART 재무제표 (매출·영업이익)
  - 한국은행 ECOS API  : 기준금리·환율 (매크로)
  - 네이버 금융        : 뉴스 헤드라인 (HTML 파싱)

각 소스가 실패하면 경고 로그 후 빈 값/Mock 폴백 처리.
엔진은 None/빈 값을 graceful 처리한다.
"""
from __future__ import annotations

import os
import ssl
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional

import pandas as pd
import urllib3

# 기업 네트워크 SSL 인스펙션 우회
# 회사 방화벽이 HTTPS에 자체 인증서를 삽입하므로 금융 데이터 수집에 한해 비활성화
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    import requests as _requests
    _orig_req = _requests.Session.request
    def _no_verify(self, method, url, **kwargs):
        kwargs.setdefault("verify", False)
        return _orig_req(self, method, url, **kwargs)
    _requests.Session.request = _no_verify
except Exception:
    pass

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
from backend.utils import cache_utils
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# pykrx column mapping (한국어 → 영어)
_OHLCV_COLS = {"시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume"}


# ────────────────────────────────────────────
# 종목 마스터 (FinanceDataReader, 세션 캐시)
# ────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_krx_listing() -> pd.DataFrame:
    """전 상장 종목 마스터. KOSPI + KOSDAQ 합산, 세션 당 1회만 로드."""
    import FinanceDataReader as fdr
    logger.info("KRX 종목 마스터 로딩 중…")
    frames = []
    for market in ("KOSPI", "KOSDAQ"):
        try:
            df = fdr.StockListing(market)
            df.columns = [c.strip() for c in df.columns]
            df["Market"] = market
            frames.append(df)
        except Exception as e:
            logger.warning("%s 마스터 로드 실패: %s", market, e)
    if not frames:
        # pykrx fallback
        try:
            from pykrx import stock as krx
            today = datetime.now().strftime("%Y%m%d")
            rows = []
            for market in ("KOSPI", "KOSDAQ"):
                tickers = krx.get_market_ticker_list(today, market=market)
                for t in tickers:
                    name = krx.get_market_ticker_name(t)
                    rows.append({"Code": t, "Name": name, "Market": market})
            df = pd.DataFrame(rows)
            logger.info("pykrx fallback 마스터: %d 종목", len(df))
            return df
        except Exception as e2:
            logger.error("마스터 로드 전체 실패: %s", e2)
            return pd.DataFrame(columns=["Code", "Name", "Market"])

    result = pd.concat(frames, ignore_index=True)
    logger.info("KRX 마스터 로드 완료: %d 종목", len(result))
    return result


def _listing_to_meta(row) -> SymbolMeta:
    market = str(row.get("Market", row.get("market", "KRX"))).upper()
    market_clean = "KOSPI" if "KOSPI" in market else "KOSDAQ" if "KOSDAQ" in market else market
    name = str(row.get("Name", row.get("name", "")))
    ticker = str(row.get("Code", row.get("code", ""))).zfill(6)
    sector = str(row.get("Sector", row.get("sector", ""))) or None
    # 약어 alias 자동 생성 (예: "삼성전자" → "삼성" 같은 단순 단축은 하지 않음;
    # fuzzy 검색이 처리하므로 빈 리스트도 무방)
    return SymbolMeta(
        ticker=ticker,
        name=name,
        market=market_clean,
        sector=sector,
        theme=None,
        aliases=[ticker],   # 코드를 alias로 등록 → 숫자 코드 직접 입력도 동작
    )


# ────────────────────────────────────────────
# OHLCV (pykrx)
# ────────────────────────────────────────────

def _fetch_ohlcv(ticker: str, days: int = 500) -> Optional[pd.DataFrame]:
    """pykrx로 일봉 OHLCV를 받아 표준 컬럼으로 반환."""
    cached = cache_utils.load(ticker)
    if cached is not None:
        return cached

    from pykrx import stock as krx
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    try:
        df = krx.get_market_ohlcv(start, end, ticker)
        if df is None or df.empty:
            logger.warning("pykrx: %s 데이터 없음", ticker)
            return None
        df = df.rename(columns=_OHLCV_COLS)
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        df.index = pd.to_datetime(df.index)
        df.index.name = "date"
        cache_utils.save(ticker, df)
        logger.info("pykrx: %s %d봉 로드", ticker, len(df))
        return df
    except Exception as e:
        logger.error("pykrx 오류 (%s): %s", ticker, e)
        return None


# ────────────────────────────────────────────
# 재무제표 (OpenDartReader)
# ────────────────────────────────────────────

def _yoy_list(series: pd.Series, col: str, n: int = 6) -> List[float]:
    """최근 n분기 YoY 성장률 리스트."""
    vals = series[col].dropna().astype(float)
    if len(vals) < 5:
        return []
    out = []
    for i in range(4, min(len(vals), n + 4)):
        prev = vals.iloc[i - 4]
        curr = vals.iloc[i]
        if prev and prev != 0:
            out.append(round((curr - prev) / abs(prev) * 100, 1))
    return out[-n:]


def _fetch_fundamentals(ticker: str) -> FundamentalsSnapshot:
    api_key = os.environ.get("OPENDART_API_KEY", "").strip()
    if not api_key:
        return FundamentalsSnapshot(available=False, note="OPENDART_API_KEY 미설정")
    try:
        import OpenDartReader
        dart = OpenDartReader.OpenDartReader(api_key)

        # 종목코드 → corp_code
        corp = dart.find_corp_code(ticker)
        if not corp:
            return FundamentalsSnapshot(available=False, note=f"DART corp_code 없음: {ticker}")

        # 최근 8분기 손익계산서
        current_year = datetime.now().year
        frames = []
        for year in range(current_year - 2, current_year + 1):
            for rept in ["11013", "11012", "11014", "11011"]:  # 1Q, 2Q, 3Q, Annual
                try:
                    fs = dart.finstate(corp, year, reprt_code=rept)
                    if fs is not None and not fs.empty:
                        fs["year"] = year
                        fs["rept"] = rept
                        frames.append(fs)
                    time.sleep(0.15)
                except Exception:
                    pass

        if not frames:
            return FundamentalsSnapshot(available=False, note="DART 재무 데이터 없음")

        all_fs = pd.concat(frames, ignore_index=True)

        # 매출액·영업이익 추출
        rev_key = all_fs[all_fs["account_nm"].str.contains("매출액|수익", na=False)]
        op_key  = all_fs[all_fs["account_nm"].str.contains("영업이익|영업손익", na=False)]

        def to_float_series(df_sub):
            s = df_sub[["thstrm_amount"]].copy()
            s["thstrm_amount"] = pd.to_numeric(
                s["thstrm_amount"].astype(str).str.replace(",", ""), errors="coerce"
            )
            return s.reset_index(drop=True)

        rev_s = to_float_series(rev_key)
        op_s  = to_float_series(op_key)

        rev_yoy = _yoy_list(rev_s, "thstrm_amount") if len(rev_s) >= 5 else []
        op_yoy  = _yoy_list(op_s,  "thstrm_amount") if len(op_s)  >= 5 else []

        # 최근 영업이익률
        op_vals  = pd.to_numeric(op_s["thstrm_amount"],  errors="coerce").dropna().tolist()
        rev_vals = pd.to_numeric(rev_s["thstrm_amount"], errors="coerce").dropna().tolist()
        margins = []
        for o, r in zip(op_vals[-6:], rev_vals[-6:]):
            if r and r != 0:
                margins.append(round(o / r * 100, 1))

        return FundamentalsSnapshot(
            revenue_yoy=rev_yoy or None,
            op_profit_yoy=op_yoy or None,
            op_margin=margins or None,
            available=True,
            note="OpenDartReader (DART 공시)",
        )
    except Exception as e:
        logger.error("OpenDartReader 오류 (%s): %s", ticker, e)
        return FundamentalsSnapshot(available=False, note=f"DART 오류: {e}")


# ────────────────────────────────────────────
# 섹터/피어 (pykrx)
# ────────────────────────────────────────────

def _fetch_theme(ticker: str, meta: SymbolMeta) -> ThemeSnapshot:
    try:
        from pykrx import stock as krx
        today = datetime.now().strftime("%Y%m%d")
        # pykrx 업종 정보
        market = "KOSPI" if meta.market == "KOSPI" else "KOSDAQ"
        sector_df = krx.get_market_sector_classifications(today, market=market)
        if sector_df is None or sector_df.empty:
            raise ValueError("업종 데이터 없음")

        # 해당 종목 업종 찾기
        row = sector_df[sector_df.index == ticker]
        if row.empty:
            sector_name = meta.sector or "기타"
        else:
            sector_name = str(row["업종명"].iloc[0])

        # 같은 업종 종목 (피어)
        same_sector = sector_df[sector_df["업종명"] == sector_name]
        peer_tickers = [t for t in same_sector.index if t != ticker][:5]

        peers: List[PeerSnapshot] = []
        for pt in peer_tickers:
            try:
                p_name = str(same_sector.loc[pt, "종목명"]) if "종목명" in same_sector.columns else pt
                df_p = _fetch_ohlcv(pt, days=65)
                if df_p is not None and len(df_p) >= 21:
                    from backend.utils import ta_utils as ta
                    p1m = ta.pct_return(df_p["close"], 20)
                    p3m = ta.pct_return(df_p["close"], 60)
                    peers.append(PeerSnapshot(name=p_name, ticker=pt, perf_1m=round(p1m, 2), perf_3m=round(p3m, 2)))
                time.sleep(0.1)
            except Exception:
                pass

        # 섹터 지수 성과 (KRX 업종 인덱스 사용 불가시 피어 평균으로 대체)
        sector_perf = round(sum(p.perf_1m for p in peers) / len(peers), 2) if peers else None

        return ThemeSnapshot(
            sector_name=sector_name,
            theme_name=sector_name,
            sector_perf_1m=sector_perf,
            theme_perf_1m=sector_perf,
            peers=peers,
            available=True,
        )
    except Exception as e:
        logger.warning("섹터/피어 조회 실패 (%s): %s", ticker, e)
        return ThemeSnapshot(
            sector_name=meta.sector,
            theme_name=meta.sector,
            sector_perf_1m=None,
            theme_perf_1m=None,
            peers=[],
            available=bool(meta.sector),
        )


# ────────────────────────────────────────────
# 매크로 (ECOS)
# ────────────────────────────────────────────

def _fetch_macro() -> MacroSnapshot:
    api_key = os.environ.get("ECOS_API_KEY", "").strip()
    if not api_key:
        return MacroSnapshot(note="ECOS_API_KEY 미설정")
    try:
        import requests
        now = datetime.now()
        period = f"{now.year - 1}{now.month:02d}/{now.year}{now.month:02d}"

        def ecos_get(stat_code: str) -> List[dict]:
            url = (
                f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}"
                f"/json/kr/1/5/{stat_code}/M/{period}"
            )
            r = requests.get(url, timeout=8, verify=False)
            data = r.json()
            items = data.get("StatisticSearch", {}).get("row", [])
            return items

        # 기준금리 (722Y001)
        rate_rows = ecos_get("722Y001")
        base_rate = float(rate_rows[-1]["DATA_VALUE"]) if rate_rows else None
        rate_prev = float(rate_rows[-2]["DATA_VALUE"]) if len(rate_rows) >= 2 else base_rate
        if base_rate and rate_prev:
            if base_rate > rate_prev:
                rate_dir = "hiking"
            elif base_rate < rate_prev:
                rate_dir = "cutting"
            else:
                rate_dir = "holding"
        else:
            rate_dir = None

        # 원/달러 환율 (731Y001 → 매매기준율)
        fx_rows = ecos_get("731Y001")
        usdkrw = float(fx_rows[-1]["DATA_VALUE"]) if fx_rows else None
        fx_prev = float(fx_rows[-2]["DATA_VALUE"]) if len(fx_rows) >= 2 else usdkrw
        if usdkrw and fx_prev:
            fx_dir = "rising" if usdkrw > fx_prev else ("falling" if usdkrw < fx_prev else "holding")
        else:
            fx_dir = None

        return MacroSnapshot(
            base_rate=base_rate,
            base_rate_direction=rate_dir,
            usdkrw=usdkrw,
            usdkrw_direction=fx_dir,
            note="한국은행 ECOS",
        )
    except Exception as e:
        logger.warning("ECOS 오류: %s", e)
        return MacroSnapshot(note=f"ECOS 오류: {e}")


# ────────────────────────────────────────────
# 뉴스 (네이버 금융)
# ────────────────────────────────────────────

def _fetch_news(ticker: str) -> List[NewsHeadline]:
    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://finance.naver.com/item/news_news.naver?code={ticker}&page=1"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://finance.naver.com",
        }
        r = requests.get(url, headers=headers, timeout=8, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")

        headlines: List[NewsHeadline] = []
        for row in soup.select("table.type5 tr"):
            a_tag = row.select_one("td.title a")
            date_td = row.select_one("td.date")
            src_td = row.select_one("td.info")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            link = f"https://finance.naver.com{href}" if href.startswith("/") else href
            date_str = date_td.get_text(strip=True) if date_td else None
            source = src_td.get_text(strip=True) if src_td else None

            # 단순 키워드 감성
            neg_words = ["하락", "급락", "실적 부진", "리스크", "우려", "손실", "적자"]
            pos_words = ["상승", "급등", "실적 호조", "수주", "흑자", "성장", "수혜"]
            title_lower = title
            sentiment = "neutral"
            if any(w in title_lower for w in pos_words):
                sentiment = "positive"
            elif any(w in title_lower for w in neg_words):
                sentiment = "negative"

            headlines.append(NewsHeadline(
                title=title,
                url=link,
                source=source,
                published_at=date_str,
                sentiment=sentiment,
            ))
            if len(headlines) >= 5:
                break
        return headlines
    except Exception as e:
        logger.warning("네이버 뉴스 오류 (%s): %s", ticker, e)
        return []


# ────────────────────────────────────────────
# LiveProvider
# ────────────────────────────────────────────

class LiveProvider(BaseProvider):
    mode = "live"

    def __init__(self):
        self._listing: Optional[pd.DataFrame] = None
        self._meta_cache: Dict[str, SymbolMeta] = {}

    def _get_listing(self) -> pd.DataFrame:
        if self._listing is None:
            self._listing = _load_krx_listing()
        return self._listing

    def list_symbols(self) -> List[SymbolMeta]:
        df = self._get_listing()
        out = []
        for _, row in df.iterrows():
            try:
                out.append(_listing_to_meta(row))
            except Exception:
                pass
        return out

    def resolve(self, query: str) -> Optional[SymbolMeta]:
        if query in self._meta_cache:
            return self._meta_cache[query]

        df = self._get_listing()
        q = query.strip()

        # 코드 직접 매칭
        code_col = "Code" if "Code" in df.columns else "code"
        name_col = "Name" if "Name" in df.columns else "name"

        exact_code = df[df[code_col].astype(str).str.zfill(6) == q.zfill(6)]
        if not exact_code.empty:
            meta = _listing_to_meta(exact_code.iloc[0])
            self._meta_cache[query] = meta
            return meta

        exact_name = df[df[name_col] == q]
        if not exact_name.empty:
            meta = _listing_to_meta(exact_name.iloc[0])
            self._meta_cache[query] = meta
            return meta

        # 부분 매칭
        partial = df[df[name_col].str.contains(q, na=False)]
        if not partial.empty:
            meta = _listing_to_meta(partial.iloc[0])
            self._meta_cache[query] = meta
            return meta

        return None

    def get_ohlcv(self, ticker: str) -> Optional[OHLCVBundle]:
        df = _fetch_ohlcv(ticker)
        if df is None:
            return None
        return OHLCVBundle(daily=df)

    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot:
        return _fetch_fundamentals(ticker)

    def get_theme(self, ticker: str) -> ThemeSnapshot:
        meta = self._meta_cache.get(ticker) or SymbolMeta(
            ticker=ticker, name=ticker, market="KRX"
        )
        return _fetch_theme(ticker, meta)

    def get_news(self, ticker: str) -> List[NewsHeadline]:
        return _fetch_news(ticker)

    def get_macro(self) -> MacroSnapshot:
        return _fetch_macro()
