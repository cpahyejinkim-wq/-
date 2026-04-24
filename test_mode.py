"""빠른 진단: 현재 어떤 프로바이더가 로드되는지 확인"""
import sys, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

print("=" * 40)
print("APP_MODE:", os.environ.get("APP_MODE", "NOT SET"))
print("OPENDART_API_KEY:", "SET" if os.environ.get("OPENDART_API_KEY") else "NOT SET")
print("ECOS_API_KEY:", "SET" if os.environ.get("ECOS_API_KEY") else "NOT SET")
print("=" * 40)

from backend.app_context import _build_provider
try:
    provider = _build_provider()
    print("Provider mode:", provider.mode)
    print("Provider class:", type(provider).__name__)
except Exception as e:
    print("Provider 초기화 오류:", e)

print("=" * 40)

if provider.mode == "live":
    print("LiveProvider 로드 성공! 종목 마스터 로딩 중...")
    try:
        symbols = provider.list_symbols()
        print(f"종목 수: {len(symbols)}")
        if symbols:
            print("첫 5개:", [(s.ticker, s.name) for s in symbols[:5]])
        else:
            print("종목 마스터가 비어있음 (네트워크 문제 가능)")
    except Exception as e:
        print("list_symbols 오류:", e)
else:
    print("Mock 모드로 실행 중 → .env의 APP_MODE=live가 적용 안됨")
