"""Google Gemini API provider using the official google-genai SDK Interactions API."""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

try:
    from google.genai._interactions import (
        APIConnectionError as _InteractionsConnectionError,
        APITimeoutError as _InteractionsTimeoutError,
    )
except ImportError:  # pragma: no cover - defensive fallback across SDK versions
    _InteractionsConnectionError = None  # type: ignore[assignment]
    _InteractionsTimeoutError = None  # type: ignore[assignment]

from backend.ai.config import (
    DEFAULT_SYSTEM_PROMPT,
    LEGACY_GEMINI_RETIRED_MODELS,
    PROVIDER_SPECS,
    get_default_gemini_model,
)
from backend.ai.providers.base import (
    BaseAIProvider,
    ProviderAuthError,
    ProviderRequestError,
    ProviderUnavailableError,
    normalize_turns,
)

logger = logging.getLogger("geoharvest.ai.provider.gemini")

_REQUEST_TIMEOUT_MS = 120_000
_CONNECTIVITY_TIMEOUT_MS = 10_000
_THINKING_LEVEL = "low"


def _strip_model_prefix(model: str) -> str:
    clean = (model or "").strip()
    if clean.startswith("publishers/google/models/"):
        clean = clean.split("publishers/google/models/", 1)[1]
    elif clean.startswith("models/"):
        clean = clean.split("models/", 1)[1]
    return clean or get_default_gemini_model()


def _create_genai_client(api_key: str, timeout_ms: int = _REQUEST_TIMEOUT_MS) -> genai.Client:
    """Instantiates a backend-only Google Gen AI SDK client for a single request."""
    return genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(
            api_version="v1beta",
            timeout=timeout_ms,
            retry_options=genai_types.HttpRetryOptions(attempts=1),
        ),
    )


async def _close_aio_client(client: Any) -> None:
    aio = getattr(client, "aio", None)
    aclose = getattr(aio, "aclose", None)
    if callable(aclose):
        try:
            await aclose()
        except Exception:
            pass


def _default_gemini_models() -> List[str]:
    return list(dict.fromkeys([get_default_gemini_model(), *PROVIDER_SPECS["gemini"]["available_models"]]))


def _extract_error_message(exc: BaseException) -> str:
    for container in (getattr(exc, "body", None), getattr(exc, "details", None)):
        if isinstance(container, dict):
            err_inner = container.get("error")
            if isinstance(err_inner, dict) and isinstance(err_inner.get("message"), str):
                return err_inner["message"].strip()
            if isinstance(container.get("message"), str):
                return container["message"].strip()
    msg = getattr(exc, "message", None)
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    return str(exc).strip() or exc.__class__.__name__


def _is_auth_message(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "api key not valid",
            "api_key_invalid",
            "invalid api key",
            "permission denied",
            "permission_denied",
            "unauthenticated",
        )
    )


def _translate_gemini_error(exc: BaseException, model: str = "") -> Exception:
    """Maps google-genai and Interactions SDK exceptions to GeoHarvest provider errors."""
    if isinstance(exc, (ProviderAuthError, ProviderUnavailableError, ProviderRequestError)):
        return exc

    if isinstance(exc, genai_errors.ContinuationInterruptedError) and exc.__cause__ is not None:
        return _translate_gemini_error(exc.__cause__, model=model)

    timeout_types: tuple[type[BaseException], ...] = (
        TimeoutError,
        asyncio.TimeoutError,
        httpx.TimeoutException,
    )
    if _InteractionsTimeoutError is not None:
        timeout_types = (*timeout_types, _InteractionsTimeoutError)
    if isinstance(exc, timeout_types):
        return ProviderUnavailableError("Google Gemini request timed out. Please try again.")

    if _InteractionsConnectionError is not None and isinstance(exc, _InteractionsConnectionError):
        return ProviderUnavailableError(
            f"Could not connect to Google Gemini API: {_extract_error_message(exc)}"
        )

    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        status_code = getattr(exc, "code", None)
    msg = _extract_error_message(exc)
    details = getattr(exc, "details", None) or getattr(exc, "body", None) or ""
    full_text = f"{msg} {details}"

    if status_code in (401, 403) or (status_code == 400 and _is_auth_message(full_text)):
        return ProviderAuthError("Google Gemini rejected the configured API key.")

    if status_code == 404:
        model_label = model or get_default_gemini_model()
        return ProviderRequestError(
            f"Gemini model '{model_label}' is unavailable or not found (HTTP 404): {msg[:300]}"
        )

    if status_code == 429:
        return ProviderRequestError(
            f"Google Gemini rate limit exceeded (HTTP 429). Please retry shortly: {msg[:300]}"
        )

    if isinstance(status_code, int) and 500 <= status_code < 600:
        return ProviderUnavailableError(
            f"Google Gemini service is temporarily unavailable (HTTP {status_code}): {msg[:300]}"
        )

    if isinstance(status_code, int) and 400 <= status_code < 500:
        return ProviderRequestError(f"Gemini API error (HTTP {status_code}): {msg[:300]}")

    if isinstance(exc, (httpx.HTTPError, OSError)):
        return ProviderUnavailableError(f"Could not connect to Google Gemini API: {msg}")

    return ProviderRequestError(f"Gemini API error: {msg[:300]}")


