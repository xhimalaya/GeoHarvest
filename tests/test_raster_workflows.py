"""Resource-isolated analysis, Atlas rendering and numerical API acceptance tests."""
from datetime import datetime
import io
import math
from statistics import median
from time import perf_counter, sleep
from uuid import uuid4

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.warp import transform
from shapely.geometry import box, mapping, shape

from backend.app.dependencies.config import settings
from backend.app.main import app
from backend.app.models.models import Asset, Dataset, JobStatus
from backend.core.processing.workflows import jobs as workflow_jobs
from backend.core.processing.workflows.engine import WEB_LIMIT
from backend.core.processing.workflows.operators import OPERATORS, Operator, Parameters, register_operator, same_spec
from backend.core.processing.workflows.plan import Workflow, compile_workflow

API = "/api/processing/workflows"


@pytest.fixture
def atlas(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setattr(settings, "downloads_dir", downloads)
    with TestClient(app) as client:
        yield client, downloads


def _asset(db, file, date=None, collection=None, footprint=None):
    key = uuid4().hex
    dataset = Dataset(id=key, collection=collection or key, dataset_id=key, acquisition_date=date,
                      geometry=footprint, bbox=list(shape(footprint).bounds) if footprint else None)
    asset = Asset(id=key + "_data", dataset=dataset, asset_name="data", url=str(file), local_path=str(file),
                  asset_type="local_raw", status="downloaded")
    db.add_all([dataset, asset])
    db.commit()
    return asset.id


def _raster(path, data, crs, affine, mask=None):
    if data.ndim == 2:
        data = data[None, ...]
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(path, "w", driver="GTiff", width=data.shape[-1], height=data.shape[-2],
                           count=len(data), crs=crs, transform=affine, dtype=data.dtype, nodata=-9999) as target:
            target.write(data)
            if mask is not None:
                target.write_mask(mask.astype(np.uint8) * 255)
    return path


def _math(expression="a", **inputs):
    return {"id": "calc", "operator": "band_math", "inputs": inputs, "parameters": {"expression": expression, "unit": "1"}}


def _submit(client, payload):
    response = client.post(API, json=payload)
    assert response.status_code == 202, response.text
    return response.json()


def _wait(client, job):
    for _ in range(400):
        status = client.get(job["status_url"]).json()
        if status["status"] == "COMPLETED":
            result = client.get(job["result_url"])
            assert result.status_code == 200, result.text
            return result.json()
        assert status["status"] not in {"FAILED", "CANCELLED"}, status
        sleep(0.025)
    pytest.fail("Workflow did not finish")


def _lonlat(crs, affine, row, col):
    x, y = affine * (col + 0.5, row + 0.5)
    lon, lat = transform(crs, "EPSG:4326", [x], [y])
    return {"lon": lon[0], "lat": lat[0]}


def _xyz(lon, lat, zoom):
    scale = 2**zoom
    return (zoom, int((lon + 180) / 360 * scale),
            int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * scale))


def _tile_url(output, z, x, y):
    return output["tiles"].format(z=z, x=x, y=y)


def _tile_array(response):
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(response.content)) as image:
        assert image.size == (256, 256) and image.mode == "RGBA"
        return np.array(image)


