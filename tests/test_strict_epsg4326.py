"""
Comprehensive verification that EVERY data downloading and saving pathway in GeoHarvest
strictly writes outputs in EPSG:4326 (WGS 84 Geographic).
"""

from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from pyproj import Transformer
from rasterio.transform import from_origin

from backend.app.dependencies.config import settings
from backend.app.main import app
from backend.core.crs.engine import STRICT_OUTPUT_CRS, enforce_strict_epsg4326
from backend.core.processing.raster_ops import RasterOps


def _write_utm_raster(
    path: Path,
    *,
    epsg: int = 32643,
    width: int = 32,
    height: int = 32,
    res: float = 30.0,
    bands: int = 1,
    origin_x: float = 730000.0,
    origin_y: float = 3785000.0,
    fill_base: int = 500,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(origin_x, origin_y, res, res)
    y, x = np.mgrid[0:height, 0:width]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=bands,
        dtype="float32",
        crs=f"EPSG:{epsg}",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        for idx in range(1, bands + 1):
            arr = (fill_base * idx + x * 10 + y * 5).astype(np.float32)
            dst.write(arr, idx)
    return path


def _assert_tif_is_epsg4326(path: Path) -> None:
    assert path.exists(), f"Expected saved raster does not exist: {path}"
    with rasterio.open(path) as src:
        assert src.crs is not None, f"Saved raster has no CRS: {path}"
        assert src.crs.to_string() == "EPSG:4326", f"Expected EPSG:4326, got {src.crs.to_string()} for {path}"
        assert src.width > 0 and src.height > 0


def test_enforce_strict_epsg4326_helper():
    assert STRICT_OUTPUT_CRS == "EPSG:4326"
    assert enforce_strict_epsg4326(None) == "EPSG:4326"
    assert enforce_strict_epsg4326("") == "EPSG:4326"
    assert enforce_strict_epsg4326("native") == "EPSG:4326"
    assert enforce_strict_epsg4326("auto_utm") == "EPSG:4326"
    assert enforce_strict_epsg4326("EPSG:3857") == "EPSG:4326"
    assert enforce_strict_epsg4326("EPSG:32643") == "EPSG:4326"
    with pytest.raises(ValueError):
        enforce_strict_epsg4326("INVALID_CRS_XYZ_99999", reject_invalid=True)


def test_wms_export_strictly_saves_epsg4326(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "downloads_dir", tmp_path / "downloads")
    client = TestClient(app)

    # Even if pasted URL & payload request EPSG:3857 or EPSG:32643, output must be EPSG:4326
    res = client.post(
        "/api/wms/export",
        json={
            "url": "https://example.invalid/wms?SERVICE=WMS&REQUEST=GetMap&SRS=EPSG:3857&LAYERS=test:layer",
            "layers": "test:layer",
            "version": "1.1.1",
            "crs": "EPSG:3857",
            "bbox": [77.2, 34.0, 77.6, 34.3],
            "width": 256,
            "height": 256,
            "output_filename": "wms_strict_test.tif",
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["crs"] == "EPSG:4326"
    assert "SRS=EPSG%3A4326" in payload["getmap_url"] or "SRS=EPSG:4326" in payload["getmap_url"]
    _assert_tif_is_epsg4326(Path(payload["output_path"]))


def test_earthengine_export_strictly_saves_epsg4326(tmp_path, monkeypatch):
    from backend.core.earthengine.auth import ee_auth_manager

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(ee_auth_manager, "get_status", lambda: {"initialized": False})
    client = TestClient(app)

    res = client.post(
        "/api/earthengine/export",
        json={
            "dataset_id": "COPERNICUS/S2_SR_HARMONIZED",
            "bbox": [77.1, 33.9, 77.5, 34.2],
            "vis_mode": "ndvi",
            "scale": 30.0,
            "crs": "EPSG:32643",
            "destination_dir": str(tmp_path / "gee_out"),
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["crs"] == "EPSG:4326"
    _assert_tif_is_epsg4326(Path(payload["local_filepath"]))

    # Malformed CRS still rejected with 400
    bad = client.post(
        "/api/earthengine/export",
        json={
            "dataset_id": "COPERNICUS/S2_SR_HARMONIZED",
            "bbox": [77.1, 33.9, 77.5, 34.2],
            "crs": "NOT_A_VALID_CRS_888",
        },
    )
    assert bad.status_code == 400


def test_processing_toolbox_and_raster_ops_strictly_save_epsg4326(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "downloads_dir", tmp_path / "downloads")
    (tmp_path / "processed").mkdir(parents=True, exist_ok=True)

    utm_b1 = _write_utm_raster(tmp_path / "inputs" / "b1_utm43.tif", epsg=32643, fill_base=400)
    utm_b2 = _write_utm_raster(tmp_path / "inputs" / "b2_utm43.tif", epsg=32643, fill_base=900)
    utm_tile2 = _write_utm_raster(
        tmp_path / "inputs" / "tile2_utm43.tif",
        epsg=32643,
        origin_x=730900.0,
        origin_y=3785000.0,
        fill_base=650,
    )
    utm_multiband = _write_utm_raster(tmp_path / "inputs" / "mb_utm43.tif", epsg=32643, bands=3, fill_base=300)

    # Derive overlapping WGS84 AOI polygon from UTM raster bounds
    with rasterio.open(utm_b1) as src:
        trans = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
        min_lon, min_lat = trans.transform(src.bounds.left + 90, src.bounds.bottom + 90)
        max_lon, max_lat = trans.transform(src.bounds.right - 90, src.bounds.top - 90)
    aoi_geom = {
        "type": "Polygon",
        "coordinates": [[[min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat]]],
    }

    client = TestClient(app)

    # 1. Direct Clip on UTM raster -> EPSG:4326
    clip_res = client.post(
        "/api/processing/clip",
        json={
            "input_path": str(utm_b1),
            "aoi_geometry": aoi_geom,
            "output_filename": "strict_clip.tif",
            "to_cog": True,
        },
    )
    assert clip_res.status_code == 200, clip_res.text
    assert clip_res.json()["crs"] == "EPSG:4326"
    _assert_tif_is_epsg4326(Path(clip_res.json()["output_path"]))

    # 2. Mosaic & Clip requesting auto_utm / EPSG:3857 -> strictly EPSG:4326
    mos_res = client.post(
        "/api/processing/mosaic-clip",
        json={
            "input_file_paths": [str(utm_b1), str(utm_tile2)],
            "aoi_geometry": aoi_geom,
            "target_crs": "auto_utm",
            "output_path": str(tmp_path / "processed" / "strict_mosaic.tif"),
            "to_cog": True,
        },
    )
    assert mos_res.status_code == 200, mos_res.text
    assert mos_res.json()["crs"] == "EPSG:4326"
    _assert_tif_is_epsg4326(Path(mos_res.json()["output_path"]))

    # 3. Band Stack requesting native -> strictly EPSG:4326
    stack_res = client.post(
        "/api/processing/stack-bands",
        json={
            "input_file_paths": [str(utm_b1), str(utm_b2)],
            "target_crs": "native",
            "output_filename": "strict_stack.tif",
            "to_cog": True,
        },
    )
    assert stack_res.status_code == 200, stack_res.text
    assert stack_res.json()["crs"] == "EPSG:4326"
    _assert_tif_is_epsg4326(Path(stack_res.json()["output_path"]))

    # 4. Spectral Index on UTM inputs -> strictly EPSG:4326
    idx_res = client.post(
        "/api/processing/spectral-index",
        json={
            "index_type": "ndvi",
            "band1_path": str(utm_b2),
            "band2_path": str(utm_b1),
            "output_filename": "strict_ndvi.tif",
            "to_cog": True,
        },
    )
    assert idx_res.status_code == 200, idx_res.text
    _assert_tif_is_epsg4326(Path(idx_res.json()["output_path"]))

    # 5. Terrain Analysis on UTM DEM -> strictly EPSG:4326
    terr_res = client.post(
        "/api/processing/terrain",
        json={
            "dem_path": str(utm_b1),
            "operation": "slope",
            "output_filename": "strict_slope.tif",
            "to_cog": True,
        },
    )
    assert terr_res.status_code == 200, terr_res.text
    _assert_tif_is_epsg4326(Path(terr_res.json()["output_path"]))

    # 6. Reproject-Resample API requesting EPSG:32643 -> strictly EPSG:4326
    rep_res = client.post(
        "/api/processing/reproject-resample",
        json={
            "input_path": str(utm_b1),
            "target_crs": "EPSG:32643",
            "output_filename": "strict_reproj.tif",
            "to_cog": True,
        },
    )
    assert rep_res.status_code == 200, rep_res.text
    assert rep_res.json()["crs"] == "EPSG:4326"
    _assert_tif_is_epsg4326(Path(rep_res.json()["output_path"]))

    # 7. Upload Custom UTM Raster -> saved strictly as EPSG:4326
    with open(utm_b1, "rb") as fh:
        up_res = client.post(
            "/api/processing/upload-raster",
            files={"file": ("uploaded_utm.tif", fh, "image/tiff")},
        )
    assert up_res.status_code == 200, up_res.text
    assert up_res.json()["raster"]["crs"] == "EPSG:4326"
    _assert_tif_is_epsg4326(Path(up_res.json()["raster"]["absolute_path"]))

    # 8. K-Means, Change Detection, and Polygonize on UTM inputs -> strictly EPSG:4326
    km = RasterOps.kmeans_clustering(str(utm_multiband), str(tmp_path / "kmeans_out.tif"), n_clusters=3, to_cog=True)
    _assert_tif_is_epsg4326(Path(km["output_path"]))

    cd = RasterOps.change_detection(str(utm_b1), str(utm_b2), str(tmp_path / "change_out.tif"), to_cog=True)
    _assert_tif_is_epsg4326(Path(cd["output_path"]))

    # Write integer class raster in UTM and verify polygonize writes EPSG:4326 lon/lat coordinates
    cls_tif = tmp_path / "inputs" / "classes_utm43.tif"
    with rasterio.open(
        cls_tif,
        "w",
        driver="GTiff",
        height=16,
        width=16,
        count=1,
        dtype="uint8",
        crs="EPSG:32643",
        transform=from_origin(730000.0, 3785000.0, 30.0, 30.0),
        nodata=255,
    ) as dst:
        dst.write(np.ones((16, 16), dtype=np.uint8), 1)
    poly_res = RasterOps.polygonize_raster(str(cls_tif), str(tmp_path / "poly.geojson"), min_area_m2=1.0)
    assert poly_res["feature_count"] >= 1
    first_coords = poly_res["geojson"]["features"][0]["geometry"]["coordinates"][0][0]
    assert -180.0 <= first_coords[0] <= 180.0 and -90.0 <= first_coords[1] <= 90.0


def test_aoi_save_normalizes_legacy_projected_crs_to_epsg4326(tmp_path, monkeypatch):
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "aois_dir", aoi_dir)

    # Create a polygon in Web Mercator (EPSG:3857) with legacy GeoJSON CRS header
    to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    p1 = list(to_3857.transform(77.4, 34.0))
    p2 = list(to_3857.transform(77.6, 34.0))
    p3 = list(to_3857.transform(77.6, 34.2))
    p4 = list(to_3857.transform(77.4, 34.2))

    projected_fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[p1, p2, p3, p4, p1]]},
                "properties": {"name": "Projected AOI", "crs": "EPSG:3857"},
            }
        ],
    }

    client = TestClient(app)
    res = client.post("/api/aoi/save", json={"geojson": projected_fc, "name": "Projected AOI"})
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["crs"] == "EPSG:4326"
    saved_file = aoi_dir / payload["file_name"]
    assert saved_file.exists()
    saved_doc = json.loads(saved_file.read_text(encoding="utf-8"))
    assert "crs" not in saved_doc  # RFC 7946 EPSG:4326 GeoJSON
    assert saved_doc["features"][0]["properties"]["crs"] == "EPSG:4326"
    ring = saved_doc["features"][0]["geometry"]["coordinates"][0]
    assert all(77.0 <= pt[0] <= 78.0 and 33.5 <= pt[1] <= 34.5 for pt in ring)
