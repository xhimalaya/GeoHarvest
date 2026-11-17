"""Local Ollama provider with automatic model discovery and NDJSON streaming."""

import json
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import httpx

from backend.ai.config import DEFAULT_SYSTEM_PROMPT, PROVIDER_SPECS
from backend.ai.providers.base import (
    BaseAIProvider,
    ProviderRequestError,
    ProviderUnavailableError,
    normalize_turns,
)

logger = logging.getLogger("geoharvest.ai.provider.ollama")


def candidate_ollama_urls(base_url: str) -> List[str]:
    """Builds candidate Ollama URLs across Docker Compose, host bridge, and local loopback."""
    clean = (base_url or PROVIDER_SPECS["ollama"]["default_base_url"]).strip().rstrip("/")
    candidates = [clean]
    if "localhost" in clean or "127.0.0.1" in clean:
        for host in ("host.docker.internal", "172.17.0.1", "ollama"):
            alt = clean.replace("localhost", host).replace("127.0.0.1", host)
            if alt not in candidates:
                candidates.append(alt)
    elif "://ollama:" in clean or clean.endswith("://ollama"):
        for host in ("host.docker.internal", "localhost"):
            alt = clean.replace("://ollama", f"://{host}")
            if alt not in candidates:
                candidates.append(alt)
    elif "host.docker.internal" in clean:
        env_url = os.environ.get("OLLAMA_BASE_URL", "").strip().rstrip("/")
        if env_url and env_url not in candidates:
            candidates.insert(0, env_url)
    return candidates


class OllamaProvider(BaseAIProvider):
    """Connects to a local/remote Ollama instance, discovers pulled models, and streams /api/chat."""

    provider_id = "ollama"
    supports_streaming = True

    async def discover_models(self, base_url: str, timeout: float = 3.0) -> Tuple[Optional[str], List[str]]:
        """Probes Ollama /api/tags and returns `(reachable_endpoint, model_names)`."""
        first_reachable: Optional[str] = None
        for cand in candidate_ollama_urls(base_url):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(f"{cand}/api/tags")
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [
                            m.get("name")
                            for m in (data.get("models") or [])
                            if isinstance(m, dict) and m.get("name")
                        ]
                        if models:
                            return cand, models
                        if first_reachable is None:
                            first_reachable = cand
            except Exception:
                continue
        if first_reachable is not None:
            return first_reachable, []
        return None, []

    async def list_models(self, config: Dict[str, Any]) -> List[str]:
        base_url = config.get("base_url") or PROVIDER_SPECS["ollama"]["default_base_url"]
        _, models = await self.discover_models(base_url, timeout=2.5)
        if models:
            return models
        return list(config.get("available_models") or [])

    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        base_url = config.get("base_url") or PROVIDER_SPECS["ollama"]["default_base_url"]
        endpoint, models = await self.discover_models(base_url, timeout=5.0)
        if not endpoint:
            return {
                "ok": False,
                "provider": "ollama",
                "models": [],
                "message": f"Ollama is unreachable at {base_url}. Ensure `ollama serve` is running.",
            }
        if not models:
            return {
                "ok": True,
                "provider": "ollama",
                "endpoint": endpoint,
                "models": [],
                "message": f"Connected to Ollama at {endpoint}, but no local models are pulled yet (run `ollama pull <model>`).",
            }
        return {
            "ok": True,
            "provider": "ollama",
            "endpoint": endpoint,
            "models": models,
            "message": f"Connected to Ollama at {endpoint} ({len(models)} model(s) discovered).",
        }

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        base_url = config.get("base_url") or PROVIDER_SPECS["ollama"]["default_base_url"]
        target_model = (model or config.get("default_model") or "").strip()
        if not target_model:
            _, discovered = await self.discover_models(base_url, timeout=2.5)
            if discovered:
                target_model = discovered[0]
            else:
                raise ProviderUnavailableError(
                    "No Ollama model is selected or installed. Start Ollama and pull a model (e.g. `ollama pull llama3.3`)."
                )

        turns = normalize_turns(messages)
        if not turns:
            raise ProviderRequestError("Cannot send an empty conversation to Ollama.")

        chat_messages = [{"role": "system", "content": system_instruction or DEFAULT_SYSTEM_PROMPT}] + turns
        payload = {
            "model": target_model,
            "messages": chat_messages,
            "stream": True,
            "options": {"temperature": temperature},
        }

        last_err: Optional[Exception] = None
        for cand in candidate_ollama_urls(base_url):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=8.0)) as client:
                    async with client.stream("POST", f"{cand}/api/chat", json=payload) as resp:
                        if resp.status_code >= 400:
                            raw_err = (await resp.aread()).decode("utf-8", errors="replace")
                            raise ProviderRequestError(f"Ollama returned HTTP {resp.status_code}: {raw_err[:400]}")

                        async for line in resp.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if chunk.get("error"):
                                raise ProviderRequestError(f"Ollama error: {chunk['error']}")
                            delta = (chunk.get("message") or {}).get("content") or ""
                            if delta:
                                yield delta
                        return
            except ProviderRequestError:
                raise
            except Exception as exc:
                last_err = exc
                continue

        raise ProviderUnavailableError(f"Could not connect to Ollama at {base_url}: {last_err}")

    async def pull_model(self, model: str, base_url: str) -> AsyncIterator[Dict[str, Any]]:
        """Pulls an Ollama model via `/api/pull` and yields normalized progress events."""
        target_model = (model or "").strip()
        if not target_model:
            raise ProviderRequestError("Provide an Ollama model tag to pull (e.g. `qwen2.5-coder:3b`).")

        endpoint, _ = await self.discover_models(base_url, timeout=4.0)
        if not endpoint:
            raise ProviderUnavailableError(
                f"Ollama is unreachable at {base_url}. Ensure `ollama serve` is running before pulling."
            )

        payload = {"model": target_model, "stream": True}
        async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0, connect=8.0)) as client:
            async with client.stream("POST", f"{endpoint}/api/pull", json=payload) as resp:
                if resp.status_code >= 400:
                    raw_err = (await resp.aread()).decode("utf-8", errors="replace")
                    raise ProviderRequestError(f"Ollama pull returned HTTP {resp.status_code}: {raw_err[:400]}")

                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise ProviderRequestError(f"Ollama pull failed: {chunk['error']}")

                    total = chunk.get("total")
                    completed = chunk.get("completed")
                    percent: Optional[float] = None
                    if isinstance(total, (int, float)) and total > 0 and isinstance(completed, (int, float)):
                        percent = round(min(100.0, max(0.0, completed * 100.0 / total)), 1)

                    yield {
                        "endpoint": endpoint,
                        "model": target_model,
                        "status": chunk.get("status") or "pulling",
                        "digest": chunk.get("digest"),
                        "total": total,
                        "completed": completed,
                        "percent": percent,
                    }
