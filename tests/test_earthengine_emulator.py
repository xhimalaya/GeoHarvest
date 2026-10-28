import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.core.earthengine.emulator import ee_emulator

client = TestClient(app)


def test_emulator_local_mode_basic_execution():
    code = """
print("Running GeoHarvest Local Script...")
x = 10 + 25
data["calculated_val"] = x
print(f"Calculated: {x}")
"""
    result = ee_emulator.execute(code=code, mode="local")
    assert result["success"] is True
    assert "Running GeoHarvest Local Script..." in result["logs"]
    assert "Calculated: 35" in result["logs"]
    assert result["data"]["calculated_val"] == 35
    assert result["execution_time_ms"] >= 0


def test_emulator_local_mode_with_aoi():
    sample_aoi = {
        "type": "Polygon",
        "coordinates": [
            [[77.5, 34.1], [77.6, 34.1], [77.6, 34.2], [77.5, 34.2], [77.5, 34.1]]
        ]
    }
    code = """
print("AOI received:", aoi["type"])
data["coord_count"] = len(aoi["coordinates"][0])
Map.addLayer(aoi, name="Study Boundary")
Map.setCenter(77.55, 34.15, 12)
"""
    result = ee_emulator.execute(code=code, mode="local", aoi_geojson=sample_aoi)
    assert result["success"] is True
    assert result["data"]["coord_count"] == 5
    assert len(result["layers"]) == 1
    assert result["layers"][0]["name"] == "Study Boundary"
    assert result["layers"][0]["layer_type"] == "geojson"
    assert result["center"] == [77.55, 34.15]
    assert result["zoom"] == 12


def test_emulator_error_traceback_capture():
    code = """
print("Step 1: start")
y = 100 / 0
print("Step 2: unreachable")
"""
    result = ee_emulator.execute(code=code, mode="local")
    assert result["success"] is False
    assert result["error"] is not None
    assert "division by zero" in result["error"].lower()
    assert "ZeroDivisionError" in result["logs"]


def test_api_emulator_run_endpoint():
    payload = {
        "code": "print('API Test'); data['status'] = 'ok'",
        "mode": "local",
        "aoi": None
    }
    response = client.post("/api/earthengine/emulator/run", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["status"] == "ok"
    assert "API Test" in res_data["logs"]


def test_api_emulator_snippets():
    response = client.get("/api/earthengine/emulator/snippets")
    assert response.status_code == 200
    snippets = response.json()
    assert len(snippets) >= 4
    ids = [s["id"] for s in snippets]
    assert "s2_ndvi" in ids
    assert "local_rasterio_ndvi" in ids


def test_api_emulator_template():
    response = client.get("/api/earthengine/emulator/template?dataset_id=COPERNICUS/S2_SR_HARMONIZED")
    assert response.status_code == 200
    data = response.json()
    assert "COPERNICUS/S2_SR_HARMONIZED" in data["code"]
    assert "Map.addLayer" in data["code"]


def test_api_emulator_local_files():
    response = client.get("/api/earthengine/emulator/local-files")
    assert response.status_code == 200
    files = response.json()
    assert isinstance(files, list)


def test_jupyter_session_variable_persistence_and_restart():
    session_id = "test-notebook-session-1"

    # Cell 1: define a variable and compute
    res1 = client.post("/api/earthengine/emulator/run", json={
        "code": "ndvi_threshold = 0.45\nbase_factor = 100",
        "mode": "local",
        "session_id": session_id,
        "cell_id": "cell-1"
    })
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["success"] is True
    assert d1["cell_id"] == "cell-1"

    # Cell 2: use the variable from Cell 1
    res2 = client.post("/api/earthengine/emulator/run", json={
        "code": "result_calc = ndvi_threshold * base_factor\nprint(f'Computed result: {result_calc}')\ndata['computed'] = result_calc",
        "mode": "local",
        "session_id": session_id,
        "cell_id": "cell-2"
    })
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["success"] is True
    assert "Computed result: 45.0" in d2["logs"]
    assert d2["data"]["computed"] == 45.0

    # Restart session
    restart_res = client.post("/api/earthengine/emulator/restart", json={"session_id": session_id})
    assert restart_res.status_code == 200
    assert restart_res.json()["status"] == "ok"

    # Cell 3 after restart: accessing ndvi_threshold should raise NameError
    res3 = client.post("/api/earthengine/emulator/run", json={
        "code": "print(ndvi_threshold)",
        "mode": "local",
        "session_id": session_id,
        "cell_id": "cell-3"
    })
    assert res3.status_code == 200
    d3 = res3.json()
    assert d3["success"] is False
    assert "NameError" in d3["logs"]

