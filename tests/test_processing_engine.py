import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pathlib import Path
from backend.core.processing.raster_ops import RasterOps
from backend.core.processing.pipeline import pipeline_runner
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import ProcessingTask, Asset, AssetLineage


@pytest.fixture
def sample_raster_path(tmp_path):
    # Create a small synthetic GeoTIFF (50x50 pixels) in EPSG:4326 over Ladakh (77.5 to 77.6 lon, 34.1 to 34.2 lat)
    file_path = tmp_path / "sample_band.tif"
    width, height = 50, 50
    transform = from_origin(77.5, 34.2, 0.002, 0.002)

    data = (np.random.rand(height, width) * 10000).astype(np.uint16)
    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint16",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": 0
    }

    with rasterio.open(str(file_path), "w", **meta) as dst:
        dst.write(data, 1)

    return str(file_path.resolve())


def test_raster_validate(sample_raster_path):
    res = RasterOps.validate_raster(sample_raster_path)
    assert res["valid"] is True
    assert res["width"] == 50
    assert res["height"] == 50
    assert res["crs"] == "EPSG:4326"


def test_raster_clip(sample_raster_path, tmp_path):
    aoi_geom = {
        "type": "Polygon",
        "coordinates": [[[77.52, 34.12], [77.58, 34.12], [77.58, 34.18], [77.52, 34.18], [77.52, 34.12]]]
    }
    clipped_path = str(tmp_path / "clipped.tif")
    out = RasterOps.clip_raster(sample_raster_path, aoi_geom, clipped_path)

    assert Path(out).exists()
    val = RasterOps.validate_raster(out)
    assert val["valid"] is True
    assert val["width"] < 50
    assert val["height"] < 50


def test_raster_reproject(sample_raster_path, tmp_path):
    reproj_path = str(tmp_path / "reprojected_utm.tif")
    # Reproject to UTM Zone 43N
    out = RasterOps.reproject_raster(sample_raster_path, "EPSG:32643", reproj_path)

    assert Path(out).exists()
    val = RasterOps.validate_raster(out)
    assert val["valid"] is True
    assert "32643" in val["crs"]


def test_raster_cog(sample_raster_path, tmp_path):
    cog_path = str(tmp_path / "output_cog.tif")
    out = RasterOps.build_cog(sample_raster_path, cog_path, tile_size=256)

    assert Path(out).exists()
    val = RasterOps.validate_raster(out)
    assert val["valid"] is True
    assert val["is_tiled"] is True
    assert len(val["overviews"]) > 0


@pytest.mark.asyncio
async def test_processing_pipeline_and_lineage(sample_raster_path, tmp_path):
    import uuid
    uid = uuid.uuid4().hex[:6]
    db = SessionLocal()
    task_id = f"task_test_proc_{uid}"
    dataset_id = f"scene_test_{uid}"
    source_asset_id = f"asset_raw_b04_{uid}"
    job_id = f"job_proc_{uid}"

    from backend.app.models.models import Dataset, Job, JobStatus

    # Ensure dataset and job exist for foreign key
    ds = Dataset(
        id=dataset_id,
        collection="sentinel-2-l2a",
        dataset_id=dataset_id
    )
    db.add(ds)
    db.flush()

    job_rec = Job(id=job_id, type="processing", status=JobStatus.RUNNING)
    db.add(job_rec)
    db.flush()

    # Register raw source asset
    src_asset = Asset(
        id=source_asset_id,
        dataset_id=dataset_id,
        asset_name="B04",
        url=sample_raster_path,
        local_path=sample_raster_path,
        asset_type="local_raw",
        status="downloaded"
    )
    db.add(src_asset)

    task = ProcessingTask(
        id=task_id,
        job_id=job_id,
        task_type="s2-aoi-cog",
        input_assets=[sample_raster_path],
        parameters={},
        status="pending",
        checkpoint={"completed_steps": [], "intermediate_files": {}}
    )
    db.add(task)
    db.commit()

    aoi_geom = {
        "type": "Polygon",
        "coordinates": [[[77.51, 34.11], [77.59, 34.11], [77.59, 34.19], [77.51, 34.19], [77.51, 34.11]]]
    }

    success = await pipeline_runner.run_task(
        task_id=task_id,
        input_file_path=sample_raster_path,
        recipe_id="s2-aoi-cog",
        aoi_geometry=aoi_geom,
        target_crs="EPSG:32643"
    )

    assert success is True

    # Check updated task and lineage in database
    db.expire_all()
    updated_task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
    assert updated_task.status == "completed"
    assert updated_task.progress == 100.0
    assert "cog" in updated_task.checkpoint["completed_steps"]

    # Verify AssetLineage record was created
    lineage = db.query(AssetLineage).filter(AssetLineage.source_asset_id == source_asset_id).first()
    assert lineage is not None
    assert lineage.recipe_id == "s2-aoi-cog"
    assert lineage.derived_asset_id is not None

    derived = db.query(Asset).filter(Asset.id == lineage.derived_asset_id).first()
    assert derived is not None
    assert derived.asset_type == "local_processed"
    assert Path(derived.local_path).exists()

    # Cleanup
    db.delete(lineage)
    db.commit()
    db.delete(derived)
    db.commit()
    db.delete(updated_task)
    db.delete(src_asset)
    db.delete(ds)
    db.delete(job_rec)
    db.commit()
    db.close()
