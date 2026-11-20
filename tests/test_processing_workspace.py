from io import BytesIO
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin


def _create_test_geotiff(path: Path, epsg: int = 4326, bands: int = 1) -> Path:
    """Create a minimal valid single/multi-band GeoTIFF on disk for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 16, 16
    data = np.ones((bands, height, width), dtype=np.uint16) * 500
    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": bands,
        "dtype": "uint16",
        "crs": f"EPSG:{epsg}",
        "transform": from_origin(77.5, 34.2, 0.001, 0.001),
    }
    with rasterio.open(str(path), "w", **meta) as dst:
        dst.write(data)
    return path


@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    """Build an isolated data/downloads, data/processed, data/custom, and external folder layout."""
    from backend.app.dependencies.config import settings
    import backend.app.api.storage as storage_mod

    data_dir = tmp_path / "data"
    downloads_dir = data_dir / "downloads"
    processed_dir = data_dir / "processed"
    custom_dir = data_dir / "custom"
    external_dir = tmp_path / "external_custom_data"

    downloads_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    custom_dir.mkdir(parents=True, exist_ok=True)
    external_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "downloads_dir", downloads_dir)
    monkeypatch.setattr(storage_mod, "get_active_download_dir", lambda: downloads_dir)
    monkeypatch.setattr(
        storage_mod,
        "get_allowed_roots",
        lambda: {
            "downloads": downloads_dir,
            "default_downloads": downloads_dir,
            "processed": processed_dir,
            "data": data_dir,
        },
    )

    # Downloaded nested folders + root file
    _create_test_geotiff(downloads_dir / "root_export.tif")
    _create_test_geotiff(
        downloads_dir / "Ladakh_Cryo_S2" / "2026" / "10" / "S2B_43SGU_20261028" / "green.tif",
        epsg=32643,
    )
    _create_test_geotiff(
        downloads_dir / "Ladakh_Cryo_S2" / "2026" / "10" / "S2C_43SET_20261003" / "swir1.tif",
        epsg=32643,
    )
    _create_test_geotiff(downloads_dir / "Bhuvan_DEM" / "2024" / "01" / "tile_01" / "dem.tif")
    # Processed and custom workspace rasters
    _create_test_geotiff(processed_dir / "ndsi_oct_2026.tif", epsg=32643)
    _create_test_geotiff(custom_dir / "existing_custom.tif", bands=3)
    # External custom directory outside managed data_dir
    _create_test_geotiff(external_dir / "field_survey_rgb.tif", bands=3)
    _create_test_geotiff(external_dir / "nested" / "sub_band.tif")

    return {
        "data_dir": data_dir,
        "downloads_dir": downloads_dir,
        "processed_dir": processed_dir,
        "custom_dir": custom_dir,
        "external_dir": external_dir,
    }


def test_list_local_rasters_default_all_roots(client, isolated_workspace):
    res = client.get("/api/processing/local-rasters")
    assert res.status_code == 200
    items = res.json()
    names = {item["name"] for item in items}

    assert {
        "root_export.tif",
        "green.tif",
        "swir1.tif",
        "dem.tif",
        "ndsi_oct_2026.tif",
        "existing_custom.tif",
    }.issubset(names)
    assert "field_survey_rgb.tif" not in names

    custom_item = next(i for i in items if i["name"] == "existing_custom.tif")
    assert custom_item["bands"] == 3
    assert custom_item["storage_root"] == "data"
    assert custom_item["storage_rel_path"] == "custom/existing_custom.tif"


def test_list_local_folders_discovers_downloaded_hierarchy(client, isolated_workspace):
    res = client.get("/api/processing/local-folders")
    assert res.status_code == 200
    payload = res.json()

    assert payload["active_download_dir"] == str(isolated_workspace["downloads_dir"].resolve())
    labels = {f["label"]: f for f in payload["folders"]}

    assert "Ladakh_Cryo_S2" in labels
    assert labels["Ladakh_Cryo_S2"]["file_count"] == 2
    # Grouping folder (2026/10 has 2 child scene dirs) is surfaced for batch filtering
    assert "Ladakh_Cryo_S2/2026/10" in labels
    assert labels["Ladakh_Cryo_S2/2026/10"]["file_count"] == 2
    assert "Ladakh_Cryo_S2/2026/10/S2B_43SGU_20261028" in labels
    assert labels["Ladakh_Cryo_S2/2026/10/S2B_43SGU_20261028"]["direct_file_count"] == 1
    assert "Bhuvan_DEM" in labels
    assert labels["Bhuvan_DEM"]["file_count"] == 1


def test_filter_local_rasters_by_downloaded_folder_and_recursive_flag(client, isolated_workspace):
    ladakh_oct_dir = isolated_workspace["downloads_dir"] / "Ladakh_Cryo_S2" / "2026" / "10"

    res_rec = client.get(
        "/api/processing/local-rasters",
        params={"directory": str(ladakh_oct_dir), "recursive": "true"},
    )
    assert res_rec.status_code == 200
    names_rec = {item["name"] for item in res_rec.json()}
    assert names_rec == {"green.tif", "swir1.tif"}

    # Storage mapping must stay valid relative to the downloads root for download buttons
    green = next(item for item in res_rec.json() if item["name"] == "green.tif")
    assert green["storage_root"] == "downloads"
    assert green["storage_rel_path"] == "Ladakh_Cryo_S2/2026/10/S2B_43SGU_20261028/green.tif"
    assert green["crs"] == "EPSG:32643"

    # Non-recursive on downloads root returns only direct root files
    res_flat = client.get(
        "/api/processing/local-rasters",
        params={"directory": str(isolated_workspace["downloads_dir"]), "recursive": "false"},
    )
    assert res_flat.status_code == 200
    assert {item["name"] for item in res_flat.json()} == {"root_export.tif"}


def test_filter_local_rasters_custom_external_directory_and_errors(client, isolated_workspace):
    ext_dir = isolated_workspace["external_dir"]
    res = client.get("/api/processing/local-rasters", params={"directory": str(ext_dir)})
    assert res.status_code == 200
    items = res.json()
    assert {item["name"] for item in items} == {"field_survey_rgb.tif", "sub_band.tif"}
    # External paths outside managed roots intentionally have null storage_root
    assert items[0]["storage_root"] is None

    res_missing = client.get("/api/processing/local-rasters", params={"directory": str(ext_dir / "missing")})
    assert res_missing.status_code == 404

    res_file = client.get(
        "/api/processing/local-rasters",
        params={"directory": str(ext_dir / "field_survey_rgb.tif")},
    )
    assert res_file.status_code == 400


def test_upload_custom_raster_validation_and_persistence(client, isolated_workspace, tmp_path):
    src_tif = _create_test_geotiff(tmp_path / "user_custom_scene.tif", epsg=32644, bands=2)

    with open(src_tif, "rb") as fh:
        res = client.post(
            "/api/processing/upload-raster",
            files={"file": ("user_custom_scene.tif", fh, "image/tiff")},
        )
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "uploaded"
    assert payload["raster"]["name"] == "user_custom_scene.tif"
    assert payload["raster"]["bands"] == 2
    assert payload["raster"]["crs"] == "EPSG:4326"
    assert payload["raster"]["storage_root"] == "data"
    assert Path(payload["raster"]["absolute_path"]).exists()

    # Uploading a file with invalid extension returns 400 cleanly
    bad_ext = client.post(
        "/api/processing/upload-raster",
        files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert bad_ext.status_code == 400

    # Uploading corrupt bytes disguised as .tif returns 400 and cleans up partial file
    bad_tif = client.post(
        "/api/processing/upload-raster",
        files={"file": ("broken_custom.tif", BytesIO(b"not a geotiff"), "image/tiff")},
    )
    assert bad_tif.status_code == 400
    assert not (isolated_workspace["custom_dir"] / "broken_custom.tif").exists()


@pytest.mark.asyncio
async def test_execute_recipe_on_folder_processes_all_tiffs_and_ndsi(isolated_workspace, db_session):
    import asyncio
    import uuid
    import httpx
    from backend.app.main import app
    from backend.app.models.models import Dataset, Asset, ProcessingTask, Job, AssetLineage

    scene_dir = isolated_workspace["downloads_dir"] / "Oct_2026_Cryo" / "Scene_A"
    _create_test_geotiff(scene_dir / "Scene_A_green.tif", epsg=4326)
    _create_test_geotiff(scene_dir / "Scene_A_swir16.tif", epsg=4326)
    _create_test_geotiff(scene_dir / "Scene_A_nir.tif", epsg=4326)

    aoi = {
        "type": "Polygon",
        "coordinates": [[[77.502, 34.186], [77.514, 34.186], [77.514, 34.198], [77.502, 34.198], [77.502, 34.186]]],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        # 1. Execute s2-aoi-cog across entire scene folder (processes all 3 TIFFs)
        res_cog = await async_client.post(
            "/api/processing/execute",
            json={
                "directory": str(scene_dir),
                "recipe_id": "s2-aoi-cog",
                "aoi_geometry": aoi,
                "clip_to_aoi": True,
                "target_crs": "EPSG:32643",
            },
        )
        assert res_cog.status_code == 200
        cog_payload = res_cog.json()
        assert cog_payload["input_count"] == 3

        task_id = cog_payload["task_id"]
        cog_task = None
        for _ in range(80):
            await asyncio.sleep(0.15)
            st = (await async_client.get(f"/api/processing/tasks/{task_id}")).json()
            cog_task = st
            if st["status"] in {"completed", "failed"}:
                break

        assert cog_task is not None and cog_task["status"] == "completed", cog_task
        assert len(cog_task["output_assets"]) == 3
        for out_p in cog_task["output_assets"]:
            assert Path(out_p).exists()

        # 2. Execute glacier-snow-ndsi across the scene folder (auto-pairs green + swir16)
        res_ndsi = await async_client.post(
            "/api/processing/execute",
            json={
                "directory": str(scene_dir),
                "recipe_id": "glacier-snow-ndsi",
                "aoi_geometry": aoi,
                "clip_to_aoi": True,
                "target_crs": "EPSG:32643",
            },
        )
        assert res_ndsi.status_code == 200
        ndsi_task_id = res_ndsi.json()["task_id"]
        ndsi_task = None
        for _ in range(80):
            await asyncio.sleep(0.15)
            st = (await async_client.get(f"/api/processing/tasks/{ndsi_task_id}")).json()
            ndsi_task = st
            if st["status"] in {"completed", "failed"}:
                break

        assert ndsi_task is not None and ndsi_task["status"] == "completed", ndsi_task
        assert len(ndsi_task["output_assets"]) == 1
        assert "ndsi" in Path(ndsi_task["output_assets"][0]).name.lower()
        assert Path(ndsi_task["output_assets"][0]).exists()

        # 3. Verify catalog asset mode (input_asset_ids) resolves DB local_path cleanly
        ds_id = f"ds_test_{uuid.uuid4().hex[:6]}"
        ast1_id = f"ast_1_{uuid.uuid4().hex[:6]}"
        ast2_id = f"ast_2_{uuid.uuid4().hex[:6]}"
        db_session.add(Dataset(id=ds_id, collection="sentinel-2-l2a", dataset_id=ds_id))
        db_session.flush()
        db_session.add(Asset(id=ast1_id, dataset_id=ds_id, asset_name="green", url="http://example.com/g.tif", local_path=str((scene_dir / "Scene_A_green.tif").resolve())))
        db_session.add(Asset(id=ast2_id, dataset_id=ds_id, asset_name="nir", url="http://example.com/n.tif", local_path=str((scene_dir / "Scene_A_nir.tif").resolve())))
        db_session.commit()

        res_cat = await async_client.post(
            "/api/processing/execute",
            json={
                "input_asset_ids": [ast1_id, ast2_id],
                "recipe_id": "s2-aoi-cog",
                "clip_to_aoi": False,
                "target_crs": "EPSG:4326",
            },
        )
        assert res_cat.status_code == 200
        assert res_cat.json()["input_count"] == 2
        cat_task_id = res_cat.json()["task_id"]
        cat_task = None
        for _ in range(80):
            await asyncio.sleep(0.15)
            st = (await async_client.get(f"/api/processing/tasks/{cat_task_id}")).json()
            cat_task = st
            if st["status"] in {"completed", "failed"}:
                break
        assert cat_task is not None and cat_task["status"] == "completed", cat_task
        assert len(cat_task["output_assets"]) == 2

    # Clean up DB rows created by tests
    db_session.expire_all()
    for tid in (task_id, ndsi_task_id, cat_task_id):
        t = db_session.query(ProcessingTask).filter(ProcessingTask.id == tid).first()
        if t:
            job_id = t.job_id
            db_session.delete(t)
            j = db_session.query(Job).filter(Job.id == job_id).first()
            if j:
                db_session.delete(j)
    db_session.query(AssetLineage).filter(AssetLineage.source_asset_id.in_([ast1_id, ast2_id])).delete(synchronize_session=False)
    db_session.query(Asset).filter(Asset.dataset_id.in_([ds_id, f"dataset_{task_id}", f"dataset_{ndsi_task_id}", f"dataset_{cat_task_id}"])).delete(synchronize_session=False)
    db_session.query(Dataset).filter(Dataset.id.in_([ds_id, f"dataset_{task_id}", f"dataset_{ndsi_task_id}", f"dataset_{cat_task_id}"])).delete(synchronize_session=False)
    db_session.commit()
