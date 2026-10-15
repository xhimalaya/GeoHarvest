from typing import Dict, Any, Optional, List
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.crs.engine import crs_engine

router = APIRouter(prefix="/api/crs", tags=["crs"])


class CRSRecommendRequest(BaseModel):
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None


@router.post("/recommend")
async def recommend_crs(request: CRSRecommendRequest):
    input_data = request.geometry or request.bbox
    return crs_engine.recommend(input_data)
