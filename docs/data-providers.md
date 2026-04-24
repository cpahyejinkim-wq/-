# Data Providers

## Mode 선택

`APP_MODE` 환경변수로 제어한다:

| `APP_MODE` | 동작                                                   |
|------------|--------------------------------------------------------|
| `mock`     | `MockProvider` — 결정론적 합성 OHLCV, API 키 불필요   |
| `live`     | `MarketProviderAdapter` (Phase 2 구현 필요)            |
| `auto`     | live 시도 후 실패하면 mock 폴백                        |

## Phase 1 — MockProvider

`backend/providers/mock_provider.py`

- 5개 종목: 샘플반도체(포킹), 샘플바이오(T바닥), 샘플2차전지(과열), 샘플조선(재랠리), 샘플AI(펌핑)
- NumPy seeded 난수 → 결정론적, 테스트에서도 동일 결과
- 추가 종목: `_defs()` 리스트에 `_MockDef` 항목 추가

## Phase 2 — 실제 데이터 소스

### pykrx (OHLCV)
```python
pip install pykrx
from pykrx import stock
df = stock.get_market_ohlcv("20230101", "20260422", "005930")
```
- 한국거래소 스크래핑 기반
- Rate-sensitive: 종목 간 `time.sleep(0.2)` 권장
- 일봉 캐시: `$CACHE_DIR/<ticker>/<YYYY-MM-DD>.parquet`

### FinanceDataReader (종목 마스터)
```python
pip install finance-datareader
import FinanceDataReader as fdr
stocks = fdr.StockListing('KRX')   # 전 상장 종목 DataFrame
```
- `symbol_resolver.py`의 fuzzy 검색 기반 원천 데이터
- 일 1회 갱신으로 충분

### OpenDartReader (재무제표)
```python
pip install opendartreader
import OpenDartReader
dart = OpenDartReader.OpenDartReader(api_key)
df = dart.finstate('005930', 2025)  # 삼성전자 FY2025
```
- DART API 키 필요: `OPENDART_API_KEY` (.env)
- 연간/분기 재무 데이터 → `FundamentalsSnapshot`

### 한국은행 ECOS (매크로)
```python
# requests 사용, API 키 필요
GET https://ecos.bok.or.kr/api/StatisticSearch/{ECOS_API_KEY}/json/kr/1/1/722Y001/A/2024/2025
```
- 기준금리(`722Y001`) 및 환율(`731Y001`) 데이터
- `risk_engine`의 매크로 컨텍스트 입력

### 네이버 금융 뉴스 (HTML 파싱)
```python
# BeautifulSoup로 파싱
url = f"https://finance.naver.com/item/news_news.naver?code={ticker}"
```
- 법적 확인 필요, robots.txt 준수
- 뉴스 감성 분석은 Phase 2.5 이후

## Provider 인터페이스

새 프로바이더는 `BaseProvider`를 상속해야 한다:

```python
class MyProvider(BaseProvider):
    def list_symbols(self) -> List[SymbolMeta]: ...
    def resolve(self, query: str) -> Optional[SymbolMeta]: ...
    def get_ohlcv(self, ticker: str) -> Optional[OHLCVBundle]: ...
    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot: ...
    def get_theme(self, ticker: str) -> ThemeSnapshot: ...
    def get_news(self, ticker: str) -> List[NewsHeadline]: ...
    def get_macro(self) -> MacroSnapshot: ...
```

연결: `backend/app_context.py`의 `_build_provider()` 수정.