def _translate_stream_error(err_obj: Any, model: str = "") -> Exception:
    """Maps an in-band Interactions SSE error event or failed status to a provider error."""
    code_raw = str(getattr(err_obj, "code", "") or "").lower()
    message = str(getattr(err_obj, "message", "") or err_obj or "Gemini interaction failed.").strip()
    combined = f"{code_raw} {message}".lower()

    if _is_auth_message(combined) or "401" in combined or "403" in combined:
        return ProviderAuthError("Google Gemini rejected the configured API key.")
    if "not_found" in combined or "not found" in combined or "404" in combined:
        model_label = model or get_default_gemini_model()
        return ProviderRequestError(
            f"Gemini model '{model_label}' is unavailable or not found (HTTP 404): {message[:300]}"
        )
    if "rate_limit" in combined or "resource_exhausted" in combined or "429" in combined:
        return ProviderRequestError(
            f"Google Gemini rate limit exceeded (HTTP 429). Please retry shortly: {message[:300]}"
        )
    if "timeout" in combined or "deadline" in combined:
        return ProviderUnavailableError("Google Gemini request timed out. Please try again.")
    if "unavailable" in combined or "internal" in combined or "500" in combined or "503" in combined:
        return ProviderUnavailableError(f"Google Gemini service is temporarily unavailable: {message[:300]}")
    return ProviderRequestError(f"Gemini API error: {message[:300]}")


def _build_interaction_input(turns: List[Dict[str, str]]) -> Any:
    """Builds single-turn string or stateless multi-turn step history for Interactions API."""
    if len(turns) == 1:
        return turns[0]["content"]
    return [
        {
            "type": "model_output" if turn["role"] == "assistant" else "user_input",
            "content": [{"type": "text", "text": turn["content"]}],
        }
        for turn in turns
    ]


def _extract_stream_text_delta(event: Any) -> Optional[str]:
    event_type = getattr(event, "event_type", None)
    if event_type in ("step.delta", "content.delta"):
        delta = getattr(event, "delta", None)
        if getattr(delta, "type", None) == "text":
            text = getattr(delta, "text", None)
            if isinstance(text, str) and text:
                return text
    return None


def _extract_interaction_text(interaction: Any) -> str:
    output_text = getattr(interaction, "output_text", None)
    if isinstance(output_text, str) and output_text:
        return output_text

    steps = getattr(interaction, "steps", None) or []
    step_texts: List[str] = []
    for step in reversed(steps):
        step_type = getattr(step, "type", None)
        if step_type == "user_input":
            break
        if step_type != "model_output":
            continue
        block_texts: List[str] = []
        for block in getattr(step, "content", None) or []:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", None)
                if isinstance(text, str) and text:
                    block_texts.append(text)
        if block_texts:
            step_texts.append("".join(block_texts))
    return "".join(reversed(step_texts))


