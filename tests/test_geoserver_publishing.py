import datetime
import shutil
import uuid
from pathlib import Path

import httpx
import pytest


@pytest.mark.asyncio
async def test_geoserver_ingest_resolves_actual_layer_name_and_skips_staging(tmp_path, monkeypatch):
    from backend.app.dependencies.config import settings
    from backend.core.geoserver import GeoServerManager

    downloads_dir = tmp_path / "downloads"
    external_dir = tmp_path / "geoserver_files"
    custom_dir = tmp_path / "custom_dl"
    downloads_dir.mkdir()
    external_dir.mkdir()
    custom_dir.mkdir()

    monkeypatch.setattr(settings, "geoserver_enabled", True)
    monkeypatch.setattr(settings, "geoserver_rest_url", "http://geoserver:8080/geoserver")
    monkeypatch.setattr(settings, "geoserver_public_url", "http://localhost:8080/geoserver")
    monkeypatch.setattr(settings, "geoserver_workspace", "geoharvest")
    monkeypatch.setattr(settings, "downloads_dir", downloads_dir)
    monkeypatch.setattr(settings, "geoserver_files_dir", external_dir)
    monkeypatch.setattr(settings, "geoserver_downloads_mount", "/opt/geoserver_data/downloads")
    monkeypatch.setattr(settings, "geoserver_external_mount", "/opt/geoserver_external")

    dl_tif = downloads_dir / "Ladakh" / "S2A_43SCA_20261117_0_L2A.tif"
    dl_tif.parent.mkdir(parents=True)
    dl_tif.write_bytes(b"II*\x00dummy")

    staging_tif = downloads_dir / ".staging" / "job_123" / "band_b04.tif"
    staging_tif.parent.mkdir(parents=True)
    staging_tif.write_bytes(b"II*\x00staging")

    custom_tif = custom_dir / "custom_scene.tif"
    custom_tif.write_bytes(b"II*\x00custom")

    requests_seen = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url, **kwargs):
            requests_seen.append(("GET", url))
            if url.endswith("/workspaces/geoharvest.json"):
                return httpx.Response(200, json={"workspace": {"name": "geoharvest"}})
            if url.endswith("/coverages.json") and "s2a_43sca" in url:
                return httpx.Response(
                    200,
                    json={"coverages": {"coverage": [{"name": "S2A_43SCA_20261117_0_L2A"}]}},
                )
            return httpx.Response(404)

        async def put(self, url, content=None, headers=None, **kwargs):
            requests_seen.append(("PUT", url, content.decode("utf-8") if content else ""))
            return httpx.Response(201, text="<coverageStore/>")

    manager = GeoServerManager()
    monkeypatch.setattr(manager, "_client", lambda: _FakeClient())

    staging_res = await manager.ingest(staging_tif)
    assert staging_res["published"] is False
    assert staging_res["skipped"] == "staging"
    assert requests_seen == []

    dl_res = await manager.ingest(dl_tif)
    assert dl_res["published"] is True
    assert dl_res["layer_name"] == "S2A_43SCA_20261117_0_L2A"
    assert dl_res["layer"] == "geoharvest:S2A_43SCA_20261117_0_L2A"
    assert dl_res["store"].startswith("gh_s2a_43sca_20261117_0_l2a_")
    assert dl_res["server_path"] == "/opt/geoserver_data/downloads/Ladakh/S2A_43SCA_20261117_0_L2A.tif"

    # When coverages.json is unavailable, fallback uses the server_path filename stem
    # (which includes the mirror hash prefix for custom destinations).
    custom_res = await manager.ingest(custom_tif)
    assert custom_res["published"] is True
    assert custom_res["layer_name"].endswith("_custom_scene")
    assert custom_res["layer"] == f"geoharvest:{custom_res['layer_name']}"


