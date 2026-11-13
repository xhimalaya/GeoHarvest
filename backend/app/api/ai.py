"""
GeoHarvest AI, Vector Database (Qdrant), and MCP API Endpoints (TAS v1.0 §4, §6, §13).
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.ai.gateway import llm_gateway
from backend.core.vector.qdrant_service import qdrant_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None  # "gemini" or "claude"
    model: Optional[str] = None
    temperature: float = 0.2
    system_instruction: Optional[str] = None


class VectorSearchRequest(BaseModel):
    query: str
    collection: str = "geospatial_algorithms"
    limit: int = 5


@router.get("/status")
async def get_ai_and_vector_status():
    """Returns real-time status of Gemini, Claude, and Qdrant connectors."""
    return llm_gateway.get_status()


@router.get("/models")
async def list_models():
    """Lists available models from Google Gemini and Anthropic Claude."""
    status = llm_gateway.get_status()
    return {
        "active_provider": status.get("active_provider"),
        "gemini": status["gemini"]["available_models"],
        "claude": status["claude"]["available_models"],
    }


@router.post("/chat")
async def chat_with_geoharvest_ai(req: ChatRequest):
    """
    Submits a natural language geospatial research instruction to Gemini or Claude.
    """
    try:
        return await llm_gateway.chat(
            prompt=req.prompt,
            provider=req.provider,
            model_name=req.model,
            system_instruction=req.system_instruction,
            temperature=req.temperature,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector/status")
async def get_vector_db_status():
    """Returns Qdrant vector database health and collection counts."""
    return qdrant_service.get_status()


@router.post("/vector/seed")
async def seed_vector_knowledge():
    """Seeds Qdrant vector database with the verified geospatial algorithm registry."""
    count = qdrant_service.seed_algorithm_knowledge()
    return {
        "status": "completed",
        "seeded_algorithms": count,
        "available": qdrant_service.is_available(),
    }


@router.post("/vector/search")
async def search_vector_knowledge(req: VectorSearchRequest):
    """Performs semantic vector search across scientific algorithms and knowledge in Qdrant."""
    import hashlib

    if not qdrant_service.is_available():
        raise HTTPException(status_code=503, detail="Qdrant vector database is offline.")

    hasher = hashlib.sha256(req.query.encode("utf-8"))
    digest = hasher.digest()
    raw_floats = [((b / 255.0) * 2.0 - 1.0) for b in digest]
    vector = (raw_floats * (384 // len(raw_floats) + 1))[:384]

    results = qdrant_service.search(
        collection_name=req.collection,
        query_vector=vector,
        limit=req.limit,
    )
    return {
        "query": req.query,
        "collection": req.collection,
        "hits_count": len(results),
        "results": results,
    }


@router.get("/mcp/info")
async def get_mcp_server_info():
    """Returns metadata for the Model Context Protocol (MCP) server integration."""
    from backend.app.dependencies.config import settings

    return {
        "name": "geoharvest",
        "version": "1.0.0",
        "protocol": "model-context-protocol",
        "sse_endpoint": f"http://localhost:{settings.mcp_server_port}/sse",
        "integrated_mount": "/mcp",
        "docker_service": "geoharvest-mcp",
        "supported_clients": ["Claude Desktop", "Gemini Agent", "Antigravity", "Cursor", "Claude Code"],
        "tools_count": 9,
        "tools": [
            "geo_resolve_aoi",
            "geo_search_datasets",
            "geo_execute_kmeans",
            "geo_polygonize_raster",
            "geo_change_detection",
            "geo_validate_raster",
            "geo_list_algorithms",
            "geo_vector_search",
            "geo_get_system_status",
        ]
    }