class GeminiProvider(BaseAIProvider):
    """Async adapter for Google Gemini using the official google-genai Interactions API."""

    provider_id = "gemini"
    supports_streaming = True

    async def _fetch_remote_models(self, api_key: str) -> List[str]:
        defaults = _default_gemini_models()
        client = _create_genai_client(api_key, timeout_ms=_CONNECTIVITY_TIMEOUT_MS)
        remote: List[str] = []
        try:
            pager = await client.aio.models.list(config={"query_base": True})
            async for item in pager:
                raw_name = getattr(item, "name", "") or ""
                name = _strip_model_prefix(raw_name)
                if not name.startswith("gemini") or name in LEGACY_GEMINI_RETIRED_MODELS:
                    continue
                actions = getattr(item, "supported_actions", None)
                if actions and "generateContent" not in actions and "interactions" not in actions:
                    continue
                remote.append(name)
        finally:
            await _close_aio_client(client)

        return list(dict.fromkeys(remote))

    @staticmethod
    def resolve_model(model: str, config: Dict[str, Any]) -> str:
        """Updates saved conversations that still point at the retired application default."""
        selected = _strip_model_prefix(model or config.get("default_model") or "")
        if selected in LEGACY_GEMINI_RETIRED_MODELS:
            return _strip_model_prefix(config.get("default_model") or "")
        return selected

    async def list_models(self, config: Dict[str, Any]) -> List[str]:
        api_key = (config.get("_api_key") or "").strip()
        defaults = _default_gemini_models()
        if not api_key:
            return defaults

        try:
            remote = await self._fetch_remote_models(api_key)
            return list(dict.fromkeys([*defaults, *remote]))
        except Exception as exc:
            logger.debug("Could not fetch live Gemini model catalog: %s", exc)
            return defaults

    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        api_key = (config.get("_api_key") or "").strip()
        model = self.resolve_model(config.get("default_model") or "", config)
        if not api_key:
            return {"ok": False, "provider": "gemini", "message": "Google Gemini API key is not configured."}

        try:
            remote_models = await self._fetch_remote_models(api_key)
            models = list(dict.fromkeys([*_default_gemini_models(), *remote_models]))
            if remote_models and model not in remote_models:
                return {
                    "ok": False,
                    "provider": "gemini",
                    "models": models,
                    "message": (
                        f"Gemini model '{model}' is unavailable (HTTP 404). "
                        "Choose another model or update GEMINI_MODEL."
                    ),
                }
            return {
                "ok": True,
                "provider": "gemini",
                "models": models,
                "message": f"Connected to Google Gemini API ({model}).",
            }
        except Exception as exc:
            translated = _translate_gemini_error(exc, model=model)
            if isinstance(translated, ProviderAuthError):
                return {
                    "ok": False,
                    "provider": "gemini",
                    "message": f"Gemini authentication rejected: {translated}",
                }
            return {"ok": False, "provider": "gemini", "message": str(translated)}

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        api_key = (config.get("_api_key") or "").strip()
        if not api_key:
            raise ProviderUnavailableError(
                "Google Gemini is not configured. Open Settings / Connectors to add a Gemini API key."
            )

        clean_model = _strip_model_prefix(model or config.get("default_model") or "")
        turns = normalize_turns(messages)
        if not turns:
            raise ProviderRequestError("Cannot send an empty conversation to Gemini.")

        interaction_input = _build_interaction_input(turns)
        client = _create_genai_client(api_key, timeout_ms=_REQUEST_TIMEOUT_MS)
        stream: Any = None
        emitted_any_text = False

        try:
            stream = await client.aio.interactions.create(
                model=clean_model,
                input=interaction_input,
                system_instruction=system_instruction or DEFAULT_SYSTEM_PROMPT,
                generation_config={"thinking_level": _THINKING_LEVEL},
                store=False,
                stream=True,
                timeout=_REQUEST_TIMEOUT_MS / 1000.0,
            )

            async for event in stream:
                event_type = getattr(event, "event_type", None)
                if event_type == "error":
                    raise _translate_stream_error(getattr(event, "error", None), model=clean_model)

                delta_text = _extract_stream_text_delta(event)
                if delta_text:
                    emitted_any_text = True
                    yield delta_text
                    continue

                if event_type == "interaction.completed":
                    interaction = getattr(event, "interaction", None)
                    status = getattr(interaction, "status", None)
                    if status == "failed":
                        raise _translate_stream_error(getattr(interaction, "error", None), model=clean_model)
                    if status != "requires_continuation" and not emitted_any_text and interaction is not None:
                        fallback_text = _extract_interaction_text(interaction)
                        if fallback_text:
                            emitted_any_text = True
                            yield fallback_text
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise _translate_gemini_error(exc, model=clean_model) from exc
        finally:
            close_stream = getattr(stream, "close", None)
            if callable(close_stream):
                try:
                    res = close_stream()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass
            await _close_aio_client(client)