@pytest.mark.integration
def test_fixture_workflow_tiles_point_export_and_latency(atlas, fixtures_dir, db_session):
    client, _ = atlas
    fixture = fixtures_dir / "rasters" / "sample_raster_utm43n.tif"
    asset_id = _asset(db_session, fixture, datetime(2020, 3, 12))
    assert any(row["id"] == asset_id for row in client.get(API + "/sources").json())
    payload = {"sources": {"input": {"asset_ids": [asset_id]}}, "steps": [_math(a="input")]}
    job = _submit(client, payload)
    assert _submit(client, payload)["job_id"] == job["job_id"]
    result = _wait(client, job)
    output = result["outputs"][0]

    with rasterio.open(fixture) as source:
        assert source.crs.to_epsg() == 32643
        expected = source.read(1, masked=True)
        row, col = source.height // 2, source.width // 2
        center = _lonlat(source.crs, source.transform, row, col)
        affine = source.transform
        crs = source.crs

    response = client.get(output["export"])
    assert response.status_code == 200
    original_export = response.content
    with MemoryFile(response.content) as memory, memory.open() as exported:
        assert exported.crs == crs and exported.transform == affine
        assert exported.tags(ns="IMAGE_STRUCTURE")["LAYOUT"] == "COG"
        np.testing.assert_array_equal(exported.read(1, masked=True), expected)
    before = client.get(output["point"], params=center).json()
    assert before["bands"][0]["value"] == expected[row, col]
    for zoom in (10, 14, 16):
        url = _tile_url(output, *_xyz(**center, zoom=zoom))
        _tile_array(client.get(url))
    pixels = _tile_array(client.get(_tile_url(output, *_xyz(**center, zoom=14))))
    assert np.any(pixels[:, :, 3] == 255) and np.any(pixels[:, :, 3] == 0)
    assert client.get(output["point"], params=center).json() == before

    # Same tile and band. Distinct style variants give independent cold keys.
    url = _tile_url(output, *_xyz(**center, zoom=14))
    cold, warm = [], []
    for variation in range(10):
        params = {"palette": "gray", "low": -variation - 1, "high": float(expected.max()) + 1}
        start = perf_counter()
        response = client.get(url, params=params)
        cold.append((perf_counter() - start) * 1000)
        assert response.headers["x-tile-cache"] == "MISS"
        start = perf_counter()
        cached = client.get(url, params=params)
        warm.append((perf_counter() - start) * 1000)
        assert cached.headers["x-tile-cache"] == "HIT" and response.content == cached.content
    print(f"Tile latency: {fixture.name}, {expected.shape[1]}×{expected.shape[0]}, "
          f"XYZ {_xyz(**center, zoom=14)}, 10 in-process HTTP cold/warm pairs. "
          f"Cold median {median(cold):.2f} ms (range {min(cold):.2f}–{max(cold):.2f}); "
          f"warm median {median(warm):.2f} ms (range {min(warm):.2f}–{max(warm):.2f}).")

    assert client.post(job["status_url"] + "/restart").status_code == 200
    assert _wait(client, job) == result
    assert response_export(client, output) == original_export


def response_export(client, output):
    response = client.get(output["export"])
    assert response.status_code == 200
    return response.content


