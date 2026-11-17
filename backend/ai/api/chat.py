"""
GeoHarvest AI V1 API Endpoints.

Provides provider status/configuration, Ollama auto-discovery,
conversation history CRUD, blocking chat, and SSE streaming chat.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.ai.models import (
    ChatRequest,
    ChatResponseOut,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdateRequest,
    OllamaPullRequest,
    ProviderConfigRequest,
    ProviderTestRequest,
)
from backend.ai.providers import (
    ProviderAuthError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from backend.ai.services.chat_service import chat_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
async def get_ai_status(refresh: bool = Query(default=True)):
    return await chat_service.get_status(refresh_ollama=refresh)


@router.get("/models")
async def list_ai_models(provider: Optional[str] = None):
    try:
        return await chat_service.list_models(provider_id=provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/configure")
async def configure_ai_provider(req: ProviderConfigRequest):
    try:
        return await chat_service.configure_provider(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/test")
async def test_ai_provider(req: ProviderTestRequest):
    try:
        return await chat_service.test_provider(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(limit: int = Query(default=50, ge=1, le=200)):
    return chat_service.list_conversations(limit=limit)


@router.post("/conversations", response_model=ConversationDetail)
async def create_conversation(req: Optional[ConversationCreateRequest] = None):
    try:
        return chat_service.create_conversation(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    try:
        return chat_service.get_conversation(conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/conversations/{conversation_id}", response_model=ConversationDetail)
async def update_conversation(conversation_id: str, req: ConversationUpdateRequest):
    try:
        return chat_service.update_conversation(conversation_id, req)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    try:
        chat_service.delete_conversation(conversation_id)
        return {"status": "deleted", "id": conversation_id}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/chat", response_model=ChatResponseOut)
async def ai_chat(req: ChatRequest):
    try:
        return await chat_service.chat(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ProviderAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ProviderRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/chat/stream")
async def ai_chat_stream(req: ChatRequest):
    try:
        prepared = chat_service.prepare_execution(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return StreamingResponse(
        chat_service.stream_prepared_events(prepared),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ollama/pull")
async def pull_ollama_model(req: OllamaPullRequest):
    try:
        model, base_url = chat_service.prepare_ollama_pull(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return StreamingResponse(
        chat_service.stream_ollama_pull(model=model, base_url=base_url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
