import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.transform import from_origin

from backend.app.dependencies.database import SessionLocal
from backend.app.main import app
from backend.app.models.models import Asset, AssetLineage, Dataset, Download, DownloadStatus, Job, JobStatus
from backend.app.schemas.schemas import AssetInfo, SearchResultItem
from backend.core.catalog.engine import catalog_engine
from backend.core.jobs.engine import JobEngine
from backend.core.satellites.bands import resolve_scene_band_selection
from backend.core.storage.estimator import StorageEstimator


pytestmark = [pytest.mark.integration, pytest.mark.geospatial]


@pytest.fixture(autouse=True)
def _isolate_stac_catalog_dir(tmp_path_factory, monkeypatch):
    """Redirect STAC catalog writes during Phase 3 integration tests into an isolated temp root."""
    isolated_cat = tmp_path_factory.mktemp("stac_catalog")
    monkeypatch.setattr(catalog_engine, "catalog_root", isolated_cat)
    catalog_engine._ensure_root_catalog()
    yield


def _write_test_geotiff(
    path: Path,
    *,
    width: int = 32,
    height: int = 32,
    res: float = 10.0,
    crs: str = "EPSG:32643",
    origin_x: float = 500000.0,
    origin_y: float = 3800000.0,
    fill_values=100,
    dtype: str = "uint16",
    nodata=0,
    count: int = 1,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(origin_x, origin_y, res, res)
    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": count,
        "dtype": dtype,
        "crs": crs,
        "transform": transform,
    }
    if nodata is not None:
        profile["nodata"] = nodata

    vals = fill_values if isinstance(fill_values, (list, tuple)) else [fill_values] * count
    with rasterio.open(path, "w", **profile) as dst:
        for b_idx in range(1, count + 1):
            arr = np.full((height, width), vals[b_idx - 1], dtype=dtype)
            if nodata is not None:
                arr[0, 0] = nodata
            dst.write(arr, b_idx)
    return path


