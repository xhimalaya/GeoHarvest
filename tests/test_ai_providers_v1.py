"""
Comprehensive V1 test suite testing each GeoHarvest AI provider individually
(Gemini, Claude, Ollama, Antigravity), credential security, Ollama auto-discovery,
multi-provider conversation persistence, SSE streaming, and cancellation handling.
"""

import asyncio
import json
import stat
from pathlib import Path
from typing import Any, Dict, List
import pytest

from backend.ai.config import AIConfigStore, DEFAULT_SYSTEM_PROMPT, PROVIDER_SPECS, V1_PROVIDER_IDS, ai_config
from backend.ai.models import ChatRequest
from backend.ai.providers.antigravity import AntigravityProvider, ag_types
from backend.ai.providers.base import (
    ProviderAuthError,
    ProviderUnavailableError,
    normalize_turns,
)
from backend.ai.providers.claude import ClaudeProvider
from backend.ai.providers.gemini import GeminiProvider
from backend.ai.providers.ollama import OllamaProvider
from backend.ai.services.chat_service import chat_service


# ---------------------------------------------------------------------------
# Helpers for deterministic mocked HTTP & SDK streams
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None, lines: List[str] | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self._lines = lines or []
        self._text = text or json.dumps(json_data or {})

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def json(self):
        return self._json_data

    async def aread(self) -> bytes:
        return self._text.encode("utf-8")

    async def aiter_lines(self):
        for line in self._lines:
            yield line


def _make_mock_httpx_client(recorder: List[Dict[str, Any]], handler):
    class _MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, **kwargs):
            recorder.append({"method": "GET", "url": url, **kwargs})
            return handler("GET", url, kwargs)

        def stream(self, method: str, url: str, **kwargs):
            recorder.append({"method": method, "url": url, **kwargs})
            return handler(method, url, kwargs)

    return _MockAsyncClient


@pytest.fixture(autouse=True)
def isolated_ai_store(tmp_path, monkeypatch):
    """Isolates ai_providers.json and clears AI env keys so tests are deterministic and non-destructive."""
    cfg_file = tmp_path / "ai_providers.json"
    monkeypatch.setattr(ai_config, "_config_path", cfg_file)
    monkeypatch.setattr(ai_config, "_configs", {})
    monkeypatch.setattr(ai_config, "_active_provider", "gemini")

    for var in (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "GEOHARVEST_GEMINI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTIGRAVITY_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)

    from backend.app.dependencies.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "gemini_default_model", "gemini-3.1-pro-preview")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    yield cfg_file


# ---------------------------------------------------------------------------
# 1. Config & Credential Security Tests
# ---------------------------------------------------------------------------


def test_config_store_prunes_legacy_providers_and_sets_0600(tmp_path):
    legacy_path = tmp_path / "legacy_ai.json"
    legacy_path.write_text(
        json.dumps(
            {
                "active_provider": "chatgpt",
                "providers": {
                    "chatgpt": {"api_key": "sk-legacy"},
                    "deepseek": {"api_key": "ds-legacy"},
                    "clawai": {"base_url": "http://localhost:8080"},
                    "custom": {"base_url": "http://localhost:9999"},
                    "gemini": {"api_key": "AIza-keep-me-123456"},
                },
            }
        ),
        encoding="utf-8",
    )

    store = AIConfigStore(config_path=legacy_path)
    store.update_provider("gemini", default_model="gemini-3.1-pro-preview")
    status = store.get_public_status()

    assert set(V1_PROVIDER_IDS) == {"gemini", "claude", "ollama", "antigravity"}
    for removed in ("chatgpt", "deepseek", "clawai", "custom"):
        assert removed not in status
    assert status["active_provider"] in V1_PROVIDER_IDS
    assert status["gemini"]["configured"] is True
    assert status["gemini"]["default_model"] == "gemini-3.1-pro-preview"
    assert "gemini-3.8-flash" in status["gemini"]["available_models"]
    assert status["gemini"]["masked_key"].startswith("AIza")
    assert "AIza-keep-me-123456" not in json.dumps(status)

    mode = stat.S_IMODE(legacy_path.stat().st_mode)
    assert mode == 0o600


