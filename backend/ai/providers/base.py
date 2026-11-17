"""Abstract base provider contract and shared error/message helpers."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider is unconfigured, offline, or its SDK/runtime cannot start."""


class ProviderAuthError(ProviderUnavailableError):
    """Raised when provider credentials fail authentication (HTTP 401/403)."""


class ProviderRequestError(RuntimeError):
    """Raised when an upstream provider request fails mid-turn."""


def normalize_turns(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Normalizes conversation turns to clean non-empty alternating `user` / `assistant` entries.
    Preserves full context cleanly across provider switches.
    """
    cleaned: List[Dict[str, str]] = []
    for item in messages:
        role = (item.get("role") or "").lower().strip()
        content = (item.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if cleaned and cleaned[-1]["role"] == role:
            cleaned[-1]["content"] = f"{cleaned[-1]['content']}\n\n{content}"
        else:
            cleaned.append({"role": role, "content": content})

    # Ensure conversation sequence starts with a user turn when non-empty
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    return cleaned


class BaseAIProvider(ABC):
    """Modular provider contract designed for V1 chat and future tools/agents."""

    provider_id: str
    supports_streaming: bool = True

    @abstractmethod
    async def list_models(self, config: Dict[str, Any]) -> List[str]:
        """Returns available models for this provider."""

    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Verifies connectivity/credentials without executing side effects."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """Yields incremental response text deltas as they stream from the provider."""
        if False:  # pragma: no cover - makes method a valid async generator signature
            yield ""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Executes a complete turn by aggregating `stream_chat`."""
        chunks: List[str] = []
        async for delta in self.stream_chat(
            messages=messages,
            model=model,
            config=config,
            system_instruction=system_instruction,
            temperature=temperature,
        ):
            chunks.append(delta)
        return "".join(chunks)
