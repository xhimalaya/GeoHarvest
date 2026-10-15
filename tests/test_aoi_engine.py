import json
from pathlib import Path
from backend.core.aoi.engine import AOIEngine
from backend.app.dependencies.config import settings


def test_validate_ladakh_sample():
    sample_file = settings.base_dir / "resources" / "samples" / "ladakh.geojson"
    assert sample_file.exists()
    with open(sample_file, "r") as f:
        data = json.load(f)

    result = AOIEngine.validate_and_analyze(geojson_data=data)
    assert result["valid"] is True
    assert result["crs"] == "EPSG:4326"
    assert result["geometry_type"] in ["Polygon", "MultiPolygon"]
    assert result["area_km2"] > 10000.0  # Ladakh area is > 10,000 sq km
    assert len(result["bbox"]) == 4
    # Check bbox roughly aligns with Ladakh coordinates
    minx, miny, maxx, maxy = result["bbox"]
    assert 75.0 <= minx <= 77.0
    assert 32.0 <= miny <= 34.0
    assert 78.0 <= maxx <= 80.0
    assert 34.0 <= maxy <= 36.0


def test_validate_bbox():
    bbox = [77.0, 34.0, 78.0, 35.0]
    result = AOIEngine.validate_and_analyze(bbox=bbox)
    assert result["valid"] is True
    assert result["geometry_type"] == "Polygon"
    assert result["area_km2"] > 0.0
    assert result["bbox"] == bbox


def test_validate_invalid_data():
    result = AOIEngine.validate_and_analyze(geojson_data={"invalid": 123})
    assert result["valid"] is False
    assert result["error"] is not None
