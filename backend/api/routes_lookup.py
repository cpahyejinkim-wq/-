from fastapi import APIRouter, Depends, Query

from backend.models.analysis_models import LookupResponse
from backend.services.analysis_service import AnalysisService
from backend.app_context import get_service


router = APIRouter()


@router.get("/api/lookup", response_model=LookupResponse)
def lookup(
    q: str = Query(..., min_length=1, description="Stock name or ticker fragment"),
    service: AnalysisService = Depends(get_service),
):
    candidates = service.resolver.search(q, limit=8)
    return LookupResponse(query=q, candidates=candidates)
