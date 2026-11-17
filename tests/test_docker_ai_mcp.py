import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.ai.config import V1_PROVIDER_IDS, ai_config
from backend.ai.services.chat_service import chat_service
from backend.core.vector.qdrant_service import qdrant_service
from backend.mcp.server import mcp, geo_resolve_aoi, geo_list_algorithms


@pytest.fixture
def client():
    return TestClient(app)


def test_qdrant_service_initialization():
    status = qdrant_service.get_status()
    assert "host" in status
    assert "port" in status
    assert "available" in status
    assert "collections" in status


def test_mcp_server_registered_tools():
    assert mcp.name == "geoharvest"
    assert mcp.version == "1.0.0"

    ladakh_res = geo_resolve_aoi("Ladakh")
    assert ladakh_res["resolved"] is True
    assert ladakh_res["crs"] == "EPSG:4326"
    assert len(ladakh_res["bbox"]) == 4

    diskit_res = geo_resolve_aoi("Diskit")
    assert diskit_res["resolved"] is True
    assert diskit_res["bbox"][0] < diskit_res["bbox"][2]

    algos = geo_list_algorithms()
    assert len(algos) >= 7
    algo_ids = [a["id"] for a in algos]
    assert "ml.kmeans" in algo_ids
    assert "raster.polygonize" in algo_ids


def test_api_ai_v1_status_and_strict_four_providers(client):
    r = client.get("/api/ai/status?refresh=false")
    assert r.status_code == 200
    data = r.json()

    assert set(V1_PROVIDER_IDS) == {"gemini", "claude", "ollama", "antigravity"}
    for pid in V1_PROVIDER_IDS:
        assert pid in data
    for legacy in ("chatgpt", "deepseek", "clawai", "custom", "qdrant"):
        assert legacy not in data
    assert len(data["providers"]) == 4


def test_api_ai_v1_models_and_legacy_rejection(client):
    r = client.get("/api/ai/models")
    assert r.status_code == 200
    models = r.json()["models"]
    assert set(models.keys()) == {"gemini", "claude", "ollama", "antigravity"}
    assert any("gemini" in m for m in models["gemini"])
    assert any("claude" in m for m in models["claude"])

    bad = client.post("/api/ai/configure", json={"provider": "chatgpt", "api_key": "sk-test"})
    assert bad.status_code == 400

    bad_chat = client.post("/api/ai/chat", json={"prompt": "hi", "provider": "deepseek"})
    assert bad_chat.status_code == 400


def test_api_ai_v1_conversation_lifecycle(client):
    created = client.post("/api/ai/conversations", json={"title": "Test Thread", "provider": "gemini"})
    assert created.status_code == 200
    cid = created.json()["id"]

    listed = client.get("/api/ai/conversations")
    assert listed.status_code == 200
    assert any(c["id"] == cid for c in listed.json())

    patched = client.patch(f"/api/ai/conversations/{cid}", json={"provider": "claude", "title": "Renamed"})
    assert patched.status_code == 200
    assert patched.json()["provider"] == "claude"
    assert patched.json()["title"] == "Renamed"

    deleted = client.delete(f"/api/ai/conversations/{cid}")
    assert deleted.status_code == 200


def test_api_ai_v1_graceful_unconfigured_provider(client, tmp_path, monkeypatch):
    cfg_file = tmp_path / "isolated.json"
    monkeypatch.setattr(ai_config, "_config_path", cfg_file)
    monkeypatch.setattr(ai_config, "_configs", {})
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTIGRAVITY_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from backend.app.dependencies.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    assert chat_service is not None
    res = client.post("/api/ai/chat", json={"prompt": "Hello", "provider": "gemini"})
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()
