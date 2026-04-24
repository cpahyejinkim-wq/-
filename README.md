# Chart Master Terminal

차트마스터반 교재 철학(흐름·탑다운·멀티타임프레임·이익레버리지)을 코드로 구현한 한국 주식 투자 분석 대시보드.

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r backend/requirements.txt

# 2. 환경 변수 (필요 시 .env.example 복사)
cp .env.example .env          # 기본값 APP_MODE=mock으로 동작

# 3. 서버 실행
uvicorn backend.app:app --reload --port 8000

# 4. 브라우저로 접속
open http://localhost:8000
```

**별도 빌드 불필요** — 프론트엔드는 FastAPI StaticFiles가 직접 서빙합니다.

## 샘플 종목 (Phase 1 Mock 모드)

| 종목 | 단계 | 설명 |
|------|------|------|
| 샘플반도체 | 포킹 | AI 반도체 테마, 이익 레버리지 양호 |
| 샘플바이오 | T바닥 | 비만치료제 테마, 흑자 전환 구간 |
| 샘플2차전지 | 과열 | LFP 배터리, 수급 주도 급등 — 진입 금지 |
| 샘플조선 | 재랠리 | 친환경선박 테마, 수주잔고 증가 |
| 샘플AI | 포킹 | 온디바이스 AI, 영업이익 급증 구간 |

## 테스트

```bash
python -m pytest backend/tests -v
```

## 구조

```
backend/   ← FastAPI + 분석 엔진 (Python)
frontend/  ← 바닐라 JS ES 모듈 (빌드 없음)
docs/      ← 아키텍처·스코어링·PDF 매핑·프로바이더·제한사항
```

→ 상세 내용은 `docs/` 참조.

## Phase 2 (실 데이터 연동)

`backend/requirements.txt`의 주석 해제 후:
- pykrx: 실시간 OHLCV
- FinanceDataReader: 전종목 마스터
- OpenDartReader: DART 재무제표
- `.env`에 `OPENDART_API_KEY`, `ECOS_API_KEY` 입력

자세한 내용: `docs/data-providers.md`

---

> **투자 유의**: 본 도구는 교육·참고 목적이며 투자 권유가 아닙니다.
