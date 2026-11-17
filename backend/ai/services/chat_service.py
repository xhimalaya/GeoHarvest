"""
GeoHarvest AI V1 Chat Service.

Coordinates the four V1 providers (Gemini, Claude, Ollama, Antigravity),
manages persisted multi-provider conversation history, performs automatic
Ollama model discovery, and streams responses cleanly over SSE.
"""

import asyncio
import datetime
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.ai.config import DEFAULT_SYSTEM_PROMPT, PROVIDER_SPECS, V1_PROVIDER_IDS, ai_config
from backend.ai.models import (
    AIConversation,
    AIMessage,
    ChatRequest,
    ChatResponseOut,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdateRequest,
    MessageOut,
    OllamaPullRequest,
    ProviderConfigRequest,
    ProviderTestRequest,
)
from backend.ai.providers import (
    AntigravityProvider,
    BaseAIProvider,
    ClaudeProvider,
    GeminiProvider,
    OllamaProvider,
    ProviderAuthError,
    ProviderRequestError,
    ProviderUnavailableError,
    normalize_turns,
)
from backend.ai.services.project_context import build_project_context
from backend.app.dependencies.database import SessionLocal
from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.ai.service")


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _iso(dt: Optional[datetime.datetime]) -> str:
    return (dt or _utcnow()).isoformat()


def _derive_title(text: str) -> str:
    clean = " ".join((text or "").split()).strip()
    if not clean:
        return "New Conversation"
    if len(clean) <= 56:
        return clean
    return clean[:53].rstrip() + "..."


