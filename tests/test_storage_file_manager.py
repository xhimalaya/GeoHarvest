import os
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import Job, Download
from backend.app.schemas.schemas import SearchResultItem, AssetInfo
from backend.core.jobs.engine import job_engine


def test_storage_destination_endpoints():
    client = TestClient(app)

    # 1. Get destination info
    res = client.get("/api/storage/destination")
    assert res.status_code == 200
    data = res.json()
    assert "default_directory" in data
    assert "active_directory" in data
    assert data["exists"] is True
    assert data["is_writable"] is True
    assert data["disk_free_bytes"] > 0

    # 2. Set custom destination
    test_custom_dir = settings.data_dir / "custom_test_downloads"
    set_res = client.post("/api/storage/destination", json={"directory": str(test_custom_dir)})
    assert set_res.status_code == 200
    set_data = set_res.json()
    assert set_data["is_custom"] is True
    assert set_data["active_directory"] == str(test_custom_dir.resolve())
    assert test_custom_dir.exists()

    # 3. Reset back to default
    reset_res = client.post("/api/storage/destination", json={"directory": ""})
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["is_custom"] is False

    # Clean up test directory
    if test_custom_dir.exists():
        shutil.rmtree(test_custom_dir)


def test_hierarchical_directory_structure():
    db = SessionLocal()
    custom_dir = settings.data_dir / "test_hierarchy_dl"
    custom_dir.mkdir(parents=True, exist_ok=True)

    try:
        sample_scene = SearchResultItem(
            id="S2A_MSIL2A_20240915T053201_R105_T43SFU",
            collection="sentinel-2-l2a",
            provider_id="aws-earthsearch",
            datetime="2024-09-15T05:32:01Z",
            cloud_cover=12.5,
            bbox=[77.0, 34.0, 78.0, 35.0],
            geometry={"type": "Polygon", "coordinates": [[[77, 34], [78, 34], [78, 35], [77, 35], [77, 34]]]},
            assets={
                "visual": AssetInfo(
                    name="visual",
                    url="https://example.com/visual.tif",
                    size_bytes=1024,
                    mime_type="image/tiff",
                    band="visual"
                )
            }
        )

        job = job_engine.create_harvest_job(
            name="Ladakh Glacier Cryo Task",
            scenes=[sample_scene],
            selected_bands=["visual"],
            db=db,
            destination_dir=str(custom_dir)
        )

        assert job.id.startswith("job_")
        assert job.job_metadata["task_name"] == "Ladakh_Glacier_Cryo_Task"
        assert job.job_metadata["destination_dir"] == str(custom_dir.resolve())

        # Check that download destination path matches: task_name > year > month > scene_name
        dls = db.query(Download).filter(Download.job_id == job.id).all()
        assert len(dls) == 1
        dl_dest = Path(dls[0].destination)

        # Expected path components
        assert dl_dest.parent.name == "S2A_MSIL2A_20240915T053201_R105_T43SFU"
        assert dl_dest.parent.parent.name == "09"  # Month
        assert dl_dest.parent.parent.parent.name == "2024"  # Year
        assert dl_dest.parent.parent.parent.parent.name == "Ladakh_Glacier_Cryo_Task"  # Task Name

        # Check that scene directory was actually created on disk
        assert dl_dest.parent.exists()

    finally:
        db.close()
        if custom_dir.exists():
            shutil.rmtree(custom_dir)


def test_file_explorer_and_security():
    client = TestClient(app)

    # 1. Path traversal security check
    res_traversal = client.get("/api/storage/files?path=../../etc")
    assert res_traversal.status_code in [403, 404]

    # 2. Browse files root
    res_root = client.get("/api/storage/files?path=&root=downloads")
    assert res_root.status_code == 200
    data = res_root.json()
    assert "breadcrumbs" in data
    assert "folders" in data
    assert "files" in data
    assert data["breadcrumbs"][0]["name"] == "Downloads"

    # 3. Create dummy file and test download & delete
    test_sub = settings.downloads_dir / "test_manager_dir"
    test_sub.mkdir(parents=True, exist_ok=True)
    test_file = test_sub / "sample_raster.tif"
    test_file.write_bytes(b"GEOTIFF_DUMMY_DATA_HEADER")

    try:
        # Browse the subfolder
        res_sub = client.get("/api/storage/files?path=test_manager_dir&root=downloads")
        assert res_sub.status_code == 200
        sub_data = res_sub.json()
        assert any(f["name"] == "sample_raster.tif" for f in sub_data["files"])

        # Test download
        dl_res = client.get("/api/storage/download?path=test_manager_dir/sample_raster.tif&root=downloads")
        assert dl_res.status_code == 200
        assert dl_res.content == b"GEOTIFF_DUMMY_DATA_HEADER"

        # Test search
        search_res = client.get("/api/storage/search?query=sample_raster&root=downloads")
        assert search_res.status_code == 200
        matches = search_res.json()
        assert len(matches) > 0
        assert matches[0]["name"] == "sample_raster.tif"

        # Test delete file
        del_res = client.delete("/api/storage/file?path=test_manager_dir/sample_raster.tif&root=downloads")
        assert del_res.status_code == 200
        assert not test_file.exists()

    finally:
        if test_sub.exists():
            shutil.rmtree(test_sub)


def test_directory_picker_endpoints():
    client = TestClient(app)

    # 1. Browse default directories
    res = client.get("/api/storage/directories")
    assert res.status_code == 200
    data = res.json()
    assert "current_path" in data
    assert "breadcrumbs" in data
    assert len(data["breadcrumbs"]) > 0
    assert "directories" in data
    assert "shortcuts" in data
    assert any(s["name"] == "GeoHarvest Default" for s in data["shortcuts"])
    assert any(s["name"] == "Home" for s in data["shortcuts"])
    assert data["is_writable"] is True
    assert data["free_bytes"] > 0

    # 2. Browse a specific folder
    test_parent = settings.data_dir / "picker_test_dir"
    test_parent.mkdir(parents=True, exist_ok=True)
    child_sub = test_parent / "alpha_subfolder"
    child_sub.mkdir(parents=True, exist_ok=True)

    try:
        browse_res = client.get(f"/api/storage/directories?path={test_parent.resolve()}")
        assert browse_res.status_code == 200
        browse_data = browse_res.json()
        assert browse_data["current_path"] == str(test_parent.resolve())
        assert any(d["name"] == "alpha_subfolder" for d in browse_data["directories"])

        # 3. Create a new directory via endpoint
        create_res = client.post("/api/storage/create-directory", json={
            "parent_path": str(test_parent.resolve()),
            "name": "beta_created_folder"
        })
        assert create_res.status_code == 200
        create_data = create_res.json()
        assert create_data["name"] == "beta_created_folder"
        assert (test_parent / "beta_created_folder").exists()
        assert (test_parent / "beta_created_folder").is_dir()

        # 4. Fail on duplicate creation
        dup_res = client.post("/api/storage/create-directory", json={
            "parent_path": str(test_parent.resolve()),
            "name": "beta_created_folder"
        })
        assert dup_res.status_code == 400

        # 5. Fail on invalid names
        bad_res = client.post("/api/storage/create-directory", json={
            "parent_path": str(test_parent.resolve()),
            "name": "../malicious"
        })
        assert bad_res.status_code == 400

    finally:
        if test_parent.exists():
            shutil.rmtree(test_parent)

