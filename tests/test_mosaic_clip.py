import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pathlib import Path
from backend.core.processing.raster_ops import RasterOps
from backend.app.models.models import Job, Download, JobStatus, DownloadStatus


@pytest.fixture
def two_adjacent_rasters(tmp_path):
    # Tile 1: 77.0 to 77.1 Lon, 34.0 to 34.1 Lat
    tile1 = tmp_path / "tile_west.tif"
    width, height = 50, 50
    transform1 = from_origin(77.0, 34.1, 0.002, 0.002)
    data1 = (np.ones((height, width)) * 100).astype(np.uint16)
    meta1 = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint16",
        "crs": "EPSG:4326",
        "transform": transform1,
        "nodata": 0
    }
    with rasterio.open(str(tile1), "w", **meta1) as dst:
        dst.write(data1, 1)

    # Tile 2: 77.1 to 77.2 Lon, 34.0 to 34.1 Lat (Adjacent East)
    tile2 = tmp_path / "tile_east.tif"
    transform2 = from_origin(77.1, 34.1, 0.002, 0.002)
    data2 = (np.ones((height, width)) * 200).astype(np.uint16)
    meta2 = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint16",
        "crs": "EPSG:4326",
        "transform": transform2,
        "nodata": 0
    }
    with rasterio.open(str(tile2), "w", **meta2) as dst:
        dst.write(data2, 1)

    return str(tile1), str(tile2)


def test_mosaic_rasters_basic(two_adjacent_rasters, tmp_path):
    tile1, tile2 = two_adjacent_rasters
    out_mosaic = str(tmp_path / "mosaic_basic.tif")

    res_path = RasterOps.mosaic_rasters([tile1, tile2], out_mosaic, to_cog=True)
    assert Path(res_path).exists()
    assert res_path == str(Path(out_mosaic).resolve())

    # Validate output with RasterOps
    val = RasterOps.validate_raster(res_path)
    assert val["valid"] is True
    assert val["width"] >= 95
    assert val["height"] == 50
    assert val["count"] == 1


def test_mosaic_and_clip_to_geojson(two_adjacent_rasters, tmp_path):
    tile1, tile2 = two_adjacent_rasters
    out_clipped = str(tmp_path / "mosaic_clipped.tif")

    # GeoJSON Polygon straddling both tiles: lon 77.05 to 77.15, lat 34.02 to 34.08
    aoi_geom = {
        "type": "Polygon",
        "coordinates": [[[77.05, 34.02], [77.15, 34.02], [77.15, 34.08], [77.05, 34.08], [77.05, 34.02]]]
    }

    res_path = RasterOps.mosaic_rasters([tile1, tile2], out_clipped, aoi_geometry=aoi_geom, to_cog=False)
    assert Path(res_path).exists()

    val = RasterOps.validate_raster(res_path)
    assert val["valid"] is True
    assert val["width"] < 95
    assert val["height"] < 50

    # Also test with FeatureCollection
    fc_geom = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": aoi_geom,
                "properties": {}
            }
        ]
    }
    out_fc_clipped = str(tmp_path / "mosaic_fc_clipped.tif")
    res_fc = RasterOps.mosaic_rasters([tile1, tile2], out_fc_clipped, aoi_geometry=fc_geom, to_cog=False)
    assert Path(res_fc).exists()
    val_fc = RasterOps.validate_raster(res_fc)
    assert val_fc["valid"] is True


import uuid

