from fastapi import APIRouter, HTTPException
from backend.core.sources.registry import source_registry
from backend.core.sources.base import ConnectionTestResult

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("")
async def list_sources():
    sources = source_registry.list_sources()
    return [
        {
            "id": s.source_id,
            "name": s.name,
            "capabilities": s.capabilities.model_dump(),
        }
        for s in sources
    ]


@router.post("/{source_id}/test", response_model=ConnectionTestResult)
async def test_source(source_id: str):
    res = await source_registry.test_source_connection(source_id)
    return res
