"""Anthropic Claude API provider with SSE streaming and multi-turn history."""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from backend.ai.config import DEFAULT_SYSTEM_PROMPT, PROVIDER_SPECS
from backend.ai.providers.base import (
    BaseAIProvider,
    ProviderAuthError,
    ProviderRequestError,
    ProviderUnavailableError,
    normalize_turns,
)

logger = logging.getLogger("geoharvest.ai.provider.claude")


class ClaudeProvider(BaseAIProvider):
    """Direct async REST adapter for Anthropic Claude Messages API."""

    provider_id = "claude"
    supports_streaming = True

    @staticmethod
    def _messages_url(config: Dict[str, Any]) -> str:
        base = (config.get("base_url") or PROVIDER_SPECS["claude"]["default_base_url"]).strip().rstrip("/")
        return base if base.endswith("/messages") else f"{base}/messages"

    async def list_models(self, config: Dict[str, Any]) -> List[str]:
        api_key = (config.get("_api_key") or "").strip()
        defaults = list(PROVIDER_SPECS["claude"]["available_models"])
        if not api_key:
            return defaults

        base = (config.get("base_url") or PROVIDER_SPECS["claude"]["default_base_url"]).strip().rstrip("/")
        if base.endswith("/messages"):
            base = base[:-len("/messages")]
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{base}/models",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    remote = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict) and m.get("id")]
                    if remote:
                        return list(dict.fromkeys(remote + defaults))
        except Exception as exc:
            logger.debug(f"Could not fetch live Claude model list: {exc}")
        return defaults

    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        api_key = (config.get("_api_key") or "").strip()
        model = (config.get("default_model") or PROVIDER_SPECS["claude"]["default_model"]).strip()
        if not api_key:
            return {"ok": False, "provider": "claude", "message": "Anthropic Claude API key is not configured."}

        base = (config.get("base_url") or PROVIDER_SPECS["claude"]["default_base_url"]).strip().rstrip("/")
        if base.endswith("/messages"):
            base = base[:-len("/messages")]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base}/models",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )
                if resp.status_code in (200, 404):
                    models = await self.list_models(config)
                    return {
                        "ok": True,
                        "provider": "claude",
                        "models": models,
                        "message": f"Connected to Anthropic Claude API ({model}).",
                    }
                if resp.status_code in (401, 403):
                    return {
                        "ok": False,
                        "provider": "claude",
                        "message": f"Claude authentication failed (HTTP {resp.status_code}). Check your API key.",
                    }
                return {
                    "ok": False,
                    "provider": "claude",
                    "message": f"Claude API returned HTTP {resp.status_code}.",
                }
        except Exception as exc:
            return {"ok": False, "provider": "claude", "message": f"Claude connection error: {exc}"}

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
                "Anthropic Claude is not configured. Open Settings / Connectors to add an Anthropic API key."
            )

        target_model = (model or config.get("default_model") or PROVIDER_SPECS["claude"]["default_model"]).strip()
        turns = normalize_turns(messages)
        if not turns:
            raise ProviderRequestError("Cannot send an empty conversation to Claude.")

        url = self._messages_url(config)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "max_tokens": 4096,
            "system": system_instruction or DEFAULT_SYSTEM_PROMPT,
            "messages": turns,
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code in (401, 403):
                    raise ProviderAuthError("Anthropic Claude rejected the configured API key.")
                if resp.status_code >= 400:
                    raw_err = (await resp.aread()).decode("utf-8", errors="replace")
                    raise ProviderRequestError(f"Claude API error ({resp.status_code}): {raw_err[:400]}")

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    etype = event.get("type")
                    if etype == "content_block_delta":
                        delta = event.get("delta") or {}
                        if delta.get("type") == "text_delta" and delta.get("text"):
                            yield delta["text"]
                    elif etype == "error":
                        err_info = event.get("error") or {}
                        raise ProviderRequestError(err_info.get("message") or "Claude stream returned an error.")
