from fastapi import APIRouter

from backend.services.analysis_service import ENGINE_VERSION

router = APIRouter()


@router.get("/api/health")
def health():
    return {"status": "ok", "engine_version": ENGINE_VERSION}