@pytest.mark.asyncio
async def test_sync_known_downloads_excludes_staging(tmp_path, db_session, monkeypatch):
    from backend.app.dependencies.config import settings
    from backend.app.models.models import Download, DownloadStatus, Job, JobStatus
    from backend.core import geoserver as gs_mod

    downloads_dir = tmp_path / "downloads"
    final_tif = downloads_dir / "proj" / "final_scene.tif"
    staging_tif = downloads_dir / ".staging" / "job_abc" / "band_b02.tif"
    final_tif.parent.mkdir(parents=True)
    staging_tif.parent.mkdir(parents=True)
    final_tif.write_bytes(b"final")
    staging_tif.write_bytes(b"staging")

    job_id = f"job_stage_{uuid.uuid4().hex[:8]}"
    dl_id = f"dl_stage_{uuid.uuid4().hex[:8]}"
    db_session.add(Job(id=job_id, type="harvest", status=JobStatus.RUNNING, progress=0.0))
    db_session.flush()
    db_session.add(
        Download(
            id=dl_id,
            job_id=job_id,
            destination=str(staging_tif),
            status=DownloadStatus.COMPLETED,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
    )
    db_session.commit()

    ingested_paths = []

    async def fake_status():
        return {"enabled": True, "available": True}

    async def fake_ingest(path):
        ingested_paths.append(Path(path).resolve())
        return {"published": True, "layer": f"geoharvest:{Path(path).stem}"}

    monkeypatch.setattr(settings, "geoserver_enabled", True)
    monkeypatch.setattr(settings, "downloads_dir", downloads_dir)
    monkeypatch.setattr(gs_mod.geoserver_manager, "status", fake_status)
    monkeypatch.setattr(gs_mod.geoserver_manager, "ingest", fake_ingest)

    try:
        await gs_mod.sync_known_downloads()
    finally:
        db_session.query(Download).filter(Download.id == dl_id).delete()
        db_session.query(Job).filter(Job.id == job_id).delete()
        db_session.commit()

    assert ingested_paths == [final_tif.resolve()]


@pytest.mark.asyncio
async def test_stacked_harvest_job_publishes_final_scene_not_staging_bands(
    db_session, tmp_path, fixtures_dir, monkeypatch
):
    from backend.app.dependencies.config import settings
    from backend.app.models.models import JobStatus
    from backend.app.schemas.schemas import AssetInfo, SearchResultItem
    from backend.core.jobs.engine import JobEngine

    fixture_tif = fixtures_dir / "rasters" / "sample_singleband_wgs84.tif"
    downloads_dir = tmp_path / "downloads"
    catalog_dir = tmp_path / "catalog"
    downloads_dir.mkdir()
    catalog_dir.mkdir()

    monkeypatch.setattr(settings, "geoserver_enabled", True)
    monkeypatch.setattr(settings, "downloads_dir", downloads_dir)
    monkeypatch.setattr(settings, "catalog_dir", catalog_dir)

    ingested_paths = []

    async def fake_ingest(path):
        resolved = Path(path).resolve()
        ingested_paths.append(resolved)
        return {
            "enabled": True,
            "stored": True,
            "published": True,
            "layer": f"geoharvest:{resolved.stem}",
            "layer_name": resolved.stem,
        }

    monkeypatch.setattr("backend.core.jobs.engine.geoserver_manager.ingest", fake_ingest)
    monkeypatch.setattr("backend.core.jobs.engine.catalog_engine.add_scene_to_catalog", lambda **kwargs: None)

    scene_id = f"S2A_TEST_{uuid.uuid4().hex[:6]}"
    scene = SearchResultItem(
        id=scene_id,
        provider_id="earth-search",
        collection="sentinel-2-l2a",
        title=scene_id,
        datetime="2026-11-17T05:30:00Z",
        bbox=[77.0, 34.0, 77.1, 34.1],
        geometry={
            "type": "Polygon",
            "coordinates": [[[77.0, 34.0], [77.1, 34.0], [77.1, 34.1], [77.0, 34.1], [77.0, 34.0]]],
        },
        assets={
            "red": AssetInfo(name="red", url="https://example.com/B04.tif", band="B04", mime_type="image/tiff"),
            "nir": AssetInfo(name="nir", url="https://example.com/B08.tif", band="B08", mime_type="image/tiff"),
        },
    )

    engine = JobEngine(max_workers=2)

    async def fake_download_file(url, destination_path, progress_callback=None, **kwargs):
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture_tif, destination_path)
        size = destination_path.stat().st_size
        if progress_callback:
            from backend.app.models.models import DownloadStatus

            progress_callback(size, size, 0.0, DownloadStatus.COMPLETED, None)
        return True

    monkeypatch.setattr(engine.download_engine, "download_file", fake_download_file)

    job = engine.create_harvest_job(
        name="GeoServer Stack Test",
        scenes=[scene],
        selected_bands=["red", "nir"],
        db=db_session,
        destination_dir=str(downloads_dir),
    )

    active_task = engine._active_tasks.get(job.id)
    if active_task is not None:
        await active_task
    else:
        await engine._run_job(job.id)
    db_session.expire_all()
    refreshed = db_session.query(type(job)).filter_by(id=job.id).first()
    assert refreshed.status == JobStatus.COMPLETED

    expected_final = Path(refreshed.job_metadata["scene_plans"][scene_id]["final_output_path"]).resolve()
    assert expected_final.is_file()
    assert ingested_paths == [expected_final]
    assert all(".staging" not in p.parts for p in ingested_paths)
    assert refreshed.job_metadata["scene_plans"][scene_id]["output_metadata"]["geoserver"]["layer"] == (
        f"geoharvest:{expected_final.stem}"
    )