@pytest.mark.integration
def test_neighborhood_stitches_at_analysis_and_atlas_tile_edges(atlas):
    client, downloads = atlas
    zoom, tile_x, tile_y = 9, 365, 203
    span = 2 * WEB_LIMIT / (2**zoom)
    resolution = span / 256
    affine = from_origin(-WEB_LIMIT + tile_x * span, WEB_LIMIT - tile_y * span, resolution, resolution)
    rows, columns = np.indices((512, 512))
    values = ((rows % 30) + (columns % 70)).astype("float64")
    values[130:384, 254:259] = -9999
    values[254:257, :119] = -9999
    _raster(downloads / "seam.tif", values, "EPSG:3857", affine)
    job = _submit(client, {
        "sources": {"data": {"local_file": {"path": "seam.tif"}}},
        "steps": [
            _math("a + 10", a="data"),
            {"id": "smooth", "operator": "mean_3x3", "inputs": {"raster": "calc"}},
            {"id": "summary", "operator": "polygon_stats", "inputs": {"raster": "smooth"}},
        ],
        "outputs": ["smooth", "summary"],
    })
    result = _wait(client, job)
    output, stats = result["outputs"]

    # Independent whole-raster NumPy reduction rolls a single 3x3 window over the full image.
    good = values != -9999
    finite = np.where(good, values + 10, np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(np.pad(finite, 1, constant_values=np.nan), (3, 3))
    total = np.nansum(windows, axis=(-1, -2))
    count = np.isfinite(windows).sum(axis=(-1, -2))
    expected = np.divide(total, count, out=np.full(values.shape, np.nan), where=good & (count > 0))
    with MemoryFile(response_export(client, output)) as memory, memory.open() as raster:
        assert raster.transform == affine
        np.testing.assert_allclose(raster.read(1), expected, atol=1e-12, rtol=0)
        np.testing.assert_array_equal(raster.read_masks(1) > 0, good)
    assert stats["statistics"][0]["count"] == int(good.sum())
    assert stats["statistics"][0]["mean"] == pytest.approx(np.nanmean(expected))

    image_rows = []
    for y in (tile_y, tile_y + 1):
        image_rows.append(np.concatenate([
            _tile_array(client.get(_tile_url(output, zoom, x, y), params={"palette": "gray", "low": 0, "high": 255}))
            for x in (tile_x, tile_x + 1)
        ], axis=1))
    atlas_image = np.concatenate(image_rows, axis=0)
    np.testing.assert_array_equal(atlas_image[:, :, 3] > 0, good)
    np.testing.assert_allclose(atlas_image[:, :, 0][good], expected[good], atol=1.01, rtol=0)

    # A publication's tile key must change with the resolved source raster version.
    values[0, 0] += 5
    _raster(downloads / "seam.tif", values, "EPSG:3857", affine)
    updated = _submit(client, {
        "sources": {"data": {"local_file": {"path": "seam.tif"}}},
        "steps": [_math("a + 10", a="data"),
                  {"id": "smooth", "operator": "mean_3x3", "inputs": {"raster": "calc"}},
                  {"id": "summary", "operator": "polygon_stats", "inputs": {"raster": "smooth"}}],
        "outputs": ["smooth", "summary"],
    })
    assert updated["job_id"] != job["job_id"]
    _wait(client, updated)


@pytest.mark.integration
def test_dated_collection_qa_median_and_hsv(atlas, db_session):
    client, downloads = atlas
    collection = uuid4().hex
    affine = from_origin(76, 35, 0.01, 0.01)
    crs = "EPSG:4326"
    footprint = mapping(box(76, 34.97, 76.03, 35))
    ids = {}
    for day, value in ((5, 50), (2, 20), (3, 30), (4, 40)):
        original = np.full((2, 3, 3), value, dtype="int16")
        original[1] = 0
        original[0, 1, 1] = -9999 if day == 3 else value
        original[1, 1, 0] = 2 if day == 4 else 0
        # Day four starts one pixel east of the reference grid.
        date_affine = from_origin(76.01, 35, 0.01, 0.01) if day == 4 else affine
        path = _raster(downloads / f"daily-{day}.tif", original, crs, date_affine)
        ids[day] = _asset(db_session, path, datetime(2020, 3, day, 23, 59), collection, footprint)
    far = _raster(downloads / "disjoint.tif", original, crs, from_origin(80, 35, 0.01, 0.01))
    _asset(db_session, far, datetime(2020, 3, 3), collection, mapping(box(80, 34.97, 80.03, 35)))

    result = _wait(client, _submit(client, {
        "aoi": footprint,
        "sources": {"s": {"collection": collection, "start_date": "2020-03-02", "end_date": "2020-03-04",
                          "qa": {"band": 2, "reject_bits": 2}}},
        "steps": [{"id": "median", "operator": "temporal_median", "inputs": {"raster": "s"}}],
    }))
    assert [row["date"] for row in result["sources"]["s"]] == ["2020-03-02", "2020-03-03", "2020-03-04"]
    point = result["outputs"][0]["point"]
    assert client.get(point, params=_lonlat(crs, affine, 0, 0)).json()["bands"][0]["value"] == 25
    assert client.get(point, params=_lonlat(crs, affine, 0, 2)).json()["bands"][0]["value"] == 30
    assert client.get(point, params=_lonlat(crs, affine, 1, 1)).json()["bands"][0]["value"] == 20
    mismatch = client.post(API, json={"sources": {"first": {"asset_ids": [ids[2]]}, "second": {"asset_ids": [ids[3]]}},
                                     "steps": [_math("a - b", a="first", b="second")]})
    assert mismatch.status_code == 422 and "dates must match" in mismatch.text

    rgb = np.array([[[255, 0, 0]], [[0, 255, 0]], [[0, 0, 255]]], dtype="int16")
    _raster(downloads / "rgb.tif", rgb, crs, affine, np.array([[True, True, False]]))
    color = _wait(client, _submit(client, {
        "sources": {channel: {"local_file": {"path": "rgb.tif"}, "band": i + 1}
                    for i, channel in enumerate(("red", "green", "blue"))},
        "steps": [{"id": "hsv", "operator": "rgb_to_hsv", "inputs": {port: port for port in ("red", "green", "blue")}},
                  _math("h / 360", h="hsv.hue")],
        "outputs": ["hsv", "calc"],
    }))
    pixels, hue_fraction = color["outputs"]
    assert [band["name"] for band in pixels["bands"]] == ["hue", "saturation", "value"]
    with MemoryFile(response_export(client, pixels)) as memory, memory.open() as raster:
        np.testing.assert_array_equal(raster.read()[:, 0, :2], [[0, 120], [1, 1], [1, 1]])
        np.testing.assert_array_equal(raster.read_masks()[:, 0, 2], [0, 0, 0])
        assert raster.units == ("degrees", "1", "1")
    assert client.get(hue_fraction["point"], params=_lonlat(crs, affine, 0, 1)).json()["bands"][0]["value"] == 1 / 3


def triple(inputs, _params):
    return inputs["raster"] * 3


@pytest.mark.integration
def test_registry_extension_and_expression_validation(atlas, fixtures_dir, db_session):
    client, _ = atlas
    asset_id = _asset(db_session, fixtures_dir / "rasters" / "sample_singleband_wgs84.tif")
    register_operator(Operator("triple_fixture", "1", "Triple fixture", "pixel", ("raster",), Parameters,
                               "Same bands and units", "Preserve missing values", same_spec, triple))
    try:
        assert any(entry["id"] == "triple_fixture" for entry in client.get(API + "/operators").json())
        result = _wait(client, _submit(client, {
            "sources": {"s": {"asset_ids": [asset_id]}},
            "steps": [{"id": "triple", "operator": "triple_fixture", "inputs": {"raster": "s"}}],
        }))
        with rasterio.open(fixtures_dir / "rasters" / "sample_singleband_wgs84.tif") as source:
            center = _lonlat(source.crs, source.transform, 20, 20)
            assert client.get(result["outputs"][0]["point"], params=center).json()["bands"][0]["value"] == 3 * source.read(1)[20, 20]
    finally:
        OPERATORS.pop(("triple_fixture", "1"))
    response = client.post(API, json={"sources": {"s": {"asset_ids": [asset_id]}},
                                     "steps": [_math("a.imag", a="s")]})
    assert response.status_code == 422
    response = client.post(API, json={"sources": {"s": {"asset_ids": [asset_id]}},
                                     "steps": [_math("a", a="calc")]})
    assert response.status_code == 422 and "cycle" in response.text


@pytest.mark.integration
def test_startup_recovers_interrupted_workflow(tmp_path, monkeypatch, fixtures_dir, db_session):
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(settings, "downloads_dir", tmp_path / "downloads")
    asset_id = _asset(db_session, fixtures_dir / "rasters" / "sample_singleband_wgs84.tif")
    request = Workflow.model_validate({"sources": {"s": {"asset_ids": [asset_id]}}, "steps": [_math(a="s")]})
    plan = compile_workflow(request, db_session, {})
    job = workflow_jobs.submit(db_session, plan, request.name)
    job.status = JobStatus.RUNNING
    db_session.commit()
    result_url = f"{API}/{job.id}/result"
    assert TestClient(app).get(result_url).status_code == 409
    with TestClient(app) as client:
        result = _wait(client, {"status_url": f"/api/jobs/{job.id}", "result_url": result_url})
        assert result["key"] == plan["key"]
        assert client.get(result["outputs"][0]["export"]).status_code == 200
