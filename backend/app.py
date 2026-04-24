"""FastAPI entry point.

Run locally:
    uvicorn backend.app:app --reload --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import routes_analysis, routes_health, routes_lookup
from backend.utils.logger import get_logger

logger = get_logger("app")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Chart Master Terminal",
        description="PDF-철학 기반 한국 주식 분석 대시보드 (Phase 1 mock mode)",
        version="0.1.0",
    )

    origins_env = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:8000,http://127.0.0.1:5500,file://",
    )
    origins = [o.strip() for o in origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r".*",  # dev-friendly; tighten in Phase 2
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_lookup.router)
    app.include_router(routes_analysis.router)

    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if os.path.isdir(frontend_dir):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
        logger.info("mounted frontend at / from %s", frontend_dir)
    else:
        logger.warning("frontend dir %s not found — API-only mode", frontend_dir)

    return app


app = create_app()