def test_gemini_model_env_and_legacy_default_migration(tmp_path, monkeypatch):
    cfg_path = tmp_path / "ai_legacy_gemini.json"
    cfg_path.write_text(
        json.dumps(
            {
                "active_provider": "gemini",
                "providers": {
                    "gemini": {
                        "api_key": "AIza-legacy-key-9999",
                        "default_model": "gemini-2.5-pro",
                        "custom_models": ["gemini-2.5-pro"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    store = AIConfigStore(config_path=cfg_path)
    default_cfg = store.get_provider_config("gemini")
    assert default_cfg["default_model"] == "gemini-3.1-pro-preview"
    assert "gemini-2.5-pro" not in default_cfg["available_models"]
    assert "gemini-3.8-flash" in default_cfg["available_models"]

    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    env_cfg = store.get_provider_config("gemini")
    assert env_cfg["default_model"] == "gemini-3.8-flash"
    assert "gemini-3.1-pro-preview" in env_cfg["available_models"]
    assert "gemini-3.8-flash" in env_cfg["available_models"]


def test_normalize_turns_alternation():
    turns = normalize_turns(
        [
            {"role": "assistant", "content": "ignored leading assistant"},
            {"role": "user", "content": "Hi"},
            {"role": "user", "content": "GeoHarvest"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "system", "content": "skip system"},
            {"role": "user", "content": "   "},
        ]
    )
    assert turns == [
        {"role": "user", "content": "Hi\n\nGeoHarvest"},
        {"role": "assistant", "content": "Hello!"},
    ]


# ---------------------------------------------------------------------------
# 2. Individual Provider Test: Google Gemini (google-genai Interactions API)
# ---------------------------------------------------------------------------


def _make_mock_genai_factory(
    interactions_calls: List[Dict[str, Any]],
    *,
    models_handler,
    interactions_handler,
):
    from types import SimpleNamespace

    class _MockPager:
        def __init__(self, items: List[Any]):
            self._items = items
            self._idx = 0

        def __aiter__(self):
            self._idx = 0
            return self

        async def __anext__(self):
            if self._idx >= len(self._items):
                raise StopAsyncIteration
            item = self._items[self._idx]
            self._idx += 1
            return item

    class _MockModels:
        def __init__(self, api_key: str):
            self._api_key = api_key

        async def list(self, **kwargs):
            return _MockPager(models_handler(self._api_key, kwargs))

    class _MockInteractions:
        def __init__(self, api_key: str):
            self._api_key = api_key

        async def create(self, **kwargs):
            interactions_calls.append({"api_key": self._api_key, **kwargs})
            return interactions_handler(self._api_key, kwargs)

    class _MockAio:
        def __init__(self, api_key: str):
            self.models = _MockModels(api_key)
            self.interactions = _MockInteractions(api_key)
            self.closed = False

        async def aclose(self):
            self.closed = True

    class _MockClient:
        def __init__(self, api_key: str, timeout_ms: int = 120_000):
            self.api_key = api_key
            self.timeout_ms = timeout_ms
            self.aio = _MockAio(api_key)

    return _MockClient


@pytest.mark.asyncio
async def test_gemini_interactions_connection_chat_multiturn_and_models(monkeypatch):
    from types import SimpleNamespace

    provider = GeminiProvider()
    cfg = ai_config.get_provider_config("gemini")
    assert cfg["default_model"] == "gemini-3.1-pro-preview"
    assert "gemini-3.8-flash" in cfg["available_models"]

    res_missing = await provider.test_connection(cfg)
    assert res_missing["ok"] is False

    with pytest.raises(ProviderUnavailableError):
        await provider.chat(
            [{"role": "user", "content": "Hi, are you there? Tell me what you can do."}],
            "",
            cfg,
        )

    interactions_calls: List[Dict[str, Any]] = []

    def models_handler(api_key: str, kwargs: Dict[str, Any]):
        return [
            SimpleNamespace(name="models/gemini-3.1-pro-preview", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-2.5-pro", supported_actions=["generateContent"]),
        ]

    class _AsyncEventStream:
        def __init__(self, events: List[Any]):
            self._events = events

        def __aiter__(self):
            async def _gen():
                for ev in self._events:
                    yield ev

            return _gen()

    def interactions_handler(api_key: str, kwargs: Dict[str, Any]):
        model = kwargs["model"]
        return _AsyncEventStream(
            [
                SimpleNamespace(event_type="interaction.created"),
                SimpleNamespace(
                    event_type="step.delta",
                    delta=SimpleNamespace(type="text", text=f"[{model}] Yes, I am here. "),
                ),
                SimpleNamespace(
                    event_type="step.delta",
                    delta=SimpleNamespace(type="text", text="I can help with geospatial workflows."),
                ),
                SimpleNamespace(
                    event_type="interaction.completed",
                    interaction=SimpleNamespace(status="completed"),
                ),
            ]
        )

    monkeypatch.setattr(
        "backend.ai.providers.gemini._create_genai_client",
        _make_mock_genai_factory(
            interactions_calls,
            models_handler=models_handler,
            interactions_handler=interactions_handler,
        ),
    )

    cfg_valid = dict(cfg, _api_key="test-gemini-secret-key")
    conn = await provider.test_connection(cfg_valid)
    assert conn["ok"] is True
    assert conn["models"][0] == "gemini-3.1-pro-preview"
    assert "gemini-3.8-flash" in conn["models"]
    assert "gemini-2.5-pro" not in conn["models"]

    # Basic single-turn text response with default model (gemini-3.1-pro-preview)
    basic_reply = await provider.chat(
        [{"role": "user", "content": "Hi, are you there? Tell me what you can do."}],
        "",
        cfg_valid,
    )
    assert basic_reply == "[gemini-3.1-pro-preview] Yes, I am here. I can help with geospatial workflows."
    assert interactions_calls[-1]["model"] == "gemini-3.1-pro-preview"
    assert interactions_calls[-1]["input"] == "Hi, are you there? Tell me what you can do."
    assert interactions_calls[-1]["store"] is False
    assert interactions_calls[-1]["stream"] is True

    # Multi-turn conversation & alternative model selection (gemini-3.8-flash)
    deltas: List[str] = []
    async for chunk in provider.stream_chat(
        messages=[
            {"role": "user", "content": "Define NDVI"},
            {"role": "assistant", "content": "Normalized Difference Vegetation Index."},
            {"role": "user", "content": "Hi, are you there? Tell me what you can do."},
        ],
        model="gemini-3.8-flash",
        config=cfg_valid,
    ):
        deltas.append(chunk)

    assert "".join(deltas) == "[gemini-3.8-flash] Yes, I am here. I can help with geospatial workflows."
    multi_call = interactions_calls[-1]
    assert multi_call["model"] == "gemini-3.8-flash"
    assert multi_call["api_key"] == "test-gemini-secret-key"
    assert multi_call["generation_config"] == {"thinking_level": "low"}
    assert multi_call["input"] == [
        {"type": "user_input", "content": [{"type": "text", "text": "Define NDVI"}]},
        {"type": "model_output", "content": [{"type": "text", "text": "Normalized Difference Vegetation Index."}]},
        {"type": "user_input", "content": [{"type": "text", "text": "Hi, are you there? Tell me what you can do."}]},
    ]

    # Verify connection check detects unavailable configured default model when catalog is returned.
    conn_missing_model = await provider.test_connection(dict(cfg_valid, default_model="gemini-nonexistent"))
    assert conn_missing_model["ok"] is False
    assert "404" in conn_missing_model["message"]


@pytest.mark.asyncio
async def test_gemini_client_uses_v1beta_and_fail_fast_retry():
    from backend.ai.providers.gemini import _create_genai_client

    sdk_client = _create_genai_client("test-key", timeout_ms=15_000)
    assert sdk_client._api_client._http_options.api_version == "v1beta"
    assert sdk_client._api_client._http_options.retry_options.attempts == 1
    await sdk_client.aio.aclose()


@pytest.mark.asyncio
async def test_gemini_interactions_error_handling(monkeypatch):
    from google.genai import errors as genai_errors
    from backend.ai.providers.base import ProviderRequestError

    provider = GeminiProvider()
    cfg = dict(ai_config.get_provider_config("gemini"), _api_key="test-gemini-key")

    def make_sdk_err(code: int, message: str):
        err = genai_errors.ClientError(code, {"error": {"code": code, "message": message}}, None)
        return err

    mode = {"case": "auth_401"}

    def models_handler(api_key: str, kwargs: Dict[str, Any]):
        if mode["case"] == "conn_bad_key":
            raise make_sdk_err(400, "API key not valid. Please pass a valid API key.")
        return []

    def interactions_handler(api_key: str, kwargs: Dict[str, Any]):
        case = mode["case"]
        if case == "conn_bad_key":
            raise make_sdk_err(400, "API key not valid. Please pass a valid API key.")
        if case == "auth_401":
            raise make_sdk_err(401, "Invalid authentication credentials.")
        if case == "auth_400":
            raise make_sdk_err(400, "API key not valid. Please pass a valid API key.")
        if case == "not_found_404":
            raise make_sdk_err(404, "models/gemini-2.5-pro is no longer available to new users.")
        if case == "rate_limit_429":
            raise make_sdk_err(429, "Quota exceeded for requests per minute.")
        if case == "timeout":
            raise TimeoutError("Read timed out")
        if case == "service_500":
            raise genai_errors.ServerError(500, {"error": {"code": 500, "message": "Internal error"}}, None)
        if case == "service_503":
            raise genai_errors.ServerError(503, {"error": {"code": 503, "message": "Service unavailable"}}, None)
        raise AssertionError(f"Unexpected case {case}")

    monkeypatch.setattr(
        "backend.ai.providers.gemini._create_genai_client",
        _make_mock_genai_factory(
            [],
            models_handler=models_handler,
            interactions_handler=interactions_handler,
        ),
    )

    mode["case"] = "conn_bad_key"
    conn_bad = await provider.test_connection(cfg)
    assert conn_bad["ok"] is False
    assert "authentication rejected" in conn_bad["message"].lower()

    for auth_case in ("auth_401", "auth_400"):
        mode["case"] = auth_case
        with pytest.raises(ProviderAuthError):
            await provider.chat([{"role": "user", "content": "Hi, are you there? Tell me what you can do."}], "", cfg)

    mode["case"] = "not_found_404"
    with pytest.raises(ProviderRequestError, match="404"):
        await provider.chat(
            [{"role": "user", "content": "Hi, are you there? Tell me what you can do."}],
            "gemini-2.5-pro",
            cfg,
        )

    mode["case"] = "rate_limit_429"
    with pytest.raises(ProviderRequestError, match="429"):
        await provider.chat([{"role": "user", "content": "Hi, are you there? Tell me what you can do."}], "", cfg)

    mode["case"] = "timeout"
    with pytest.raises(ProviderUnavailableError, match="timed out"):
        await provider.chat([{"role": "user", "content": "Hi, are you there? Tell me what you can do."}], "", cfg)

    for server_case, code_str in (("service_500", "500"), ("service_503", "503")):
        mode["case"] = server_case
        with pytest.raises(ProviderUnavailableError, match=code_str):
            await provider.chat([{"role": "user", "content": "Hi, are you there? Tell me what you can do."}], "", cfg)


# ---------------------------------------------------------------------------
# 3. Individual Provider Test: Anthropic Claude
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claude_provider_unavailable_auth_and_streaming(monkeypatch):
    provider = ClaudeProvider()
    cfg = ai_config.get_provider_config("claude")

    res_missing = await provider.test_connection(cfg)
    assert res_missing["ok"] is False

    with pytest.raises(ProviderUnavailableError):
        await provider.chat([{"role": "user", "content": "Hello"}], "claude-3-7-sonnet-20250219", cfg)

    calls: List[Dict[str, Any]] = []

    def handler(method: str, url: str, kwargs: Dict[str, Any]):
        if method == "GET":
            return _FakeHTTPResponse(200, json_data={"data": [{"id": "claude-3-7-sonnet-20250219"}]})
        if kwargs["headers"].get("x-api-key") == "invalid-claude-key":
            return _FakeHTTPResponse(401, text="invalid x-api-key")
        return _FakeHTTPResponse(
            200,
            lines=[
                'event: content_block_delta',
                'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Sentinel-2 "}}',
                'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Band 8 is NIR."}}',
                'data: {"type":"message_stop"}',
            ],
        )

    monkeypatch.setattr(
        "backend.ai.providers.claude.httpx.AsyncClient",
        _make_mock_httpx_client(calls, handler),
    )

    cfg_valid = dict(cfg, _api_key="sk-ant-valid-9999")
    conn = await provider.test_connection(cfg_valid)
    assert conn["ok"] is True

    text = await provider.chat(
        messages=[{"role": "user", "content": "Which Sentinel-2 band is NIR?"}],
        model="claude-sonnet-4-manual-id",
        config=cfg_valid,
        system_instruction="Be concise.",
    )
    assert text == "Sentinel-2 Band 8 is NIR."
    post_call = [c for c in calls if c["method"] == "POST"][0]
    assert post_call["json"]["model"] == "claude-sonnet-4-manual-id"
    assert post_call["json"]["stream"] is True
    assert post_call["headers"]["x-api-key"] == "sk-ant-valid-9999"

    cfg_bad = dict(cfg, _api_key="invalid-claude-key")
    with pytest.raises(ProviderAuthError):
        await provider.chat([{"role": "user", "content": "hi"}], "claude-3-7-sonnet-20250219", cfg_bad)


# ---------------------------------------------------------------------------
# 4. Individual Provider Test: Local Ollama
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_discovery_docker_bridge_streaming_and_offline(monkeypatch):
    provider = OllamaProvider()
    calls: List[Dict[str, Any]] = []

    def offline_handler(method: str, url: str, kwargs: Dict[str, Any]):
        raise OSError("Connection refused")

    from backend.ai.providers.ollama import candidate_ollama_urls

    assert candidate_ollama_urls("http://ollama:11434") == [
        "http://ollama:11434",
        "http://host.docker.internal:11434",
        "http://localhost:11434",
    ]
    assert "http://ollama:11434" in candidate_ollama_urls("http://localhost:11434")

    monkeypatch.setattr(
        "backend.ai.providers.ollama.httpx.AsyncClient",
        _make_mock_httpx_client(calls, offline_handler),
    )

    cfg = ai_config.get_provider_config("ollama")
    offline_conn = await provider.test_connection(cfg)
    assert offline_conn["ok"] is False
    with pytest.raises(ProviderUnavailableError):
        await provider.chat([{"role": "user", "content": "Hi"}], "", cfg)

    calls.clear()

    def bridge_handler(method: str, url: str, kwargs: Dict[str, Any]):
        if "localhost" in url:
            raise OSError("Container localhost refused")
        if method == "GET" and url == "http://host.docker.internal:11434/api/tags":
            return _FakeHTTPResponse(
                200,
                json_data={"models": [{"name": "qwen2.5-coder:7b"}, {"name": "llama3.2:latest"}]},
            )
        if method == "POST" and url == "http://host.docker.internal:11434/api/chat":
            return _FakeHTTPResponse(
                200,
                lines=[
                    '{"message":{"role":"assistant","content":"QGIS "},"done":false}',
                    '{"message":{"role":"assistant","content":"uses GDAL."},"done":true}',
                ],
            )
        return _FakeHTTPResponse(404)

    monkeypatch.setattr(
        "backend.ai.providers.ollama.httpx.AsyncClient",
        _make_mock_httpx_client(calls, bridge_handler),
    )

    endpoint, discovered = await chat_service.refresh_ollama_models(timeout=1.0)
    assert endpoint == "http://host.docker.internal:11434"
    assert discovered == ["qwen2.5-coder:7b", "llama3.2:latest"]

    updated_cfg = ai_config.get_provider_config("ollama")
    assert updated_cfg["available_models"] == ["qwen2.5-coder:7b", "llama3.2:latest"]

    reply = await provider.chat([{"role": "user", "content": "What powers QGIS rasters?"}], "", updated_cfg)
    assert reply == "QGIS uses GDAL."


@pytest.mark.asyncio
async def test_ollama_host_bridge_not_overridden_by_env_and_404_fallback(monkeypatch):
    from backend.ai.providers.base import ProviderRequestError
    from backend.ai.providers.ollama import candidate_ollama_urls

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")

    # Explicit host.docker.internal base_url must stay primary ahead of OLLAMA_BASE_URL fallback.
    assert candidate_ollama_urls("http://host.docker.internal:11434") == [
        "http://host.docker.internal:11434",
        "http://ollama:11434",
        "http://localhost:11434",
    ]

    provider = OllamaProvider()
    calls: List[Dict[str, Any]] = []

    def split_models_handler(method: str, url: str, kwargs: Dict[str, Any]):
        if method == "GET" and url == "http://ollama:11434/api/tags":
            return _FakeHTTPResponse(200, json_data={"models": [{"name": "qwen2.5-coder:3b"}]})
        if method == "GET" and url == "http://host.docker.internal:11434/api/tags":
            return _FakeHTTPResponse(200, json_data={"models": [{"name": "qwen3-coder-next:q4_K_M"}]})
        if method == "POST" and url == "http://ollama:11434/api/chat":
            model_name = (kwargs.get("json") or {}).get("model")
            if model_name == "qwen2.5-coder:3b":
                return _FakeHTTPResponse(
                    200,
                    lines=['{"message":{"role":"assistant","content":"container ok"},"done":true}'],
                )
            return _FakeHTTPResponse(
                404,
                text=f'{{"error":"model \'{model_name}\' not found"}}',
            )
        if method == "POST" and url == "http://host.docker.internal:11434/api/chat":
            model_name = (kwargs.get("json") or {}).get("model")
            if model_name == "qwen3-coder-next:q4_K_M":
                return _FakeHTTPResponse(
                    200,
                    lines=['{"message":{"role":"assistant","content":"host ok"},"done":true}'],
                )
            return _FakeHTTPResponse(404, text=f'{{"error":"model \'{model_name}\' not found"}}')
        return _FakeHTTPResponse(404, text='{"error":"not found"}')

    monkeypatch.setattr(
        "backend.ai.providers.ollama.httpx.AsyncClient",
        _make_mock_httpx_client(calls, split_models_handler),
    )

    ai_config.update_provider("ollama", base_url="http://host.docker.internal:11434")
    endpoint, discovered = await chat_service.refresh_ollama_models(timeout=1.0)
    assert endpoint == "http://host.docker.internal:11434"
    assert discovered == ["qwen3-coder-next:q4_K_M"]

    cfg_host = ai_config.get_provider_config("ollama")
    reply_host = await provider.chat([{"role": "user", "content": "hi"}], "qwen3-coder-next:q4_K_M", cfg_host)
    assert reply_host == "host ok"
    assert [c["url"] for c in calls if c["method"] == "POST"] == ["http://host.docker.internal:11434/api/chat"]

    # When base_url starts at http://ollama:11434 and returns 404 for a host model, fallback succeeds cleanly.
    calls.clear()
    cfg_container = dict(cfg_host, base_url="http://ollama:11434")
    reply_fallback = await provider.chat([{"role": "user", "content": "hi"}], "qwen3-coder-next:q4_K_M", cfg_container)
    assert reply_fallback == "host ok"
    assert [c["url"] for c in calls if c["method"] == "POST"] == [
        "http://ollama:11434/api/chat",
        "http://host.docker.internal:11434/api/chat",
    ]

    # Truly missing model still surfaces HTTP 404 ProviderRequestError.
    with pytest.raises(ProviderRequestError, match="HTTP 404"):
        await provider.chat([{"role": "user", "content": "hi"}], "nonexistent:model", cfg_host)


# ---------------------------------------------------------------------------
# 5. Individual Provider Test: Google Antigravity SDK
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_antigravity_sdk_no_tools_streaming_and_cancellation(monkeypatch):
    provider = AntigravityProvider()
    cfg = ai_config.get_provider_config("antigravity")

    # Unauthenticated -> graceful unavailable error (no fake fallback)
    test_no_auth = await provider.test_connection(cfg)
    assert test_no_auth["ok"] is False
    with pytest.raises(ProviderUnavailableError):
        await provider.chat([{"role": "user", "content": "Hello"}], "gemini-3.8-flash", cfg)

    # Verify V1 LocalAgentConfig disables ALL BuiltinTools & subagents (Rule 8)
    cfg_auth = dict(cfg, _api_key="ag-test-key-123456")
    sdk_cfg = provider._build_config(cfg_auth, "gemini-3.8-flash", DEFAULT_SYSTEM_PROMPT)
    assert sdk_cfg.capabilities.enable_subagents is False
    assert set(sdk_cfg.capabilities.disabled_tools) == set(ag_types.BuiltinTools)
    assert sdk_cfg.api_key == "ag-test-key-123456"

    captured: Dict[str, Any] = {"cancelled": False, "prompts": [], "configs": []}

    class _FakeResponse:
        def __init__(self, chunks: List[str]):
            self._chunks = chunks

        async def cancel(self):
            captured["cancelled"] = True

        def __aiter__(self):
            async def _gen():
                for c in self._chunks:
                    await asyncio.sleep(0)
                    yield c

            return _gen()

    class _FakeAgent:
        def __init__(self, agent_cfg):
            captured["configs"].append(agent_cfg)
            self.is_started = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def chat(self, prompt: str):
            captured["prompts"].append(prompt)
            return _FakeResponse(["DEM ", "resolution ", "is 30m."])

    monkeypatch.setattr("backend.ai.providers.antigravity.Agent", _FakeAgent)

    conn_ok = await provider.test_connection(cfg_auth)
    assert conn_ok["ok"] is True

    chunks = []
    async for delta in provider.stream_chat(
        messages=[
            {"role": "user", "content": "Earlier I chose SRTM."},
            {"role": "assistant", "content": "Understood, SRTM DEM."},
            {"role": "user", "content": "What resolution?"},
        ],
        model="gemini-3.8-flash",
        config=cfg_auth,
    ):
        chunks.append(delta)

    assert "".join(chunks) == "DEM resolution is 30m."
    assert captured["prompts"][-1] == "What resolution?"
    assert "User: Earlier I chose SRTM." in captured["configs"][-1].system_instructions
    assert "Assistant: Understood, SRTM DEM." in captured["configs"][-1].system_instructions

    # Also test cancellation delegates to response.cancel()
    class _SlowAgent(_FakeAgent):
        async def chat(self, prompt: str):
            class _SlowResp(_FakeResponse):
                def __aiter__(self):
                    async def _gen():
                        yield "First "
                        await asyncio.sleep(5)
                        yield "Second"
                    return _gen()
            return _SlowResp([])

    monkeypatch.setattr("backend.ai.providers.antigravity.Agent", _SlowAgent)
    got = []
    first_received = asyncio.Event()

    async def _consume():
        async for tok in provider.stream_chat([{"role": "user", "content": "Go"}], "gemini-3.8-flash", cfg_auth):
            got.append(tok)
            first_received.set()

    task = asyncio.create_task(_consume())
    await first_received.wait()
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert got == ["First "]
    assert captured["cancelled"] is True


# ---------------------------------------------------------------------------
# 6. Conversation Persistence, Provider Switching & SSE Cancel Integration
# ---------------------------------------------------------------------------


def test_cross_provider_conversation_history_and_sse_streaming(client, monkeypatch):
    # Configure mock credentials via API
    assert client.post(
        "/api/ai/configure",
        json={"provider": "gemini", "api_key": "gem-secret-token", "default_model": "gemini-3.1-pro-preview"},
    ).status_code == 200
    assert client.post(
        "/api/ai/configure",
        json={"provider": "claude", "api_key": "ant-secret-token", "default_model": "claude-3-7-sonnet-20250219"},
    ).status_code == 200

    recorded_histories: List[Dict[str, Any]] = []

    async def fake_gemini_stream(self, messages, model, config, system_instruction=None, temperature=0.2):
        recorded_histories.append({"provider": "gemini", "model": model, "messages": list(messages)})
        yield "GeoTIFF stores gridded raster data."

    async def fake_claude_stream(self, messages, model, config, system_instruction=None, temperature=0.2):
        recorded_histories.append({"provider": "claude", "model": model, "messages": list(messages)})
        yield "COG adds internal tiling and overviews."

    monkeypatch.setattr(GeminiProvider, "stream_chat", fake_gemini_stream)
    monkeypatch.setattr(ClaudeProvider, "stream_chat", fake_claude_stream)

    # Create conversation on Gemini
    conv = client.post("/api/ai/conversations", json={"provider": "gemini", "model": "gemini-3.1-pro-preview"}).json()
    cid = conv["id"]

    # Turn 1 (SSE streaming on Gemini)
    with client.stream(
        "POST",
        "/api/ai/chat/stream",
        json={"conversation_id": cid, "prompt": "What is GeoTIFF?", "provider": "gemini", "model": "gemini-3.1-pro-preview"},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
        assert "event: meta" in body
        assert "event: delta" in body
        assert "event: done" in body
        assert "GeoTIFF stores gridded raster data." in body

    # Turn 2: Switch provider to Claude inside the SAME conversation
    turn2 = client.post(
        "/api/ai/chat",
        json={
            "conversation_id": cid,
            "prompt": "Compare it with COG.",
            "provider": "claude",
            "model": "claude-3-5-haiku-20241022",
        },
    )
    assert turn2.status_code == 200
    assert turn2.json()["provider"] == "claude"
    assert turn2.json()["model"] == "claude-3-5-haiku-20241022"
    assert turn2.json()["text"] == "COG adds internal tiling and overviews."

    # Verify Turn 2 received the full prior history from Gemini!
    assert len(recorded_histories) == 2
    assert recorded_histories[1]["provider"] == "claude"
    assert recorded_histories[1]["messages"] == [
        {"role": "user", "content": "What is GeoTIFF?"},
        {"role": "assistant", "content": "GeoTIFF stores gridded raster data."},
        {"role": "user", "content": "Compare it with COG."},
    ]

    # Verify persisted conversation record preserves message-level provider & auto-title
    detail = client.get(f"/api/ai/conversations/{cid}").json()
    assert detail["title"] == "What is GeoTIFF?"
    assert detail["provider"] == "claude"
    assert len(detail["messages"]) == 4
    assert detail["messages"][1]["provider"] == "gemini"
    assert detail["messages"][3]["provider"] == "claude"

    # Graceful SSE error when calling unconfigured Antigravity (no leaked orphan turns)
    with client.stream(
        "POST",
        "/api/ai/chat/stream",
        json={"conversation_id": cid, "prompt": "Should fail safely", "provider": "antigravity"},
    ) as err_resp:
        assert err_resp.status_code == 200
        err_body = "".join(err_resp.iter_text())
        assert "event: error" in err_body
        assert "provider_unavailable" in err_body

    detail_after_err = client.get(f"/api/ai/conversations/{cid}").json()
    assert len(detail_after_err["messages"]) == 4

    # Delete conversation cleanly
    del_res = client.delete(f"/api/ai/conversations/{cid}")
    assert del_res.status_code == 200
    assert client.get(f"/api/ai/conversations/{cid}").status_code == 404


@pytest.mark.asyncio
async def test_sse_stream_cancellation_persists_partial_response(monkeypatch):
    client_conv = chat_service.create_conversation()

    async def slow_stream(self, messages, model, config, system_instruction=None, temperature=0.2):
        yield "Partial answer "
        yield "before stop"
        await asyncio.sleep(10)
        yield "never reached"

    ai_config.update_provider("gemini", api_key="gem-stop-test")
    monkeypatch.setattr(GeminiProvider, "stream_chat", slow_stream)

    prepared = chat_service.prepare_execution(
        ChatRequest(conversation_id=client_conv.id, prompt="Explain SAR", provider="gemini")
    )
    gen = chat_service.stream_prepared_events(prepared)

    frames = []
    frames.append(await gen.__anext__())  # meta
    frames.append(await gen.__anext__())  # delta 1
    frames.append(await gen.__anext__())  # delta 2
    await gen.aclose()

    detail = chat_service.get_conversation(client_conv.id)
    assert len(detail.messages) == 2
    assert detail.messages[1].content == "Partial answer before stop\n\n_[Generation stopped]_"
    chat_service.delete_conversation(client_conv.id)


@pytest.mark.asyncio
async def test_ollama_pull_model_streaming_and_error(monkeypatch):
    from backend.ai.providers.base import ProviderRequestError

    provider = OllamaProvider()
    calls: List[Dict[str, Any]] = []

    def handler(method: str, url: str, kwargs: Dict[str, Any]):
        if method == "GET" and url.endswith("/api/tags"):
            return _FakeHTTPResponse(200, json_data={"models": []})
        if method == "POST" and url.endswith("/api/pull"):
            model_name = (kwargs.get("json") or {}).get("model")
            if model_name == "missing-bad-tag":
                return _FakeHTTPResponse(200, lines=['{"error":"pull model manifest: file does not exist"}'])
            return _FakeHTTPResponse(
                200,
                lines=[
                    '{"status":"pulling manifest"}',
                    '{"status":"downloading abc","digest":"sha256:abc","total":1000,"completed":500}',
                    '{"status":"success"}',
                ],
            )
        return _FakeHTTPResponse(404)

    monkeypatch.setattr(
        "backend.ai.providers.ollama.httpx.AsyncClient",
        _make_mock_httpx_client(calls, handler),
    )

    events = [ev async for ev in provider.pull_model("qwen2.5-coder:3b", "http://localhost:11434")]
    assert events[0]["status"] == "pulling manifest"
    assert events[1]["percent"] == 50.0
    assert events[2]["status"] == "success"

    with pytest.raises(ProviderRequestError):
        _ = [ev async for ev in provider.pull_model("missing-bad-tag", "http://localhost:11434")]


def test_api_ollama_pull_sse_updates_models_and_reachable(client, monkeypatch):
    bad = client.post("/api/ai/ollama/pull", json={"model": "   "})
    assert bad.status_code == 400

    pulled_models: List[str] = []
    calls: List[Dict[str, Any]] = []

    def handler(method: str, url: str, kwargs: Dict[str, Any]):
        if "localhost" in url and method == "GET" and url.endswith("/api/tags"):
            return _FakeHTTPResponse(200, json_data={"models": [{"name": m} for m in pulled_models]})
        if method == "POST" and url == "http://localhost:11434/api/pull":
            target = (kwargs.get("json") or {}).get("model")
            if target and target not in pulled_models:
                pulled_models.append(target)
            return _FakeHTTPResponse(
                200,
                lines=[
                    '{"status":"pulling manifest"}',
                    '{"status":"downloading layer","total":2000,"completed":1000}',
                    '{"status":"success"}',
                ],
            )
        return _FakeHTTPResponse(404)

    monkeypatch.setattr(
        "backend.ai.providers.ollama.httpx.AsyncClient",
        _make_mock_httpx_client(calls, handler),
    )

    # Online with 0 models -> reachable=True, models=[]
    before = client.get("/api/ai/models?provider=ollama")
    assert before.status_code == 200
    assert before.json()["reachable"] is True
    assert before.json()["models"] == []

    # Pull qwen2.5-coder:3b via SSE endpoint
    with client.stream("POST", "/api/ai/ollama/pull", json={"model": "qwen2.5-coder:3b"}) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
        assert "event: progress" in body
        assert '"percent": 50.0' in body
        assert "event: done" in body
        assert "qwen2.5-coder:3b" in body

    after = client.get("/api/ai/models?provider=ollama").json()
    assert after["reachable"] is True
    assert after["models"] == ["qwen2.5-coder:3b"]
    assert after["default_model"] == "qwen2.5-coder:3b"

    # Pull a second model and verify switching/changing model persists cleanly
    with client.stream("POST", "/api/ai/ollama/pull", json={"model": "llama3.2:latest"}) as resp2:
        assert resp2.status_code == 200
        assert "event: done" in "".join(resp2.iter_text())

    switched = client.post(
        "/api/ai/configure",
        json={"provider": "ollama", "default_model": "qwen2.5-coder:3b", "set_active": False},
    )
    assert switched.status_code == 200
    assert switched.json()["ollama"]["default_model"] == "qwen2.5-coder:3b"
    assert switched.json()["ollama"]["available_models"] == ["qwen2.5-coder:3b", "llama3.2:latest"]
