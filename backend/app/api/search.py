from fastapi import APIRouter, HTTPException
from backend.app.schemas.schemas import SearchRequest, SearchResponse
from backend.core.discovery.manager import discovery_manager

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_scenes(request: SearchRequest):
    try:
        items = await discovery_manager.search(
            provider_id=request.provider_id,
            collection=request.collection,
            start_date=request.start_date,
            end_date=request.end_date,
            aoi=request.aoi,
            bbox=request.bbox,
            max_cloud_cover=request.max_cloud_cover or 100.0,
            limit=request.limit or 50
        )
        return SearchResponse(total_found=len(items), items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