def test_mosaic_options_and_execute_job_api(client, db_session, two_adjacent_rasters, tmp_path):
    tile1, tile2 = two_adjacent_rasters
    job_id = f"job_mosaic_{uuid.uuid4().hex[:8]}"

    # Create satellite harvest job
    job = Job(
        id=job_id,
        type="harvest",
        status=JobStatus.COMPLETED,
        progress=100.0,
        job_metadata={
            "name": "Sentinel-2 Ladakh Test",
            "task_name": "sentinel_test",
            "is_toposheet": False,
            "aoi": {
                "type": "Polygon",
                "coordinates": [[[77.05, 34.02], [77.15, 34.02], [77.15, 34.08], [77.05, 34.08], [77.05, 34.02]]]
            },
            "destination_dir": str(tmp_path)
        }
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    dl1 = Download(
        id=f"dl_{uuid.uuid4().hex[:8]}",
        job_id=job.id,
        destination=tile1,
        status=DownloadStatus.COMPLETED,
        total_bytes=Path(tile1).stat().st_size,
        downloaded_bytes=Path(tile1).stat().st_size
    )
    dl2 = Download(
        id=f"dl_{uuid.uuid4().hex[:8]}",
        job_id=job.id,
        destination=tile2,
        status=DownloadStatus.COMPLETED,
        total_bytes=Path(tile2).stat().st_size,
        downloaded_bytes=Path(tile2).stat().st_size
    )
    db_session.add_all([dl1, dl2])
    db_session.commit()

    # 1. Test GET /api/processing/jobs/{job.id}/mosaic-options
    resp = client.get(f"/api/processing/jobs/{job.id}/mosaic-options")
    assert resp.status_code == 200
    options = resp.json()
    assert options["eligible"] is True
    assert options["is_toposheet"] is False
    assert len(options["raster_assets"]) == 2
    assert options["aoi_geometry"] is not None

    # 2. Test POST /api/processing/jobs/{job.id}/mosaic-clip
    out_job_mosaic = str(tmp_path / "job_mosaic_out.tif")
    post_resp = client.post(
        f"/api/processing/jobs/{job.id}/mosaic-clip",
        json={
            "selected_download_ids": [dl1.id, dl2.id],
            "aoi_geometry": options["aoi_geometry"],
            "target_crs": "EPSG:4326",
            "to_cog": True,
            "output_path": out_job_mosaic
        }
    )
    assert post_resp.status_code == 200
    clip_result = post_resp.json()
    assert clip_result["status"] == "queued"
    assert clip_result["input_files_count"] == 2
    assert clip_result["task_id"].startswith("proc_mos_")

    # 3. Verify pipeline_runner execution directly
    import asyncio
    from backend.core.processing.pipeline import pipeline_runner
    exec_res = asyncio.run(
        pipeline_runner.run_mosaic_clip_task(
            task_id=clip_result["task_id"],
            input_file_paths=[tile1, tile2],
            output_path=out_job_mosaic,
            aoi_geometry=options["aoi_geometry"],
            target_crs="EPSG:4326",
            to_cog=True
        )
    )
    assert exec_res is True
    assert Path(out_job_mosaic).exists()
    val = RasterOps.validate_raster(out_job_mosaic)
    assert val["valid"] is True


def test_toposheet_strictly_excluded_from_mosaic(client, db_session, tmp_path):
    # Dummy TopoSheet PDF
    dummy_pdf = tmp_path / "soi_52G14.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 mock toposheet content")

    toposheet_job = Job(
        id=f"job_toposheet_{uuid.uuid4().hex[:8]}",
        type="harvest",
        status=JobStatus.COMPLETED,
        progress=100.0,
        job_metadata={
            "name": "Survey of India TopoSheet 52G/14",
            "task_name": "toposheet_52G14",
            "is_toposheet": True,
            "provider_id": "survey-of-india",
            "destination_dir": str(tmp_path)
        }
    )
    db_session.add(toposheet_job)
    db_session.commit()
    db_session.refresh(toposheet_job)

    dl = Download(
        id=f"dl_topo_{uuid.uuid4().hex[:8]}",
        job_id=toposheet_job.id,
        destination=str(dummy_pdf),
        status=DownloadStatus.COMPLETED,
        total_bytes=dummy_pdf.stat().st_size,
        downloaded_bytes=dummy_pdf.stat().st_size
    )
    db_session.add(dl)
    db_session.commit()

    # 1. Test GET mosaic-options returns eligible=False, is_toposheet=True
    resp = client.get(f"/api/processing/jobs/{toposheet_job.id}/mosaic-options")
    assert resp.status_code == 200
    data = resp.json()
    assert data["eligible"] is False
    assert data["is_toposheet"] is True
    assert "TopoSheet" in data["reason"]

    # 2. Test POST mosaic-clip on TopoSheet job is strictly rejected with 400
    post_resp = client.post(
        f"/api/processing/jobs/{toposheet_job.id}/mosaic-clip",
        json={
            "to_cog": True
        }
    )
    assert post_resp.status_code == 400
    err_body = post_resp.json()
    assert "TopoSheet" in err_body["detail"]


def test_mosaic_clip_rejects_pdf_and_non_rasters(client, tmp_path):
    pdf_file = tmp_path / "document.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    resp = client.post(
        "/api/processing/mosaic-clip",
        json={
            "input_file_paths": [str(pdf_file)],
            "to_cog": True
        }
    )
    assert resp.status_code == 400
    assert "PDF files cannot be mosaicked" in resp.json()["detail"]