def _make_sentinel_cdse_scene(scene_id: str, dt_iso: str) -> SearchResultItem:
    base_url = f"https://example.org/{scene_id}"
    return SearchResultItem(
        id=scene_id,
        collection="sentinel-2-l2a",
        provider_id="copernicus-dataspace",
        title=scene_id,
        datetime=dt_iso,
        cloud_cover=4.2,
        resolution_meters=10.0,
        bbox=[77.0, 34.0, 77.01, 34.01],
        geometry={
            "type": "Polygon",
            "coordinates": [[[77.0, 34.0], [77.01, 34.0], [77.01, 34.01], [77.0, 34.01], [77.0, 34.0]]],
        },
        assets={
            "B02_10m": AssetInfo(name="B02_10m", title="Band 2 - Blue (10m)", url=f"{base_url}/B02_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="B02"),
            "blue": AssetInfo(name="blue", title="Band 2 - Blue (10m)", url=f"{base_url}/B02_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="blue"),
            "B02_20m": AssetInfo(name="B02_20m", title="Band 2 - Blue (20m)", url=f"{base_url}/B02_20m.jp2", size_bytes=800, mime_type="image/jp2", band="B02"),
            "B03_10m": AssetInfo(name="B03_10m", title="Band 3 - Green (10m)", url=f"{base_url}/B03_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="B03"),
            "green": AssetInfo(name="green", title="Band 3 - Green (10m)", url=f"{base_url}/B03_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="green"),
            "B04_10m": AssetInfo(name="B04_10m", title="Band 4 - Red (10m)", url=f"{base_url}/B04_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="B04"),
            "red": AssetInfo(name="red", title="Band 4 - Red (10m)", url=f"{base_url}/B04_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="red"),
            "B08_10m": AssetInfo(name="B08_10m", title="Band 8 - NIR (10m)", url=f"{base_url}/B08_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="B08"),
            "nir": AssetInfo(name="nir", title="Band 8 - NIR (10m)", url=f"{base_url}/B08_10m.jp2", size_bytes=2000, mime_type="image/jp2", band="nir"),
            "B11_20m": AssetInfo(name="B11_20m", title="Band 11 - SWIR 1 (20m)", url=f"{base_url}/B11_20m.jp2", size_bytes=1000, mime_type="image/jp2", band="B11"),
            "B12_20m": AssetInfo(name="B12_20m", title="Band 12 - SWIR 2 (20m)", url=f"{base_url}/B12_20m.jp2", size_bytes=1000, mime_type="image/jp2", band="B12"),
            "TCI_10m": AssetInfo(name="TCI_10m", title="True Color Image (10m)", url=f"{base_url}/TCI_10m.jp2", size_bytes=3000, mime_type="image/jp2", band="TCI"),
            "TCI_20m": AssetInfo(name="TCI_20m", title="True Color Image (20m)", url=f"{base_url}/TCI_20m.jp2", size_bytes=1500, mime_type="image/jp2", band="TCI"),
            "visual": AssetInfo(name="visual", title="True Color Image", url=f"{base_url}/TCI_10m.jp2", size_bytes=3000, mime_type="image/jp2", band="visual"),
            "thumbnail": AssetInfo(name="thumbnail", title="Overview", url=f"{base_url}/thumb.jpg", size_bytes=256, mime_type="image/jpeg", band=None),
        },
    )


def _make_landsat8_scene(scene_id: str, dt_iso: str) -> SearchResultItem:
    base_url = f"https://example.org/{scene_id}"
    return SearchResultItem(
        id=scene_id,
        collection="landsat-c2-l2",
        provider_id="usgs-landsat-pc",
        title=scene_id,
        datetime=dt_iso,
        cloud_cover=5.0,
        resolution_meters=30.0,
        bbox=[78.0, 28.0, 78.01, 28.01],
        geometry={
            "type": "Polygon",
            "coordinates": [[[78.0, 28.0], [78.01, 28.0], [78.01, 28.01], [78.0, 28.01], [78.0, 28.0]]],
        },
        assets={
            "blue": AssetInfo(name="blue", title="Band 2 - Blue", url=f"{base_url}/SR_B2.tif", size_bytes=4096, mime_type="image/tiff", band="SR_B2"),
            "green": AssetInfo(name="green", title="Band 3 - Green", url=f"{base_url}/SR_B3.tif", size_bytes=4096, mime_type="image/tiff", band="SR_B3"),
            "red": AssetInfo(name="red", title="Band 4 - Red", url=f"{base_url}/SR_B4.tif", size_bytes=4096, mime_type="image/tiff", band="SR_B4"),
            "nir08": AssetInfo(name="nir08", title="Band 5 - Near Infrared (NIR)", url=f"{base_url}/SR_B5.tif", size_bytes=4096, mime_type="image/tiff", band="SR_B5"),
            "swir16": AssetInfo(name="swir16", title="Band 6 - SWIR 1", url=f"{base_url}/SR_B6.tif", size_bytes=4096, mime_type="image/tiff", band="SR_B6"),
            "swir22": AssetInfo(name="swir22", title="Band 7 - SWIR 2", url=f"{base_url}/SR_B7.tif", size_bytes=4096, mime_type="image/tiff", band="SR_B7"),
            "rendered_preview": AssetInfo(name="rendered_preview", url=f"{base_url}/preview.png", size_bytes=512, mime_type="image/png", band=None),
        },
    )


def test_band_resolution_dedup_and_estimator_consistency():
    scene = _make_sentinel_cdse_scene("S2A_MSIL2A_20240115T052000_N0510_T43SFU", "2024-01-15T05:20:00Z")

    # Default UI selection mixes 'visual' with spectral bands -> should select ONLY 4 unique 10m spectral assets
    res = resolve_scene_band_selection(scene, ["visual", "red", "green", "blue", "nir"])
    assert res.mode == "stack_bands"
    assert [item.asset_key for item in res.selected_assets] == ["red", "green", "blue", "nir"]
    assert "visual" in res.skipped_ancillary

    # Requesting using B02/B08 aliases selects one finest-resolution asset per band, without B02_20m duplicates
    res_codes = resolve_scene_band_selection(scene, ["B02", "B03", "B04", "B08", "B11", "B12"])
    assert len(res_codes.selected_assets) == 6
    assert [item.canonical_band for item in res_codes.selected_assets] == [
        "blue",
        "green",
        "red",
        "nir",
        "swir16",
        "swir22",
    ]

    # Visual-only resolves to single_multiband_raster and skips non-requested assets
    res_vis = resolve_scene_band_selection(scene, ["visual"])
    assert res_vis.mode == "single_multiband_raster"
    assert len(res_vis.selected_assets) == 1
    assert res_vis.selected_assets[0].canonical_band == "visual"

    # Thumbnail-only resolves to direct mode
    res_thumb = resolve_scene_band_selection(scene, ["thumbnail"])
    assert res_thumb.mode == "direct"
    assert [item.asset_key for item in res_thumb.selected_assets] == ["thumbnail"]

    # StorageEstimator uses same deduplication (no duplicate byte counting across aliases / 20m variants)
    estimator = StorageEstimator()
    est = estimator.estimate([scene], ["red", "green", "blue", "nir"])
    assert est.asset_count == 4
    assert est.raw_bytes == 8000


@pytest.mark.asyncio
async def test_e2e_landsat8_6band_stacking_catalog_lineage_and_cleanup(tmp_path):
    db = SessionLocal()
    try:
        engine = JobEngine()
        scene = _make_landsat8_scene("LC08_L2SP_139043_20240615_phase3", "2024-06-15T04:55:00Z")
        events = []
        engine.add_listener(events.append)

        band_val_by_suffix = {
            "SR_B2.tif": 200,
            "SR_B3.tif": 300,
            "SR_B4.tif": 400,
            "SR_B5.tif": 500,
            "SR_B6.tif": 600,
            "SR_B7.tif": 700,
        }

        async def fake_download_file(url, destination_path, **kwargs):
            dest = Path(destination_path)
            val = next(v for suf, v in band_val_by_suffix.items() if url.endswith(suf))
            _write_test_geotiff(
                dest,
                width=24,
                height=24,
                res=30.0,
                crs="EPSG:32644",
                origin_x=200000.0,
                origin_y=3100000.0,
                fill_values=val,
                dtype="uint16",
                nodata=0,
            )
            return True

        with patch.object(engine.download_engine, "download_file", side_effect=fake_download_file):
            job = engine.create_harvest_job(
                name="Indus Valley Project",
                scenes=[scene],
                selected_bands=["B2", "B3", "B4", "B5", "B6", "B7"],
                db=db,
                destination_dir=str(tmp_path),
                target_crs="native",
            )
            if job.id in engine._active_tasks:
                await engine._active_tasks[job.id]
            else:
                await engine._run_job(job.id)

        db.expire_all()
        done_job = db.query(Job).filter(Job.id == job.id).first()
        assert done_job.status == JobStatus.COMPLETED
        assert done_job.progress == 100.0
        assert done_job.completed_at is not None

        expected_tif = (
            tmp_path / "Indus_Valley_Project" / "landsat-c2-l2" / "2024" / "06" / "LC08_L2SP_139043_20240615_phase3.tif"
        )
        assert expected_tif.exists()

        # No individual band files or staging dirs remain anywhere under dest_root
        all_files = [p for p in tmp_path.rglob("*") if p.is_file()]
        assert all_files == [expected_tif]
        assert not (tmp_path / ".staging").exists()

        with rasterio.open(expected_tif) as src:
            assert src.driver == "GTiff"
            assert src.count == 6
            assert src.width == 24
            assert src.height == 24
            assert src.crs.to_string() == "EPSG:32644"
            assert src.nodata == 0
            assert src.is_tiled
            assert all(dt == "uint16" for dt in src.dtypes)
            descs = list(src.descriptions)
            assert "Blue" in descs[0] and "Green" in descs[1] and "Red" in descs[2]
            assert "NIR" in descs[3]
            tags = src.tags()
            assert tags["SCENE_ID"] == scene.id
            assert tags["BAND_COUNT"] == "6"
            for idx, exp_val in enumerate([200, 300, 400, 500, 600, 700], start=1):
                band_arr = src.read(idx)
                assert int(band_arr[0, 0]) == 0  # preserved nodata pixel
                assert int(band_arr[5, 5]) == exp_val

        # Check STAC catalog & SQLite Asset + AssetLineage
        stacked_asset = db.query(Asset).filter(Asset.id == f"{scene.id}_stacked").first()
        assert stacked_asset is not None
        assert stacked_asset.asset_type == "stacked_geotiff"
        assert Path(stacked_asset.local_path) == expected_tif.resolve()
        assert stacked_asset.status == "processed"

        raw_assets = db.query(Asset).filter(Asset.dataset_id == scene.id, Asset.id != stacked_asset.id).all()
        assert len(raw_assets) == 6
        assert all(a.local_path is None and a.status == "processed" for a in raw_assets)

        lineages = db.query(AssetLineage).filter(AssetLineage.derived_asset_id == stacked_asset.id).all()
        assert len(lineages) == 6
        assert all(lin.operation == "scene_stack" for lin in lineages)

        ds = db.query(Dataset).filter(Dataset.id == scene.id).first()
        stac_path = Path(ds.dataset_metadata["stac_item_path"])
        assert stac_path.exists()
        stac_doc = json.loads(stac_path.read_text())
        assert Path(stac_doc["assets"]["stacked"]["href"]) == expected_tif.resolve()
        assert stac_doc["properties"]["proj:code"] == "EPSG:32644"

        scene_events = [e for e in events if e.get("type") == "scene_progress" and e.get("scene_id") == scene.id]
        assert [e.get("status") for e in scene_events] == ["stacking", "completed"]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_sentinel2_multires_multimonth_same_month_separation_and_mosaic_storage_api(tmp_path):
    db = SessionLocal()
    try:
        engine = JobEngine()
        s_jan1 = _make_sentinel_cdse_scene("S2A_MSIL2A_20240110T052000_T43SFU_p3", "2024-01-10T05:20:00Z")
        s_jan2 = _make_sentinel_cdse_scene("S2B_MSIL2A_20240120T052000_T43SFU_p3", "2024-01-20T05:20:00Z")
        s_feb1 = _make_sentinel_cdse_scene("S2A_MSIL2A_20250205T052000_T43SFU_p3", "2025-02-05T05:20:00Z")

        # Give each scene slightly shifted origins or distinct pixel values across 10m & 20m bands
        async def fake_download_file(url, destination_path, **kwargs):
            dest = Path(destination_path)
            if "20m" in url or "B11" in url or "B12" in url:
                fill = 1100 if "B11" in url else 1200
                _write_test_geotiff(dest, width=16, height=16, res=20.0, fill_values=fill)
            else:
                fill = 10 if "B02" in url else (20 if "B03" in url else (30 if "B04" in url else 80))
                _write_test_geotiff(dest, width=32, height=32, res=10.0, fill_values=fill)
            return True

        with patch.object(engine.download_engine, "download_file", side_effect=fake_download_file):
            job = engine.create_harvest_job(
                name="Himalaya Glaciers",
                scenes=[s_jan1, s_jan2, s_feb1],
                # Include 'visual' like frontend default + request B11/B12 -> TCI/visual & duplicates skipped cleanly
                selected_bands=["visual", "red", "green", "blue", "nir", "swir16", "swir22"],
                db=db,
                destination_dir=str(tmp_path),
                target_crs="native",
            )
            if job.id in engine._active_tasks:
                await engine._active_tasks[job.id]
            else:
                await engine._run_job(job.id)

        db.expire_all()
        done_job = db.query(Job).filter(Job.id == job.id).first()
        assert done_job.status == JobStatus.COMPLETED

        base_ds = tmp_path / "Himalaya_Glaciers" / "sentinel-2-l2a"
        tif_jan1 = base_ds / "2024" / "01" / f"{s_jan1.id}.tif"
        tif_jan2 = base_ds / "2024" / "01" / f"{s_jan2.id}.tif"
        tif_feb1 = base_ds / "2025" / "02" / f"{s_feb1.id}.tif"

        assert tif_jan1.exists() and tif_jan2.exists() and tif_feb1.exists()
        assert set(tmp_path.rglob("*.tif")) == {tif_jan1, tif_jan2, tif_feb1}

        for tif_path in (tif_jan1, tif_jan2, tif_feb1):
            with rasterio.open(tif_path) as src:
                assert src.count == 6
                assert src.width == 32 and src.height == 32
                assert src.res == pytest.approx((10.0, 10.0))

        # Check mosaic options endpoint exposes the 3 stacked deliverables (not staging files)
        client = TestClient(app)
        resp = client.get(f"/api/processing/jobs/{job.id}/mosaic-options")
        assert resp.status_code == 200
        body = resp.json()
        assert body["eligible"] is True
        assert len(body["raster_assets"]) == 3
        assert "stacked" in body["available_bands"]

        # Execute mosaic on the stacked GeoTIFF deliverables
        out_mosaic = tmp_path / "mosaicked_out.tif"
        clip_resp = client.post(
            f"/api/processing/jobs/{job.id}/mosaic-clip",
            json={"output_path": str(out_mosaic)},
        )
        assert clip_resp.status_code == 200
        clip_data = clip_resp.json()
        assert clip_data["status"] == "queued"
        assert clip_data["input_files_count"] == 3

        from backend.core.processing.pipeline import pipeline_runner

        exec_ok = await pipeline_runner.run_mosaic_clip_task(
            task_id=clip_data["task_id"],
            input_file_paths=[item["destination"] for item in body["raster_assets"]],
            output_path=str(out_mosaic),
            aoi_geometry=None,
            target_crs=None,
            to_cog=True,
        )
        assert exec_ok is True
        assert out_mosaic.exists()
        with rasterio.open(out_mosaic) as msrc:
            assert msrc.count == 6

        # Storage search must never expose hidden .staging entries
        with patch("backend.app.dependencies.config.settings.downloads_dir", tmp_path):
            sr = client.get("/api/storage/search", params={"query": ".tif", "root": "downloads"})
            assert sr.status_code == 200
            names = {item["name"] for item in sr.json()}
            assert ".staging" not in str(sr.json())
            assert f"{s_jan1.id}.tif" in names
    finally:
        db.close()


@pytest.mark.asyncio
async def test_visual_only_thumbnail_direct_and_toposheet_modes(tmp_path):
    db = SessionLocal()
    try:
        engine = JobEngine()
        scene_vis = _make_sentinel_cdse_scene("S2A_MSIL2A_20240401T050000_VIS", "2024-04-01T05:00:00Z")
        scene_thumb = _make_sentinel_cdse_scene("S2A_MSIL2A_20240402T050000_THUMB", "2024-04-02T05:00:00Z")
        scene_topo = SearchResultItem(
            id="SOI_43J_12_TOPO",
            collection="survey-of-india-osm",
            provider_id="survey-of-india",
            title="Toposheet 43J/12",
            datetime="2024-04-03T00:00:00Z",
            bbox=[77.0, 34.0, 77.25, 34.25],
            geometry={"type": "Polygon", "coordinates": []},
            assets={
                "pdf": AssetInfo(name="pdf", url="https://example.org/43J_12.pdf", size_bytes=256, mime_type="application/pdf")
            },
        )

        async def fake_download_file(url, destination_path, **kwargs):
            dest = Path(destination_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if url.endswith(".jp2"):
                _write_test_geotiff(dest, width=16, height=16, res=10.0, count=3, fill_values=[25, 50, 75], dtype="uint8", nodata=None)
            elif url.endswith(".jpg"):
                dest.write_bytes(b"\xff\xd8\xff\xe0JFIF_MOCK")
            else:
                dest.write_bytes(b"%PDF-1.4 MOCK")
            return True

        with patch.object(engine.download_engine, "download_file", side_effect=fake_download_file):
            # 1) Visual-only -> 3-band GeoTIFF at scene deliverable path
            j_vis = engine.create_harvest_job("Visual Only", [scene_vis], ["visual"], db, destination_dir=str(tmp_path / "vis"))
            # 2) Thumbnail-only -> direct JPEG download, no stacking
            j_thumb = engine.create_harvest_job("Thumb Only", [scene_thumb], ["thumbnail"], db, destination_dir=str(tmp_path / "thumb"))
            # 3) Toposheet -> direct legacy structure preserved
            j_topo = engine.create_harvest_job("Topo Task", [scene_topo], ["all"], db, destination_dir=str(tmp_path / "topo"), is_toposheet=True)

            for j in (j_vis, j_thumb, j_topo):
                if j.id in engine._active_tasks:
                    await engine._active_tasks[j.id]
                else:
                    await engine._run_job(j.id)

        db.expire_all()
        vis_tif = tmp_path / "vis" / "Visual_Only" / "sentinel-2-l2a" / "2024" / "04" / f"{scene_vis.id}.tif"
        assert vis_tif.exists()
        with rasterio.open(vis_tif) as src:
            assert src.count == 3
            assert src.crs.to_string() == "EPSG:4326"
            assert list(src.descriptions) == ["Red", "Green", "Blue"]
        assert not (tmp_path / "vis" / ".staging").exists()

        thumb_files = list((tmp_path / "thumb").rglob("*.jpg"))
        assert len(thumb_files) == 1
        assert db.query(Job).filter(Job.id == j_thumb.id).first().status == JobStatus.COMPLETED

        topo_pdfs = list((tmp_path / "topo" / "Topo_Task" / "2024" / "04" / "SOI_43J_12_TOPO").glob("*.pdf"))
        assert len(topo_pdfs) == 1
        assert db.query(Job).filter(Job.id == j_topo.id).first().status == JobStatus.COMPLETED
    finally:
        db.close()


@pytest.mark.asyncio
async def test_stacking_failure_preserves_staging_resume_succeeds_and_reuse_existing(tmp_path):
    db = SessionLocal()
    try:
        engine = JobEngine()
        scene = _make_landsat8_scene("LC08_L2SP_140040_20240501_retry", "2024-05-01T05:00:00Z")

        async def bad_crs_download(url, destination_path, **kwargs):
            dest = Path(destination_path)
            # Band 3 has incompatible CRS when allow_reproject=False -> stacking fails validation
            crs = "EPSG:32645" if url.endswith("SR_B3.tif") else "EPSG:32644"
            _write_test_geotiff(dest, width=16, height=16, res=30.0, crs=crs, fill_values=123, nodata=0)
            return True

        with patch.object(engine.download_engine, "download_file", side_effect=bad_crs_download):
            job = engine.create_harvest_job(
                name="Retry Project",
                scenes=[scene],
                selected_bands=["blue", "green"],
                db=db,
                destination_dir=str(tmp_path),
                allow_reproject=False,
            )
            if job.id in engine._active_tasks:
                await engine._active_tasks[job.id]
            else:
                await engine._run_job(job.id)

        db.expire_all()
        failed_job = db.query(Job).filter(Job.id == job.id).first()
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.completed_at is None

        plan = failed_job.job_metadata["scene_plans"][scene.id]
        assert plan["status"] == "failed"
        staging_dir = Path(plan["staging_dir"])
        final_tif = Path(plan["final_output_path"])
        assert not final_tif.exists()
        # Downloaded staging files MUST remain intact after stacking failure
        staged_tifs = sorted(staging_dir.glob("*.tif"))
        assert len(staged_tifs) == 2

        # Fix the bad staged green band in-place and resume without re-downloading
        bad_green = next(p for p in staged_tifs if "green" in p.name or "B3" in p.name)
        _write_test_geotiff(bad_green, width=16, height=16, res=30.0, crs="EPSG:32644", fill_values=456, nodata=0)

        download_calls = []

        async def fail_if_redownloaded(*args, **kwargs):
            download_calls.append(args)
            return True

        with patch.object(engine.download_engine, "download_file", side_effect=fail_if_redownloaded):
            resumed = engine.resume_job(job.id, db)
            assert resumed is True
            if job.id in engine._active_tasks:
                await engine._active_tasks[job.id]
            else:
                await engine._run_job(job.id)

        # Resume stacked directly from preserved staging files without re-downloading
        assert len(download_calls) == 0

        db.expire_all()
        ok_job = db.query(Job).filter(Job.id == job.id).first()
        assert ok_job.status == JobStatus.COMPLETED
        assert final_tif.exists()
        assert not staging_dir.exists()
        with rasterio.open(final_tif) as src:
            assert src.count == 2
            assert int(src.read(1)[4, 4]) == 123
            assert int(src.read(2)[4, 4]) == 456

        # Second identical job reuses valid existing final GeoTIFF without creating _1 duplicates
        async def second_download(url, destination_path, **kwargs):
            _write_test_geotiff(Path(destination_path), width=16, height=16, res=30.0, crs="EPSG:32644", fill_values=999, nodata=0)
            return True

        with patch.object(engine.download_engine, "download_file", side_effect=second_download):
            job2 = engine.create_harvest_job(
                name="Retry Project",
                scenes=[scene],
                selected_bands=["blue", "green"],
                db=db,
                destination_dir=str(tmp_path),
            )
            if job2.id in engine._active_tasks:
                await engine._active_tasks[job2.id]
            else:
                await engine._run_job(job2.id)

        db.expire_all()
        ok_job2 = db.query(Job).filter(Job.id == job2.id).first()
        assert ok_job2.status == JobStatus.COMPLETED
        assert ok_job2.job_metadata["scene_plans"][scene.id]["warnings"] == ["Reused existing validated scene GeoTIFF"]
        # Pixel values untouched from first validated deliverable, single .tif only
        assert list(final_tif.parent.glob("*.tif")) == [final_tif]
        with rasterio.open(final_tif) as src:
            assert int(src.read(1)[4, 4]) == 123
    finally:
        db.close()


@pytest.mark.asyncio
async def test_api_jobs_forwards_configurable_stacking_options(tmp_path):
    db = SessionLocal()
    try:
        scene = _make_sentinel_cdse_scene("S2A_MSIL2A_20240710T052000_CFG", "2024-07-10T05:20:00Z")

        async def fake_download_file(url, destination_path, **kwargs):
            dest = Path(destination_path)
            if "B11" in url or "20m" in url:
                _write_test_geotiff(dest, width=16, height=16, res=20.0, fill_values=200)
            else:
                _write_test_geotiff(dest, width=32, height=32, res=10.0, fill_values=100)
            return True

        from backend.core.jobs.engine import job_engine

        with patch.object(job_engine.download_engine, "download_file", side_effect=fake_download_file):
            client = TestClient(app)
            resp = client.post(
                "/api/jobs",
                json={
                    "name": "Coarsest Config Test",
                    "scenes": [scene.model_dump()],
                    "bands": ["red", "swir16"],
                    "destination_dir": str(tmp_path),
                    "target_resolution": "coarsest",
                    "resampling_method": "nearest",
                    "target_crs": "native",
                },
            )
            assert resp.status_code == 200
            job_id = resp.json()["id"]
            if job_id in job_engine._active_tasks:
                await job_engine._active_tasks[job_id]
            else:
                await job_engine._run_job(job_id)

        db.expire_all()
        job = db.query(Job).filter(Job.id == job_id).first()
        assert job.status == JobStatus.COMPLETED
        out_tif = Path(job.job_metadata["scene_plans"][scene.id]["final_output_path"])
        with rasterio.open(out_tif) as src:
            assert src.count == 2
            # Coarsest resolution = 20m -> 16x16 instead of 32x32
            assert src.width == 16 and src.height == 16
            assert src.res == pytest.approx((20.0, 20.0))
    finally:
        db.close()


@pytest.mark.asyncio
async def test_restart_failed_scene_and_job_endpoints(tmp_path):
    db = SessionLocal()
    try:
        from backend.core.jobs.engine import job_engine

        scene1 = _make_sentinel_cdse_scene("S2A_MSIL2A_20240710T052000_R1", "2024-07-10T05:20:00Z")
        scene2 = _make_sentinel_cdse_scene("S2A_MSIL2A_20240710T052000_R2", "2024-07-10T05:20:00Z")
        corrupt_first_run = {"active": True}

        async def fake_download_file(url, destination_path, **kwargs):
            dest = Path(destination_path)
            if corrupt_first_run["active"] and "R2" in str(dest) and "red" in str(dest):
                # Write mismatched CRS on first run for scene2's red band
                _write_test_geotiff(dest, width=16, height=16, res=10.0, crs="EPSG:4326", fill_values=50)
            else:
                _write_test_geotiff(dest, width=16, height=16, res=10.0, crs="EPSG:32643", fill_values=120)
            return True

        with patch.object(job_engine.download_engine, "download_file", side_effect=fake_download_file):
            client = TestClient(app)
            resp = client.post(
                "/api/jobs",
                json={
                    "name": "Restart Test",
                    "scenes": [scene1.model_dump(), scene2.model_dump()],
                    "bands": ["red", "blue"],
                    "destination_dir": str(tmp_path),
                },
            )
            assert resp.status_code == 200
            job_id = resp.json()["id"]
            if job_id in job_engine._active_tasks:
                await job_engine._active_tasks[job_id]
            else:
                await job_engine._run_job(job_id)

            detail1 = client.get(f"/api/jobs/{job_id}").json()
            assert detail1["status"] == "FAILED"
            assert detail1["progress"] < 100.0
            s2_item = next(s for s in detail1["scenes"] if s["scene_id"] == scene2.id)
            assert s2_item["status"] == "failed"
            assert s2_item["progress_percentage"] == 90.0

            # Now fix upstream and call POST /api/jobs/{job_id}/scenes/{scene_id}/restart
            corrupt_first_run["active"] = False
            restart_resp = client.post(f"/api/jobs/{job_id}/scenes/{scene2.id}/restart")
            assert restart_resp.status_code == 200
            if job_id in job_engine._active_tasks:
                await job_engine._active_tasks[job_id]
            else:
                await job_engine._run_job(job_id)

            detail2 = client.get(f"/api/jobs/{job_id}").json()
            assert detail2["status"] == "COMPLETED"
            assert detail2["progress"] == 100.0
            assert all(s["status"] == "completed" and s["progress_percentage"] == 100.0 for s in detail2["scenes"])
    finally:
        db.close()


@pytest.mark.asyncio
async def test_default_harvest_and_processing_output_epsg4326(tmp_path):
    """Default POST /api/jobs, direct GeoTIFF harvest, and mosaic/execute endpoints output EPSG:4326."""
    db = SessionLocal()
    try:
        from backend.core.jobs.engine import job_engine

        scene = _make_sentinel_cdse_scene("S2B_43SFS_20261117_0_L2A_WGS", "2026-11-17T05:30:00Z")

        # Pre-seed an old EPSG:32643 file at the deliverable path to ensure it is NOT reused when EPSG:4326 is requested
        existing_out = (
            tmp_path
            / "WGS84_Default_Harvest"
            / "sentinel-2-l2a"
            / "2026"
            / "11"
            / f"{scene.id}.tif"
        )
        _write_test_geotiff(existing_out, width=16, height=16, res=10.0, crs="EPSG:32643", fill_values=[99, 99], count=2)

        async def fake_download_utm(url, destination_path, **kwargs):
            _write_test_geotiff(Path(destination_path), width=24, height=24, res=10.0, crs="EPSG:32643", fill_values=250)
            return True

        client = TestClient(app)
        with patch.object(job_engine.download_engine, "download_file", side_effect=fake_download_utm):
            resp = client.post(
                "/api/jobs",
                json={
                    "name": "WGS84 Default Harvest",
                    "scenes": [scene.model_dump()],
                    "bands": ["red", "blue"],
                    "destination_dir": str(tmp_path),
                },
            )
            assert resp.status_code == 200
            job_id = resp.json()["id"]
            if job_id in job_engine._active_tasks:
                await job_engine._active_tasks[job_id]
            else:
                await job_engine._run_job(job_id)

        db.expire_all()
        job = db.query(Job).filter(Job.id == job_id).first()
        assert job.status == JobStatus.COMPLETED
        assert job.job_metadata["stacking_config"]["target_crs"] == "EPSG:4326"
        assert existing_out.exists()
        with rasterio.open(existing_out) as src:
            assert src.crs.to_string() == "EPSG:4326"
            assert src.count == 2

        ds = db.query(Dataset).filter(Dataset.id == scene.id).first()
        stac_doc = json.loads(Path(ds.dataset_metadata["stac_item_path"]).read_text())
        assert stac_doc["properties"]["proj:code"] == "EPSG:4326"

        # Verify Mosaic & Clip API defaults to EPSG:4326 even on EPSG:32643 inputs
        utm_tile = _write_test_geotiff(tmp_path / "utm_tile.tif", width=24, height=24, res=10.0, crs="EPSG:32643", fill_values=333)
        mosaic_out = tmp_path / "mosaic_default_4326.tif"
        mos_resp = client.post(
            "/api/processing/mosaic-clip",
            json={
                "input_file_paths": [str(utm_tile)],
                "output_path": str(mosaic_out),
            },
        )
        assert mos_resp.status_code == 200
        assert mos_resp.json()["crs"] == "EPSG:4326"
        with rasterio.open(mosaic_out) as msrc:
            assert msrc.crs.to_string() == "EPSG:4326"

        # Verify invalid target_crs returns HTTP 400 cleanly
        bad_resp = client.post(
            "/api/jobs",
            json={
                "name": "Invalid CRS Job",
                "scenes": [scene.model_dump()],
                "bands": ["red"],
                "target_crs": "NOT_A_VALID_CRS_99999",
            },
        )
        assert bad_resp.status_code == 400

        # Verify direct mode raster (e.g. toposheet GeoTIFF in EPSG:32643) also converts to EPSG:4326
        topo_scene = SearchResultItem(
            id="SOI_43J_12_GEO",
            collection="survey-of-india-50k",
            provider_id="survey-of-india-toposheets",
            title="Toposheet GeoTIFF 43J/12",
            datetime="2024-01-01T00:00:00Z",
            bbox=[77.0, 34.0, 77.25, 34.25],
            geometry={"type": "Polygon", "coordinates": []},
            assets={
                "georef_tif": AssetInfo(
                    name="georef_tif",
                    url="https://example.org/43J_12.tif",
                    size_bytes=1024,
                    mime_type="image/tiff",
                    band="georef",
                )
            },
        )
        with patch.object(job_engine.download_engine, "download_file", side_effect=fake_download_utm):
            topo_job = job_engine.create_harvest_job(
                name="Topo GeoTIFF WGS84",
                scenes=[topo_scene],
                selected_bands=["all"],
                db=db,
                destination_dir=str(tmp_path / "topo_wgs"),
                is_toposheet=True,
            )
            if topo_job.id in job_engine._active_tasks:
                await job_engine._active_tasks[topo_job.id]
            else:
                await job_engine._run_job(topo_job.id)

        db.expire_all()
        done_topo = db.query(Job).filter(Job.id == topo_job.id).first()
        assert done_topo.status == JobStatus.COMPLETED
        topo_tifs = list((tmp_path / "topo_wgs").rglob("*.tif"))
        assert len(topo_tifs) == 1
        with rasterio.open(topo_tifs[0]) as tsrc:
            assert tsrc.crs.to_string() == "EPSG:4326"
    finally:
        db.close()
