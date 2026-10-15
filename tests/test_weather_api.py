import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_live_weather_endpoint():
    response = client.get("/api/weather/live?lat=34.15&lon=77.5")
    assert response.status_code == 200
    data = response.json()
    assert "latitude" in data
    assert "longitude" in data
    assert "temperature_c" in data
    assert "cloud_cover_percent" in data
    assert "optical_viability" in data
    assert data["optical_viability"] in ["OPTIMAL", "MODERATE", "OVERCAST"]
    assert "recommendation" in data
    assert len(data["recommendation"]) > 5


def test_get_radar_frames_endpoint():
    response = client.get("/api/weather/radar-frames")
    assert response.status_code == 200
    data = response.json()
    assert "host" in data
    assert "frames" in data
    assert isinstance(data["frames"], list)


def test_get_nasa_gibs_info_endpoint():
    response = client.get("/api/weather/nasa-gibs")
    assert response.status_code == 200
    data = response.json()
    assert "valid_date" in data
    assert "cloud_fraction_url_template" in data
    assert "true_color_url_template" in data
    assert "temperature_surface_url_template" in data
    assert "temperature_air_url_template" in data
    assert "{z}" in data["cloud_fraction_url_template"]
    assert "{z}" in data["true_color_url_template"]
    assert "{z}" in data["temperature_surface_url_template"]
    assert "{z}" in data["temperature_air_url_template"]
