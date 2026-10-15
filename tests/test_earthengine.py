import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.core.earthengine.catalog import ee_catalog, CURATED_EE_DATASETS
from backend.core.earthengine.auth import ee_auth_manager

client = TestClient(app)


def test_ee_status_endpoint():
    response = client.get("/api/earthengine/status")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "is_authenticated" in data
    assert "credentials_exist" in data
    assert "auth_page_url" in data
    assert "https://code.earthengine.google.com/client-auth" in data["auth_page_url"]


def test_ee_catalog_datasets_endpoint():
    response = client.get("/api/earthengine/datasets")
    assert response.status_code == 200
    datasets = response.json()
    assert len(datasets) >= 10
    
    # Check that primary satellite datasets exist
    ids = [d["id"] for d in datasets]
    assert "COPERNICUS/S2_SR_HARMONIZED" in ids
    assert "LANDSAT/LC09/C02/T1_L2" in ids
    assert "COPERNICUS/S1_GRD" in ids
    assert "GOOGLE/DYNAMICWORLD/V1" in ids
    assert "USGS/SRTMGL1_003" in ids


def test_ee_catalog_category_filtering():
    # Filter optical
    response = client.get("/api/earthengine/datasets?category=optical")
    assert response.status_code == 200
    data = response.json()
    assert all(d["category"] == "optical" for d in data)
    assert any("S2" in d["id"] for d in data)

    # Filter radar
    response = client.get("/api/earthengine/datasets?category=radar")
    assert response.status_code == 200
    data = response.json()
    assert all(d["category"] == "radar" for d in data)
    assert any("S1_GRD" in d["id"] for d in data)

    # Filter elevation
    response = client.get("/api/earthengine/datasets?category=elevation")
    assert response.status_code == 200
    data = response.json()
    assert all(d["category"] == "elevation" for d in data)


def test_ee_catalog_search_query():
    response = client.get("/api/earthengine/datasets?query=dynamic")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert "DYNAMICWORLD" in data[0]["id"]


def test_ee_generate_auth_url():
    response = client.post("/api/earthengine/auth/url")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "auth_url" in data
    assert "code.earthengine.google.com/client-auth" in data["auth_url"]


def test_ee_auth_exchange_empty_code():
    response = client.post("/api/earthengine/auth/exchange", json={"auth_code": "   "})
    assert response.status_code == 400


def test_ee_auth_set_project_empty():
    response = client.post("/api/earthengine/auth/project", json={"project_id": "   "})
    assert response.status_code == 400


def test_ee_service_account_invalid_json():
    response = client.post("/api/earthengine/auth/service-account", json={"service_account_json": {}})
    assert response.status_code == 400
    assert "client_email" in response.json()["detail"]


def test_ee_catalog_direct_methods():
    ds = ee_catalog.get_dataset("COPERNICUS/S2_SR_HARMONIZED")
    assert ds is not None
    assert ds.name.startswith("Sentinel-2")
    assert "true_color" in ds.vis_presets
    assert "ndvi" in ds.vis_presets

    missing = ee_catalog.get_dataset("NON_EXISTENT_DATASET_12345")
    assert missing is None