@pytest.mark.asyncio
async def test_direct_scene_plan_publishes_after_reprojection_in_finalize_scene(
    db_session, tmp_path, fixtures_dir, monkeypatch
):
    from backend.app.dependencies.config import settings
    from backend.app.models.models import DownloadStatus, JobStatus
    from backend.app.schemas.schemas import AssetInfo, SearchResultItem
    from backend.core.jobs.engine import JobEngine

    utm_fixture = fixtures_dir / "rasters" / "sample_raster_utm43n.tif"
    downloads_dir = tmp_path / "downloads"
    catalog_dir = tmp_path / "catalog"
    downloads_dir.mkdir()
    catalog_dir.mkdir()

    monkeypatch.setattr(settings, "geoserver_enabled", True)
    monkeypatch.setattr(settings, "downloads_dir", downloads_dir)
    monkeypatch.setattr(settings, "catalog_dir", catalog_dir)

    observed_crs = []

    async def fake_ingest(path):
        import rasterio

        p = Path(path).resolve()
        with rasterio.open(p) as src:
            observed_crs.append((p, src.crs.to_string() if src.crs else None))
        return {
            "enabled": True,
            "stored": True,
            "published": True,
            "layer": f"geoharvest:{p.stem}",
            "layer_name": p.stem,
        }

    monkeypatch.setattr("backend.core.jobs.engine.geoserver_manager.ingest", fake_ingest)
    monkeypatch.setattr("backend.core.jobs.engine.catalog_engine.add_scene_to_catalog", lambda **kwargs: None)

    scene_id = f"SOI_DIRECT_{uuid.uuid4().hex[:6]}"
    scene = SearchResultItem(
        id=scene_id,
        provider_id="survey-of-india-toposheets",
        collection="survey-of-india-50k",
        title=scene_id,
        datetime="2024-01-01T00:00:00Z",
        bbox=[76.99, 33.99, 77.01, 34.01],
        geometry={"type": "Polygon", "coordinates": []},
        assets={
            "georef_tif": AssetInfo(
                name="georef_tif",
                url="https://example.com/sheet.tif",
                mime_type="image/tiff",
                band="georef",
            )
        },
    )

    engine = JobEngine(max_workers=1)

    async def fake_download_file(url, destination_path, progress_callback=None, **kwargs):
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(utm_fixture, destination_path)
        size = destination_path.stat().st_size
        if progress_callback:
            progress_callback(size, size, 0.0, DownloadStatus.COMPLETED, None)
        return True

    monkeypatch.setattr(engine.download_engine, "download_file", fake_download_file)

    job = engine.create_harvest_job(
        name="Direct Reproject Test",
        scenes=[scene],
        selected_bands=["all"],
        db=db_session,
        destination_dir=str(downloads_dir),
        is_toposheet=True,
    )
    active_task = engine._active_tasks.get(job.id)
    if active_task is not None:
        await active_task
    else:
        await engine._run_job(job.id)

    db_session.expire_all()
    refreshed = db_session.query(type(job)).filter_by(id=job.id).first()
    assert refreshed.status == JobStatus.COMPLETED
    assert len(observed_crs) == 1
    assert observed_crs[0][1] == "EPSG:4326"


def test_earthengine_export_publishes_local_filepath(client, tmp_path, monkeypatch):
    from backend.app.dependencies.config import settings

    exported_tif = tmp_path / "ee_s2_test.tif"
    exported_tif.write_bytes(b"II*\x00ee-tif")
    ingested = []

    async def fake_export_dataset(**kwargs):
        return {
            "dataset_id": kwargs["dataset_id"],
            "filename": exported_tif.name,
            "download_url": "https://earthengine.example/ee_s2_test.tif",
            "local_filepath": str(exported_tif),
            "destination_dir": str(tmp_path),
            "scale": 30.0,
            "crs": "EPSG:4326",
            "vis_mode": "true_color",
        }

    async def fake_ingest(path):
        ingested.append(Path(path))
        return {
            "enabled": True,
            "stored": True,
            "published": True,
            "layer": "geoharvest:ee_s2_test",
            "layer_name": "ee_s2_test",
        }

    monkeypatch.setattr(settings, "geoserver_enabled", True)
    monkeypatch.setattr("backend.app.api.earthengine.ee_service.export_dataset", fake_export_dataset)
    monkeypatch.setattr("backend.app.api.earthengine.geoserver_manager.ingest", fake_ingest)

    res = client.post(
        "/api/earthengine/export",
        json={
            "dataset_id": "COPERNICUS/S2_SR_HARMONIZED",
            "bbox": [77.0, 34.0, 77.2, 34.2],
            "destination_dir": str(tmp_path),
            "crs": "EPSG:4326",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert ingested == [exported_tif]
    assert body["geoserver"]["published"] is True
    assert body["geoserver"]["layer"] == "geoharvest:ee_s2_test"