def _sse_frame(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@dataclass
class PreparedChat:
    conversation_id: Optional[str]
    conversation_title: str
    auto_created_conversation: bool
    user_message_id: Optional[int]
    provider_id: str
    model: str
    provider_config: Dict[str, Any]
    turns: List[Dict[str, str]]
    system_instruction: str
    temperature: float


class ChatService:
    """Orchestrates V1 providers, settings, conversation persistence, and SSE streaming."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory
        self.ollama = OllamaProvider()
        self.providers: Dict[str, BaseAIProvider] = {
            "gemini": GeminiProvider(),
            "claude": ClaudeProvider(),
            "ollama": self.ollama,
            "antigravity": AntigravityProvider(),
        }

    def get_provider(self, provider_id: str) -> BaseAIProvider:
        pid = ai_config.validate_provider_id(provider_id)
        return self.providers[pid]

    # ------------------------------------------------------------------
    # Provider status, model discovery & configuration
    # ------------------------------------------------------------------

    async def refresh_ollama_models(self, timeout: float = 1.5) -> Tuple[Optional[str], List[str]]:
        cfg = ai_config.get_provider_config("ollama")
        base_url = cfg.get("base_url") or PROVIDER_SPECS["ollama"]["default_base_url"]
        endpoint, models = await self.ollama.discover_models(base_url, timeout=timeout)
        if endpoint:
            ai_config.set_discovered_ollama_models(endpoint, models)
        return endpoint, models

    async def get_status(self, refresh_ollama: bool = True) -> Dict[str, Any]:
        ollama_reachable = False
        if refresh_ollama:
            endpoint, _ = await self.refresh_ollama_models(timeout=1.2)
            ollama_reachable = endpoint is not None
        status = ai_config.get_public_status()
        status["ollama"]["reachable"] = ollama_reachable
        return status

    async def list_models(self, provider_id: Optional[str] = None) -> Dict[str, Any]:
        if provider_id:
            pid = ai_config.validate_provider_id(provider_id)
            ollama_reachable: Optional[bool] = None
            if pid == "ollama":
                endpoint, models = await self.refresh_ollama_models(timeout=2.0)
                ollama_reachable = endpoint is not None
                cfg = ai_config.get_provider_config(pid)
                if not endpoint:
                    models = list(cfg.get("available_models") or [])
            else:
                cfg = ai_config.get_provider_config(pid)
                models = await self.providers[pid].list_models(cfg)
            payload: Dict[str, Any] = {
                "provider": pid,
                "models": models,
                "default_model": cfg.get("default_model") or (models[0] if models else ""),
                "allow_manual_model": cfg.get("allow_manual_model", False),
            }
            if ollama_reachable is not None:
                payload["reachable"] = ollama_reachable
            return payload

        models_map: Dict[str, List[str]] = {}
        for pid in V1_PROVIDER_IDS:
            if pid == "ollama":
                endpoint, discovered = await self.refresh_ollama_models(timeout=1.5)
                cfg = ai_config.get_provider_config(pid)
                models_map[pid] = discovered if endpoint else list(cfg.get("available_models") or [])
            else:
                cfg = ai_config.get_provider_config(pid)
                models_map[pid] = await self.providers[pid].list_models(cfg)
        return {"models": models_map}

    async def configure_provider(self, req: ProviderConfigRequest) -> Dict[str, Any]:
        pid = ai_config.validate_provider_id(req.provider)
        ai_config.update_provider(
            provider_id=pid,
            api_key=req.api_key,
            base_url=req.base_url,
            default_model=req.default_model,
            vertex_project=req.vertex_project,
            vertex_location=req.vertex_location,
            set_active=req.set_active,
        )
        ollama_reachable = False
        if pid == "ollama":
            endpoint, _ = await self.refresh_ollama_models(timeout=2.0)
            ollama_reachable = endpoint is not None

        status = ai_config.get_public_status()
        if pid == "ollama":
            status["ollama"]["reachable"] = ollama_reachable
        return {
            **status,
            "status": "ok",
            "provider": pid,
            "config": status[pid],
        }

    async def test_provider(self, req: ProviderTestRequest) -> Dict[str, Any]:
        pid = ai_config.validate_provider_id(req.provider)
        cfg = dict(ai_config.get_provider_config(pid))
        if req.api_key is not None and req.api_key.strip():
            cfg["_api_key"] = req.api_key.strip()
        if req.base_url is not None and req.base_url.strip():
            cfg["base_url"] = req.base_url.strip()
        if req.model is not None and req.model.strip():
            cfg["default_model"] = req.model.strip()
        if req.vertex_project is not None and req.vertex_project.strip():
            cfg["vertex_project"] = req.vertex_project.strip()
        if req.vertex_location is not None and req.vertex_location.strip():
            cfg["vertex_location"] = req.vertex_location.strip()

        result = await self.providers[pid].test_connection(cfg)
        if pid == "ollama" and result.get("ok") and result.get("endpoint") and not req.base_url:
            ai_config.set_discovered_ollama_models(result["endpoint"], result.get("models") or [])
        return result

    def prepare_ollama_pull(self, req: OllamaPullRequest) -> Tuple[str, str]:
        """Validates Ollama pull parameters before opening the SSE stream."""
        model = (req.model or "").strip()
        if not model:
            raise ValueError("Model tag is required (for example `qwen2.5-coder:3b`).")
        cfg = ai_config.get_provider_config("ollama")
        base_url = (req.base_url or "").strip() or cfg.get("base_url") or PROVIDER_SPECS["ollama"]["default_base_url"]
        return model, base_url

    async def stream_ollama_pull(self, model: str, base_url: str) -> AsyncIterator[str]:
        """Streams Ollama `/api/pull` progress as SSE events and refreshes available models on finish."""
        try:
            async for chunk in self.ollama.pull_model(model=model, base_url=base_url):
                yield _sse_frame("progress", chunk)

            endpoint, discovered = await self.ollama.discover_models(base_url, timeout=3.0)
            resolved_base = endpoint or base_url
            resolved_model = model
            if model in discovered:
                resolved_model = model
            elif f"{model}:latest" in discovered:
                resolved_model = f"{model}:latest"
            elif discovered:
                resolved_model = discovered[0]

            if endpoint:
                ai_config.set_discovered_ollama_models(resolved_base, discovered)
                if resolved_model:
                    ai_config.update_provider(
                        "ollama",
                        base_url=resolved_base,
                        default_model=resolved_model,
                        set_active=False,
                    )

            status = ai_config.get_public_status()
            status["ollama"]["reachable"] = endpoint is not None
            yield _sse_frame(
                "done",
                {
                    "status": "success",
                    "model": resolved_model,
                    "models": discovered,
                    "ollama": status["ollama"],
                },
            )
        except (asyncio.CancelledError, GeneratorExit):
            raise
        except ProviderUnavailableError as exc:
            yield _sse_frame("error", {"error": str(exc), "code": "provider_unavailable"})
        except ProviderRequestError as exc:
            yield _sse_frame("error", {"error": str(exc), "code": "provider_request"})
        except Exception as exc:
            logger.exception("Unexpected Ollama pull error for model=%s", model)
            yield _sse_frame("error", {"error": str(exc), "code": "unexpected_error"})

    # ------------------------------------------------------------------
    # Conversation persistence & history CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def _to_message_out(msg: AIMessage) -> MessageOut:
        return MessageOut(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            provider=msg.provider,
            model=msg.model,
            is_error=bool(msg.is_error),
            created_at=_iso(msg.created_at),
        )

    @classmethod
    def _to_conversation_detail(cls, conv: AIConversation) -> ConversationDetail:
        ordered = sorted(conv.messages, key=lambda m: m.id)
        return ConversationDetail(
            id=conv.id,
            title=conv.title,
            provider=conv.provider,
            model=conv.model,
            message_count=len(ordered),
            created_at=_iso(conv.created_at),
            updated_at=_iso(conv.updated_at),
            messages=[cls._to_message_out(m) for m in ordered],
        )

    def list_conversations(self, limit: int = 50) -> List[ConversationSummary]:
        with self._session_factory() as db:
            rows = (
                db.query(AIConversation, func.count(AIMessage.id).label("msg_count"))
                .outerjoin(AIMessage, AIConversation.id == AIMessage.conversation_id)
                .group_by(AIConversation.id)
                .order_by(AIConversation.updated_at.desc(), AIConversation.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                ConversationSummary(
                    id=conv.id,
                    title=conv.title,
                    provider=conv.provider,
                    model=conv.model,
                    message_count=int(msg_count or 0),
                    created_at=_iso(conv.created_at),
                    updated_at=_iso(conv.updated_at),
                )
                for conv, msg_count in rows
            ]

    def create_conversation(self, req: Optional[ConversationCreateRequest] = None) -> ConversationDetail:
        pid = ai_config.validate_provider_id(req.provider) if (req and req.provider) else ai_config.get_active_provider()
        cfg = ai_config.get_provider_config(pid)
        default_model = (
            (req.model.strip() if req and req.model else "")
            or cfg.get("default_model")
            or ((cfg.get("available_models") or [""])[0])
        )
        title = (req.title.strip() if req and req.title else "") or "New Conversation"
        now = _utcnow()

        with self._session_factory() as db:
            conv = AIConversation(
                id=uuid.uuid4().hex[:16],
                title=title,
                provider=pid,
                model=default_model,
                created_at=now,
                updated_at=now,
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            return self._to_conversation_detail(conv)

    def get_conversation(self, conversation_id: str) -> ConversationDetail:
        with self._session_factory() as db:
            conv = db.query(AIConversation).filter(AIConversation.id == conversation_id).first()
            if not conv:
                raise LookupError(f"Conversation '{conversation_id}' not found.")
            return self._to_conversation_detail(conv)

    def update_conversation(self, conversation_id: str, req: ConversationUpdateRequest) -> ConversationDetail:
        with self._session_factory() as db:
            conv = db.query(AIConversation).filter(AIConversation.id == conversation_id).first()
            if not conv:
                raise LookupError(f"Conversation '{conversation_id}' not found.")
            if req.title is not None and req.title.strip():
                conv.title = req.title.strip()[:120]
            if req.provider is not None:
                pid = ai_config.validate_provider_id(req.provider)
                if pid != conv.provider and req.model is None:
                    cfg = ai_config.get_provider_config(pid)
                    conv.model = cfg.get("default_model") or ((cfg.get("available_models") or [""])[0])
                conv.provider = pid
            if req.model is not None and req.model.strip():
                conv.model = req.model.strip()
            conv.updated_at = _utcnow()
            db.commit()
            db.refresh(conv)
            return self._to_conversation_detail(conv)

    def delete_conversation(self, conversation_id: str) -> None:
        with self._session_factory() as db:
            conv = db.query(AIConversation).filter(AIConversation.id == conversation_id).first()
            if not conv:
                raise LookupError(f"Conversation '{conversation_id}' not found.")
            db.delete(conv)
            db.commit()

    # ------------------------------------------------------------------
    # Execution & SSE Streaming
    # ------------------------------------------------------------------

    def prepare_execution(self, req: ChatRequest) -> PreparedChat:
        """
        Validates provider & input, resolves target model, loads/creates persistent
        conversation, records the user turn, and returns the execution bundle.
        """
        prompt_text = (req.prompt or "").strip()
        raw_messages = [m.model_dump() for m in (req.messages or [])]
        if not prompt_text and not raw_messages:
            raise ValueError("Provide a non-empty prompt or messages list.")

        system_instruction = (req.system_instruction or "").strip() or DEFAULT_SYSTEM_PROMPT

        with self._session_factory() as db:
            project_context = build_project_context(db, settings.aois_dir)
            system_instruction = f"{system_instruction.rstrip()}\n\n{project_context}"
            conv: Optional[AIConversation] = None
            if req.conversation_id:
                conv = db.query(AIConversation).filter(AIConversation.id == req.conversation_id).first()
                if not conv:
                    raise LookupError(f"Conversation '{req.conversation_id}' not found.")

            raw_pid = req.provider or (conv.provider if conv else None) or ai_config.get_active_provider()
            pid = ai_config.validate_provider_id(raw_pid)
            cfg = ai_config.get_provider_config(pid)

            same_provider_model = conv.model if (conv and conv.provider == pid and conv.model) else ""
            target_model = (
                (req.model or "").strip()
                or same_provider_model
                or cfg.get("default_model")
                or ((cfg.get("available_models") or [""])[0])
            )

            should_persist = conv is not None or bool(prompt_text and not raw_messages)
            if not should_persist:
                turns = normalize_turns(raw_messages)
                if not turns:
                    raise ValueError("At least one non-empty user message is required.")
                return PreparedChat(
                    conversation_id=None,
                    conversation_title="Stateless Chat",
                    auto_created_conversation=False,
                    user_message_id=None,
                    provider_id=pid,
                    model=target_model,
                    provider_config=cfg,
                    turns=turns,
                    system_instruction=system_instruction,
                    temperature=req.temperature,
                )

            now = _utcnow()
            auto_created = False
            if conv is None:
                auto_created = True
                conv = AIConversation(
                    id=uuid.uuid4().hex[:16],
                    title=_derive_title(prompt_text),
                    provider=pid,
                    model=target_model,
                    created_at=now,
                    updated_at=now,
                )
                db.add(conv)
                db.flush()
            else:
                conv.provider = pid
                if target_model:
                    conv.model = target_model
                conv.updated_at = now

            prior_turns = [
                {"role": m.role, "content": m.content}
                for m in sorted(conv.messages, key=lambda item: item.id)
                if not m.is_error
            ]

            new_user_content = prompt_text
            if not new_user_content and raw_messages:
                for item in reversed(raw_messages):
                    if item.get("role") == "user" and (item.get("content") or "").strip():
                        new_user_content = item["content"].strip()
                        break

            if not new_user_content:
                raise ValueError("Cannot send an empty user message.")

            if conv.title == "New Conversation" and not prior_turns:
                conv.title = _derive_title(new_user_content)

            user_msg = AIMessage(
                conversation_id=conv.id,
                role="user",
                content=new_user_content,
                provider=pid,
                model=target_model,
                is_error=False,
                created_at=now,
            )
            db.add(user_msg)
            db.commit()
            db.refresh(conv)
            db.refresh(user_msg)

            turns = normalize_turns(prior_turns + [{"role": "user", "content": new_user_content}])
            return PreparedChat(
                conversation_id=conv.id,
                conversation_title=conv.title,
                auto_created_conversation=auto_created,
                user_message_id=user_msg.id,
                provider_id=pid,
                model=target_model,
                provider_config=cfg,
                turns=turns,
                system_instruction=system_instruction,
                temperature=req.temperature,
            )

    def _rollback_empty_turn(self, prepared: PreparedChat) -> None:
        """Removes an unanswered user message (and empty auto-created thread) on pre-token error."""
        if prepared.user_message_id is None and not prepared.auto_created_conversation:
            return
        with self._session_factory() as db:
            if prepared.user_message_id is not None:
                msg = db.query(AIMessage).filter(AIMessage.id == prepared.user_message_id).first()
                if msg:
                    db.delete(msg)
            if prepared.auto_created_conversation and prepared.conversation_id:
                conv = db.query(AIConversation).filter(AIConversation.id == prepared.conversation_id).first()
                if conv:
                    remaining = (
                        db.query(func.count(AIMessage.id))
                        .filter(AIMessage.conversation_id == conv.id, AIMessage.id != prepared.user_message_id)
                        .scalar()
                    )
                    if not remaining:
                        db.delete(conv)
            db.commit()

    def _save_assistant_message(
        self,
        conversation_id: Optional[str],
        provider_id: str,
        model: str,
        content: str,
        is_error: bool = False,
    ) -> Optional[int]:
        if not conversation_id or not content:
            return None
        with self._session_factory() as db:
            conv = db.query(AIConversation).filter(AIConversation.id == conversation_id).first()
            if not conv:
                return None
            now = _utcnow()
            msg = AIMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                provider=provider_id,
                model=model,
                is_error=is_error,
                created_at=now,
            )
            conv.updated_at = now
            db.add(msg)
            db.commit()
            db.refresh(msg)
            return msg.id

    async def chat(self, req: ChatRequest) -> ChatResponseOut:
        prepared = self.prepare_execution(req)
        provider = self.get_provider(prepared.provider_id)

        try:
            text = await provider.chat(
                messages=prepared.turns,
                model=prepared.model,
                config=prepared.provider_config,
                system_instruction=prepared.system_instruction,
                temperature=prepared.temperature,
            )
        except Exception:
            self._rollback_empty_turn(prepared)
            raise

        msg_id = self._save_assistant_message(
            conversation_id=prepared.conversation_id,
            provider_id=prepared.provider_id,
            model=prepared.model,
            content=text,
            is_error=False,
        )
        return ChatResponseOut(
            conversation_id=prepared.conversation_id,
            provider=prepared.provider_id,
            model=prepared.model,
            text=text,
            finish_reason="stop",
            metadata={"message_id": msg_id} if msg_id is not None else {},
        )

    async def stream_prepared_events(self, prepared: PreparedChat) -> AsyncIterator[str]:
        """Streams SSE frames from an already-validated `PreparedChat` execution bundle."""
        provider = self.get_provider(prepared.provider_id)
        yield _sse_frame(
            "meta",
            {
                "conversation_id": prepared.conversation_id,
                "title": prepared.conversation_title,
                "provider": prepared.provider_id,
                "model": prepared.model,
            },
        )

        accumulated: List[str] = []
        completed = False
        try:
            async for delta in provider.stream_chat(
                messages=prepared.turns,
                model=prepared.model,
                config=prepared.provider_config,
                system_instruction=prepared.system_instruction,
                temperature=prepared.temperature,
            ):
                if delta:
                    accumulated.append(delta)
                    yield _sse_frame("delta", {"delta": delta})

            completed = True
            full_text = "".join(accumulated)
            msg_id = self._save_assistant_message(
                conversation_id=prepared.conversation_id,
                provider_id=prepared.provider_id,
                model=prepared.model,
                content=full_text,
                is_error=False,
            )
            yield _sse_frame(
                "done",
                {
                    "conversation_id": prepared.conversation_id,
                    "title": prepared.conversation_title,
                    "provider": prepared.provider_id,
                    "model": prepared.model,
                    "text": full_text,
                    "message_id": msg_id,
                },
            )
        except (asyncio.CancelledError, GeneratorExit):
            if not completed:
                if accumulated:
                    partial = "".join(accumulated).rstrip() + "\n\n_[Generation stopped]_"
                    self._save_assistant_message(
                        conversation_id=prepared.conversation_id,
                        provider_id=prepared.provider_id,
                        model=prepared.model,
                        content=partial,
                        is_error=False,
                    )
                else:
                    self._rollback_empty_turn(prepared)
            raise
        except ProviderAuthError as exc:
            if not accumulated:
                self._rollback_empty_turn(prepared)
            yield _sse_frame(
                "error",
                {"error": str(exc), "code": "provider_auth", "provider": prepared.provider_id},
            )
        except ProviderUnavailableError as exc:
            if not accumulated:
                self._rollback_empty_turn(prepared)
            yield _sse_frame(
                "error",
                {"error": str(exc), "code": "provider_unavailable", "provider": prepared.provider_id},
            )
        except ProviderRequestError as exc:
            if not accumulated:
                self._rollback_empty_turn(prepared)
            yield _sse_frame(
                "error",
                {"error": str(exc), "code": "provider_request", "provider": prepared.provider_id},
            )
        except Exception as exc:
            logger.exception("Unexpected streaming failure for provider=%s", prepared.provider_id)
            if not accumulated:
                self._rollback_empty_turn(prepared)
            yield _sse_frame(
                "error",
                {"error": str(exc), "code": "unexpected_error", "provider": prepared.provider_id},
            )


chat_service = ChatService()
