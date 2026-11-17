"""Google Gemini API provider with SSE streaming and multi-turn history."""

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

logger = logging.getLogger("geoharvest.ai.provider.gemini")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _strip_model_prefix(model: str) -> str:
    clean = (model or "").strip()
    if clean.startswith("models/"):
        return clean.split("models/", 1)[1]
    return clean or PROVIDER_SPECS["gemini"]["default_model"]


class GeminiProvider(BaseAIProvider):
    """Direct async REST adapter for the Google Gemini generateContent & streaming SSE APIs."""

    provider_id = "gemini"
    supports_streaming = True

    async def list_models(self, config: Dict[str, Any]) -> List[str]:
        api_key = (config.get("_api_key") or "").strip()
        defaults = list(PROVIDER_SPECS["gemini"]["available_models"])
        if not api_key:
            return defaults

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{GEMINI_API_BASE}/models", headers={"x-goog-api-key": api_key})
                if resp.status_code == 200:
                    data = resp.json()
                    remote = [
                        (m.get("name") or "").replace("models/", "")
                        for m in (data.get("models") or [])
                        if "generateContent" in (m.get("supportedGenerationMethods") or [])
                        and (m.get("name") or "").replace("models/", "").startswith("gemini")
                    ]
                    if remote:
                        return list(dict.fromkeys(remote + defaults))
        except Exception as exc:
            logger.debug(f"Could not fetch live Gemini model catalog: {exc}")
        return defaults

    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        api_key = (config.get("_api_key") or "").strip()
        model = _strip_model_prefix(config.get("default_model") or "")
        if not api_key:
            return {"ok": False, "provider": "gemini", "message": "Google Gemini API key is not configured."}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{GEMINI_API_BASE}/models", headers={"x-goog-api-key": api_key})
                if resp.status_code == 200:
                    models = await self.list_models(config)
                    return {
                        "ok": True,
                        "provider": "gemini",
                        "models": models,
                        "message": f"Connected to Google Gemini API ({model}).",
                    }
                if resp.status_code in (400, 401, 403):
                    return {
                        "ok": False,
                        "provider": "gemini",
                        "message": f"Gemini authentication rejected (HTTP {resp.status_code}). Check your API key.",
                    }
                return {
                    "ok": False,
                    "provider": "gemini",
                    "message": f"Gemini API returned HTTP {resp.status_code}.",
                }
        except Exception as exc:
            return {"ok": False, "provider": "gemini", "message": f"Gemini connection error: {exc}"}

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

        contents = [
            {
                "role": "model" if turn["role"] == "assistant" else "user",
                "parts": [{"text": turn["content"]}],
            }
            for turn in turns
        ]

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction or DEFAULT_SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        url = f"{GEMINI_API_BASE}/models/{clean_model}:streamGenerateContent?alt=sse"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code in (401, 403):
                    raise ProviderAuthError("Google Gemini rejected the configured API key.")
                if resp.status_code >= 400:
                    raw_err = (await resp.aread()).decode("utf-8", errors="replace")
                    raise ProviderRequestError(f"Gemini API error ({resp.status_code}): {raw_err[:400]}")

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    candidates = chunk.get("candidates") or []
                    if not candidates:
                        continue
                    parts = (candidates[0].get("content") or {}).get("parts") or []
                    for part in parts:
                        text = part.get("text")
                        if text:
                            yield text
