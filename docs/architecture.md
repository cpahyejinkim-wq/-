# Architecture

## Overview

```
Browser (frontend/index.html + ES modules)
        │ fetch /api/analyze
        ▼
FastAPI (backend/app.py)
        │
  ┌─────┴─────────────────────────┐
  │      Analysis Pipeline        │
  │  SymbolResolver               │
  │  ↓ OHLCV / Fundamentals /     │
  │    Theme / News / Macro       │
  │  ↓ TechnicalEngine            │
  │  ↓ FlowEngine                 │
  │  ↓ TimeframeEngine            │
  │  ↓ FundamentalsEngine         │
  │  ↓ ThemeEngine                │
  │  ↓ RiskEngine                 │
  │  ↓ TradePlanEngine            │
  │  ↓ ScoringEngine              │
  │  → AnalysisResponse (JSON)    │
  └───────────────────────────────┘
        │
  Provider (MockProvider │ LiveProvider)
```

## Responsibilities

### Frontend (`frontend/`)
- Pure rendering: receives `AnalysisResponse` JSON, maps to HTML.
- No scoring logic. No business rules.
- ES modules, no build step — served by FastAPI StaticFiles.

### Backend (`backend/`)
- `app.py`: FastAPI app, CORS, mounts static frontend.
- `app_context.py`: single place to swap providers (`APP_MODE=mock|live`).
- `api/`: thin route handlers, no logic beyond HTTP → service → response.
- `services/`: orchestration. `AnalysisService` runs the pipeline.
- `engines/`: domain logic — each engine is independent, testable.
- `models/`: Pydantic API models + internal score bucket dataclasses.
- `providers/`: data-source abstraction (see `data-providers.md`).
- `utils/`: pure helpers (TA math, formatters, logger).

## Analysis Pipeline (14 steps)

1. Resolve ticker from name (fuzzy match over provider catalogue)
2. Fetch daily OHLCV bundle
3. Fetch fundamentals snapshot
4. Fetch theme / peer snapshot
5. Fetch recent news headlines
6. Fetch macro snapshot (rate, FX)
7. `technical_engine`: pattern detection → `TechnicalBuckets`
8. `flow_engine`: stage classification + continuity → `FlowBuckets`
9. `timeframe_engine`: weekly/monthly resample → `TimeframeBuckets`
10. `fundamentals_engine`: YoY growth direction → `FundamentalBuckets`
11. `theme_engine`: sector strength + peer → `ThemeBuckets`
12. `risk_engine`: overextension, vol, event → `RiskBuckets`
13. `trade_plan_engine`: structural support/resistance → `TradePlan`
14. `scoring_engine`: aggregate + PDF-aligned overrides → `FinalDecision`
