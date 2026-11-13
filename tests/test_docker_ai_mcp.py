import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.core.ai.gateway import llm_gateway
from backend.core.ai.connectors.gemini import gemini_connector
from backend.core.ai.connectors.claude import claude_connector
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


def test_gemini_connector_initialization():
    assert hasattr(gemini_connector, "is_configured")
    assert hasattr(gemini_connector, "list_available_models")
    models = gemini_connector.list_available_models()
    assert len(models) >= 2
    assert any("gemini" in m for m in models)


def test_claude_connector_initialization():
    assert hasattr(claude_connector, "is_configured")
    assert hasattr(claude_connector, "list_available_models")
    models = claude_connector.list_available_models()
    assert len(models) >= 2
    assert any("claude" in m for m in models)


def test_llm_gateway_status():
    status = llm_gateway.get_status()
    assert "gemini" in status
    assert "claude" in status
    assert "qdrant" in status
    assert "active_provider" in status


def test_mcp_server_registered_tools():
    assert mcp.name == "geoharvest"
    assert mcp.version == "1.0.0"

    # Test tools execution directly
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


def test_api_ai_status(client):
    r = client.get("/api/ai/status")
    assert r.status_code == 200
    data = r.json()
    assert "gemini" in data
    assert "claude" in data
    assert "qdrant" in data


def test_api_ai_models(client):
    r = client.get("/api/ai/models")
    assert r.status_code == 200
    data = r.json()
    assert "gemini" in data
    assert "claude" in data


def test_api_ai_chat(client):
    r = client.post("/api/ai/chat", json={"prompt": "Extract building candidates using K-Means"})
    assert r.status_code == 200
    data = r.json()
    assert "text" in data
    assert "provider" in data


def test_api_mcp_info(client):
    r = client.get("/api/ai/mcp/info")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "geoharvest"
    assert data["tools_count"] == 9
    assert "geo_resolve_aoi" in data["tools"]
    assert "geo_execute_kmeans" in data["tools"]
    assert "geo_polygonize_raster" in data["tools"]


def test_api_vector_status(client):
    r = client.get("/api/ai/vector/status")
    assert r.status_code == 200
    data = r.json()
    assert "host" in data
    assert "port" in data
