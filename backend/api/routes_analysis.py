from fastapi import APIRouter, Depends, HTTPException

from backend.models.analysis_models import AnalysisResponse, AnalyzeRequest
from backend.services.analysis_service import AnalysisService
from backend.app_context import get_service


router = APIRouter()


@router.post("/api/analyze", response_model=AnalysisResponse)
def analyze(req: AnalyzeRequest, service: AnalysisService = Depends(get_service)):
    result = service.analyze(req)
    if result is None:
        raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {req.query}")
    return result


@router.get("/api/analyze/{query}", response_model=AnalysisResponse)
def analyze_get(query: str, service: AnalysisService = Depends(get_service)):
    """Convenience GET wrapper for frontend and ad-hoc curl testing."""
    result = service.analyze(AnalyzeRequest(query=query))
    if result is None:
        raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {query}")
    return result
