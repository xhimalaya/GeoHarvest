from backend.core.crs.engine import CRSEngine


def test_utm_zone_calculation():
    # Greenwich 0 deg lon -> UTM zone 31
    zone, hem, epsg = CRSEngine.calculate_utm_zone(0.0, 51.5)
    assert zone == 31
    assert hem == "N"
    assert epsg == 32631

    # Sydney, Australia -> UTM zone 56 South
    zone, hem, epsg = CRSEngine.calculate_utm_zone(151.2, -33.8)
    assert zone == 56
    assert hem == "S"
    assert epsg == 32756


def test_ladakh_multi_zone_detection():
    # Ladakh test bounding box spans from 76.1 deg lon (Zone 43N) to 79.2 deg lon (Zone 44N)
    ladakh_bbox = [76.10, 32.80, 79.20, 35.20]
    rec = CRSEngine.recommend(ladakh_bbox)

    assert rec["crosses_multiple_zones"] is True
    assert rec["warning"] is not None
    assert "43N" in rec["warning"]
    assert "44N" in rec["warning"]
    # Centroid ~77.65 is in zone 43N (72 to 78 deg E)
    assert rec["recommended_crs"] == "EPSG:32643"
    assert len(rec["candidates"]) >= 3


def test_single_zone_detection():
    # Small area strictly within Zone 43N (73.0 to 74.0 deg lon)
    bbox = [73.0, 34.0, 74.0, 35.0]
    rec = CRSEngine.recommend(bbox)

    assert rec["crosses_multiple_zones"] is False
    assert rec["warning"] is None
    assert rec["recommended_crs"] == "EPSG:32643"
