import asyncio
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.app.dependencies.database import get_db
from backend.app.models.models import ProcessingTask, Asset, AssetLineage
from backend.core.processing.recipes import recipe_registry
from backend.core.processing.pipeline import pipeline_runner
from backend.core.processing.raster_ops import RasterOps
from backend.core.processing.executor import GeoProcessExecutor

router = APIRouter(prefix="/api/processing", tags=["processing"])


class ExecuteProcessingRequest(BaseModel):
    input_file_path: str
    recipe_id: str = "s2-aoi-cog"
    aoi_geometry: Dict[str, Any]
    target_crs: Optional[str] = "auto_utm"
    job_id: Optional[str] = None


@router.get("/recipes")
async def list_recipes():
    return recipe_registry.list_recipes()


@router.post("/execute")
async def execute_recipe(request: ExecuteProcessingRequest, db: Session = Depends(get_db)):
    task_id = f"proc_{uuid.uuid4().hex[:12]}"
    job_id = request.job_id or f"job_proc_{uuid.uuid4().hex[:8]}"

    from backend.app.models.models import Job, JobStatus
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        job = Job(id=job_id, type="processing", status=JobStatus.RUNNING)
        db.add(job)
        db.flush()

    task = ProcessingTask(
        id=task_id,
        job_id=job_id,
        task_type=request.recipe_id,
        input_assets=[request.input_file_path],
        parameters={
            "recipe_id": request.recipe_id,
            "target_crs": request.target_crs,
        },
        status="queued",
        progress=0.0,
        checkpoint={"completed_steps": [], "intermediate_files": {}}
    )
    db.add(task)
    db.commit()

    # Launch in asyncio background task
    asyncio.create_task(
        pipeline_runner.run_task(
            task_id=task_id,
            input_file_path=request.input_file_path,
            recipe_id=request.recipe_id,
            aoi_geometry=request.aoi_geometry,
            target_crs=request.target_crs
        )
    )

    return {
        "status": "queued",
        "task_id": task_id,
        "job_id": job_id,
        "recipe_id": request.recipe_id
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Processing task not found")

    return {
        "id": task.id,
        "job_id": task.job_id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error": task.error,
        "checkpoint": task.checkpoint,
        "input_assets": task.input_assets,
        "output_assets": task.output_assets
    }


@router.get("/lineage/{asset_id}")
async def get_asset_lineage(asset_id: str, db: Session = Depends(get_db)):
    lineage_records = db.query(AssetLineage).filter(
        (AssetLineage.source_asset_id == asset_id) | (AssetLineage.derived_asset_id == asset_id)
    ).all()

    results = []
    for r in lineage_records:
        src = db.query(Asset).filter(Asset.id == r.source_asset_id).first()
        der = db.query(Asset).filter(Asset.id == r.derived_asset_id).first()
        results.append({
            "id": r.id,
            "operation": r.operation,
            "recipe_id": r.recipe_id,
            "created_at": r.created_at,
            "source": {
                "id": src.id if src else r.source_asset_id,
                "name": src.asset_name if src else None,
                "type": src.asset_type if src else None,
                "path": src.local_path or src.url if src else None
            },
            "derived": {
                "id": der.id if der else r.derived_asset_id,
                "name": der.asset_name if der else None,
                "type": der.asset_type if der else None,
                "path": der.local_path or der.url if der else None
            }
        })

    return results


class MosaicClipRequest(BaseModel):
    input_file_paths: List[str]
    output_path: Optional[str] = None
    aoi_geometry: Optional[Dict[str, Any]] = None
    target_crs: Optional[str] = "auto_utm"
    nodata: Optional[float] = 0.0
    to_cog: bool = True
    job_id: Optional[str] = None


class JobMosaicClipRequest(BaseModel):
    selected_download_ids: Optional[List[str]] = None
    band: Optional[str] = None
    aoi_geometry: Optional[Dict[str, Any]] = None
    target_crs: Optional[str] = "auto_utm"
    nodata: Optional[float] = 0.0
    to_cog: bool = True
    output_path: Optional[str] = None


def _is_toposheet_job(job: Any) -> bool:
    if not job:
        return False
    meta = job.job_metadata or {}
    if meta.get("is_toposheet") is True:
        return True
    if "topo" in (meta.get("name") or "").lower():
        return True
    if meta.get("provider_id") == "survey-of-india":
        return True
    return False


@router.get("/jobs/{job_id}/mosaic-options")
async def get_job_mosaic_options(job_id: str, db: Session = Depends(get_db)):
    from backend.app.models.models import Job, Download, DownloadStatus
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if _is_toposheet_job(job):
        return {
            "eligible": False,
            "reason": "Mosaic & Clip is not supported for TopoSheet map sheets. Supported on satellite and elevation rasters.",
            "is_toposheet": True,
            "raster_assets": [],
            "available_bands": [],
            "aoi_geometry": None
        }

    dls = db.query(Download).filter(Download.job_id == job_id, Download.status == DownloadStatus.COMPLETED).all()
    valid_exts = {".tif", ".tiff", ".jp2", ".img", ".vrt"}
    raster_dls = []
    bands_found = set()

    for d in dls:
        if d.destination:
            p = Path(d.destination)
            if p.suffix.lower() in valid_exts and p.exists() and p.stat().st_size > 0:
                band_name = None
                # Check if asset has band or filename has band
                if d.asset:
                    band_name = d.asset.band
                if not band_name:
                    stem_parts = p.stem.split("_")
                    band_name = stem_parts[-1] if len(stem_parts) > 1 else "raster"
                bands_found.add(band_name)

                raster_dls.append({
                    "id": d.id,
                    "asset_name": d.asset.asset_name if d.asset else p.name,
                    "destination": str(p.resolve()),
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                    "band": band_name
                })

    if not raster_dls:
        return {
            "eligible": False,
            "reason": "No completed raster files found on disk for this job.",
            "is_toposheet": False,
            "raster_assets": [],
            "available_bands": [],
            "aoi_geometry": None
        }

    meta = job.job_metadata or {}
    aoi = meta.get("aoi")
    dest_dir = Path(meta.get("destination_dir") or "/home/himalaya/Desktop/divakar/test/processed")
    suggested_output = str((dest_dir / f"{job.id}_mosaic.tif").resolve())

    return {
        "eligible": True,
        "reason": None,
        "is_toposheet": False,
        "raster_assets": raster_dls,
        "available_bands": sorted(list(bands_found)),
        "aoi_geometry": aoi,
        "suggested_output_path": suggested_output
    }


@router.post("/jobs/{job_id}/mosaic-clip")
async def execute_job_mosaic_clip(
    job_id: str,
    request: JobMosaicClipRequest,
    db: Session = Depends(get_db)
):
    from backend.app.models.models import Job, Download, DownloadStatus, JobStatus
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if _is_toposheet_job(job):
        raise HTTPException(
            status_code=400,
            detail="Mosaic & Clip operation is not supported for TopoSheet documents. Supported on satellite and elevation rasters."
        )

    dls = db.query(Download).filter(Download.job_id == job_id, Download.status == DownloadStatus.COMPLETED).all()
    valid_exts = {".tif", ".tiff", ".jp2", ".img", ".vrt"}

    selected_dls = []
    for d in dls:
        if d.destination:
            p = Path(d.destination)
            if p.suffix.lower() in valid_exts and p.exists() and p.stat().st_size > 0:
                if request.selected_download_ids and d.id not in request.selected_download_ids:
                    continue
                if request.band:
                    # Filter by band
                    b_name = d.asset.band if d.asset else p.stem.split("_")[-1]
                    if b_name.lower() != request.band.lower():
                        continue
                selected_dls.append(d)

    if not selected_dls:
        raise HTTPException(status_code=400, detail="No matching completed raster files found for mosaicking.")

    input_paths = [str(Path(d.destination).resolve()) for d in selected_dls]

    meta = job.job_metadata or {}
    aoi_geom = request.aoi_geometry or meta.get("aoi")

    dest_dir = Path(meta.get("destination_dir") or "/home/himalaya/Desktop/divakar/test/processed")
    dest_dir.mkdir(parents=True, exist_ok=True)
    band_suffix = f"_{request.band.lower()}" if request.band else ""
    out_path = request.output_path or str((dest_dir / f"{job.id}{band_suffix}_mosaic.tif").resolve())

    task_id = f"proc_mos_{uuid.uuid4().hex[:8]}"
    proc_job_id = f"job_mosaic_{uuid.uuid4().hex[:8]}"

    proc_job = Job(id=proc_job_id, type="processing", status=JobStatus.RUNNING)
    db.add(proc_job)
    db.flush()

    task = ProcessingTask(
        id=task_id,
        job_id=proc_job_id,
        task_type="mosaic-clip-aoi",
        input_assets=input_paths,
        parameters={
            "job_id": job_id,
            "band": request.band,
            "target_crs": request.target_crs,
            "to_cog": request.to_cog,
            "output_path": out_path,
            "has_aoi": aoi_geom is not None
        },
        status="queued",
        progress=0.0,
        checkpoint={"output_path": out_path}
    )
    db.add(task)
    db.commit()

    asyncio.create_task(
        pipeline_runner.run_mosaic_clip_task(
            task_id=task_id,
            input_file_paths=input_paths,
            output_path=out_path,
            aoi_geometry=aoi_geom,
            target_crs=request.target_crs,
            nodata=request.nodata,
            to_cog=request.to_cog
        )
    )

    return {
        "status": "queued",
        "task_id": task_id,
        "processing_job_id": proc_job_id,
        "source_job_id": job_id,
        "input_files_count": len(input_paths),
        "output_path": out_path
    }


@router.post("/mosaic-clip")
async def execute_mosaic_clip(request: MosaicClipRequest, db: Session = Depends(get_db)):
    if not request.input_file_paths:
        raise HTTPException(status_code=400, detail="input_file_paths cannot be empty.")

    # Reject PDFs
    for p in request.input_file_paths:
        if p.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="PDF files cannot be mosaicked. Mosaic & Clip is supported on raster formats (GeoTIFF, JP2, etc.)."
            )

    valid_paths = [str(Path(p).resolve()) for p in request.input_file_paths if Path(p).exists() and Path(p).stat().st_size > 0]
    if not valid_paths:
        raise HTTPException(status_code=400, detail="None of the specified input raster files exist or are non-empty.")

    from backend.app.dependencies.config import settings
    default_dir = settings.data_dir / "processed"
    default_dir.mkdir(parents=True, exist_ok=True)
    out_path = request.output_path or str((default_dir / f"mosaic_{uuid.uuid4().hex[:8]}.tif").resolve())

    task_id = f"proc_mos_{uuid.uuid4().hex[:8]}"
    proc_job_id = request.job_id or f"job_mosaic_{uuid.uuid4().hex[:8]}"

    from backend.app.models.models import Job, JobStatus
    proc_job = db.query(Job).filter(Job.id == proc_job_id).first()
    if not proc_job:
        proc_job = Job(id=proc_job_id, type="processing", status=JobStatus.RUNNING)
        db.add(proc_job)
        db.flush()

    task = ProcessingTask(
        id=task_id,
        job_id=proc_job_id,
        task_type="mosaic-clip-aoi",
        input_assets=valid_paths,
        parameters={
            "target_crs": request.target_crs,
            "to_cog": request.to_cog,
            "output_path": out_path,
            "has_aoi": request.aoi_geometry is not None
        },
        status="queued",
        progress=0.0,
        checkpoint={"output_path": out_path}
    )
    db.add(task)
    db.commit()

    await pipeline_runner.run_mosaic_clip_task(
        task_id=task_id,
        input_file_paths=valid_paths,
        output_path=out_path,
        aoi_geometry=request.aoi_geometry,
        target_crs=request.target_crs,
        nodata=request.nodata,
        to_cog=request.to_cog
    )

    from backend.core.processing.raster_ops import RasterOps
    meta = {}
    if Path(out_path).exists():
        try:
            meta = RasterOps.validate_raster(out_path)
        except Exception:
            pass

    return {
        "status": "completed",
        "task_id": task_id,
        "processing_job_id": proc_job_id,
        "input_files_count": len(valid_paths),
        "output_path": out_path,
        "filename": Path(out_path).name,
        "crs": meta.get("crs"),
        "width": meta.get("width"),
        "height": meta.get("height"),
        "band_count": meta.get("count"),
        "metadata": meta,
    }


# =========================================================================
# RASTER GEOPROCESSING TOOLBOX ENDPOINTS
# (Clip, Band Stack, Spectral Indices, Terrain Analysis, Reproject, Stats)
# =========================================================================

class DirectClipRequest(BaseModel):
    input_file_path: Optional[str] = None
    input_path: Optional[str] = None
    aoi_geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None  # [minLon, minLat, maxLon, maxLat]
    output_filename: Optional[str] = None
    nodata: float = 0.0
    to_cog: bool = True


class BandStackRequest(BaseModel):
    input_file_paths: List[str]
    band_names: Optional[List[str]] = None
    aoi_geometry: Optional[Dict[str, Any]] = None
    target_crs: Optional[str] = None
    output_filename: Optional[str] = None
    to_cog: bool = True
    resampling_method: str = "bilinear"


class SpectralIndexRequest(BaseModel):
    index_type: str = "ndvi"  # ndvi, ndwi, mndwi, ndsi, ndbi, savi, evi, nbr, custom
    band1_path: str
    band2_path: Optional[str] = None
    band3_path: Optional[str] = None
    band1_idx: int = 1
    band2_idx: int = 2
    band3_idx: int = 3
    custom_formula: Optional[str] = None
    output_filename: Optional[str] = None
    to_cog: bool = True


class TerrainAnalysisRequest(BaseModel):
    dem_path: str
    operation: str = "hillshade"  # slope, aspect, hillshade, tri, tpi
    azimuth: float = 315.0
    altitude: float = 45.0
    z_factor: float = 1.0
    output_filename: Optional[str] = None
    to_cog: bool = True


class ReprojectResampleRequest(BaseModel):
    input_file_path: Optional[str] = None
    input_path: Optional[str] = None
    target_crs: str = "EPSG:4326"
    resolution: Optional[float] = None
    resampling_method: str = "bilinear"
    output_filename: Optional[str] = None
    to_cog: bool = True


class RasterStatsRequest(BaseModel):
    input_file_path: Optional[str] = None
    input_path: Optional[str] = None
    aoi_geometry: Optional[Dict[str, Any]] = None


@router.get("/local-rasters")
async def list_local_rasters():
    """Scans downloads and processed directories for all available raster files."""
    import rasterio
    from backend.app.dependencies.config import settings

    valid_exts = {".tif", ".tiff", ".jp2", ".img", ".vrt"}
    rasters = []
    scan_dirs = [
        ("downloads", settings.downloads_dir),
        ("processed", settings.data_dir / "processed"),
    ]
    for folder_label, folder_path in scan_dirs:
        if not folder_path.exists():
            continue
        for p in sorted(folder_path.rglob("*"), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
            if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith(".") and p.stat().st_size > 0:
                abs_str = str(p.resolve())
                try:
                    rel_str = str(p.relative_to(folder_path))
                except Exception:
                    rel_str = p.name
                info: Dict[str, Any] = {
                    "name": p.name,
                    "path": abs_str,
                    "absolute_path": abs_str,
                    "relative_path": rel_str,
                    "folder": folder_label,
                    "root": folder_label,
                    "size_bytes": p.stat().st_size,
                    "modified_at": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                    "bands": 1,
                    "crs": "EPSG:4326",
                    "dimensions": [0, 0],
                }
                try:
                    with rasterio.open(str(p)) as src:
                        info["bands"] = src.count
                        info["crs"] = src.crs.to_string() if src.crs else "EPSG:4326"
                        info["dimensions"] = [src.width, src.height]
                        info["dtype"] = str(src.dtypes[0])
                except Exception:
                    pass
                rasters.append(info)
    return rasters


@router.post("/clip")
async def execute_direct_clip(req: DirectClipRequest):
    """Clips any raster by GeoJSON AOI polygon or bounding box [minX, minY, maxX, maxY]."""
    from backend.core.processing.raster_ops import RasterOps
    from backend.app.dependencies.config import settings
    import shapely.geometry

    target_in = req.input_file_path or req.input_path
    if not target_in:
        raise HTTPException(status_code=400, detail="Provide input_path or input_file_path")
    in_p = Path(target_in)
    if not in_p.exists():
        raise HTTPException(status_code=404, detail=f"Input raster not found: {target_in}")

    aoi_geom = req.aoi_geometry
    if not aoi_geom and req.bbox and len(req.bbox) == 4:
        aoi_geom = shapely.geometry.mapping(shapely.geometry.box(*req.bbox))

    if not aoi_geom:
        raise HTTPException(status_code=400, detail="Provide either aoi_geometry or bbox [minLon, minLat, maxLon, maxLat].")

    processed_dir = settings.data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_name = req.output_filename or f"{in_p.stem}_clipped_{uuid.uuid4().hex[:6]}.tif"
    if not out_name.lower().endswith((".tif", ".tiff")):
        out_name += ".tif"
    out_path = str((processed_dir / out_name).resolve())

    try:
        temp_clip = out_path if not req.to_cog else str((processed_dir / f"_tmp_{out_name}").resolve())
        await GeoProcessExecutor.run_cpu_bound(
            RasterOps.clip_raster, str(in_p.resolve()), aoi_geom, temp_clip, nodata=req.nodata
        )
        if req.to_cog:
            await GeoProcessExecutor.run_cpu_bound(RasterOps.build_cog, temp_clip, out_path)
            Path(temp_clip).unlink(missing_ok=True)
        meta = await GeoProcessExecutor.run_cpu_bound(RasterOps.validate_raster, out_path)
        return {
            "status": "completed",
            "operation": "CLIP",
            "output_path": out_path,
            "filename": Path(out_path).name,
            "crs": meta.get("crs"),
            "width": meta.get("width"),
            "height": meta.get("height"),
            "band_count": meta.get("count"),
            "metadata": meta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clip failed: {str(e)}")


@router.post("/stack-bands")
async def execute_band_stack(req: BandStackRequest):
    """Stacks multiple single-band or multi-band rasters into a composite multi-band GeoTIFF/COG."""
    from backend.app.dependencies.config import settings

    if len(req.input_file_paths) < 1:
        raise HTTPException(status_code=400, detail="Select at least 1 raster file to stack.")

    processed_dir = settings.data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_name = req.output_filename or f"stacked_composite_{uuid.uuid4().hex[:6]}.tif"
    if not out_name.lower().endswith((".tif", ".tiff")):
        out_name += ".tif"
    out_path = str((processed_dir / out_name).resolve())

    try:
        final_path = await GeoProcessExecutor.run_cpu_bound(
            RasterOps.stack_bands,
            input_paths=req.input_file_paths,
            output_path=out_path,
            band_names=req.band_names,
            aoi_geometry=req.aoi_geometry,
            target_crs=req.target_crs,
            to_cog=req.to_cog,
            resampling_method=req.resampling_method,
        )
        meta = await GeoProcessExecutor.run_cpu_bound(RasterOps.validate_raster, final_path)
        return {
            "status": "completed",
            "operation": "BAND_STACK",
            "output_path": final_path,
            "filename": Path(final_path).name,
            "input_count": len(req.input_file_paths),
            "crs": meta.get("crs"),
            "width": meta.get("width"),
            "height": meta.get("height"),
            "band_count": meta.get("count"),
            "metadata": meta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Band stacking failed: {str(e)}")


@router.post("/spectral-index")
async def execute_spectral_index(req: SpectralIndexRequest):
    """Computes spectral index (NDVI, NDWI, MNDWI, NDSI, NDBI, SAVI, EVI, NBR) or custom band math."""
    from backend.core.processing.raster_ops import RasterOps
    from backend.app.dependencies.config import settings

    processed_dir = settings.data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_name = req.output_filename or f"{req.index_type.lower()}_{uuid.uuid4().hex[:6]}.tif"
    if not out_name.lower().endswith((".tif", ".tiff")):
        out_name += ".tif"
    out_path = str((processed_dir / out_name).resolve())

    try:
        res = await GeoProcessExecutor.run_cpu_bound(
            RasterOps.calc_spectral_index_advanced,
            index_type=req.index_type,
            output_path=out_path,
            band1_path=req.band1_path,
            band2_path=req.band2_path,
            band3_path=req.band3_path,
            band1_idx=req.band1_idx,
            band2_idx=req.band2_idx,
            band3_idx=req.band3_idx,
            custom_formula=req.custom_formula,
            to_cog=req.to_cog,
        )
        return {
            "status": "completed",
            "operation": f"INDEX_{req.index_type.upper()}",
            "filename": Path(out_path).name,
            "min_val": res.get("min"),
            "max_val": res.get("max"),
            "mean_val": res.get("mean"),
            **res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spectral index calculation failed: {str(e)}")


@router.post("/terrain")
async def execute_terrain_analysis(req: TerrainAnalysisRequest):
    """Computes Slope, Aspect, Hillshade, TRI, or TPI from a DEM raster."""
    from backend.app.dependencies.config import settings

    processed_dir = settings.data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_name = req.output_filename or f"terrain_{req.operation.lower()}_{uuid.uuid4().hex[:6]}.tif"
    if not out_name.lower().endswith((".tif", ".tiff")):
        out_name += ".tif"
    out_path = str((processed_dir / out_name).resolve())

    try:
        res = await GeoProcessExecutor.run_cpu_bound(
            RasterOps.terrain_analysis,
            dem_path=req.dem_path,
            output_path=out_path,
            operation=req.operation,
            azimuth=req.azimuth,
            altitude=req.altitude,
            z_factor=req.z_factor,
            to_cog=req.to_cog,
        )
        return {
            "status": "completed",
            "filename": Path(out_path).name,
            "min_val": res.get("min"),
            "max_val": res.get("max"),
            "mean_val": res.get("mean"),
            **res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terrain analysis failed: {str(e)}")


@router.post("/reproject-resample")
async def execute_reproject_resample(req: ReprojectResampleRequest):
    """Reprojects raster to target CRS and optionally builds COG pyramids."""
    from backend.app.dependencies.config import settings

    target_in = req.input_file_path or req.input_path
    if not target_in:
        raise HTTPException(status_code=400, detail="Provide input_path or input_file_path")
    in_p = Path(target_in)
    if not in_p.exists():
        raise HTTPException(status_code=404, detail=f"Input raster not found: {target_in}")

    processed_dir = settings.data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_name = req.output_filename or f"{in_p.stem}_reproj_{uuid.uuid4().hex[:6]}.tif"
    if not out_name.lower().endswith((".tif", ".tiff")):
        out_name += ".tif"
    out_path = str((processed_dir / out_name).resolve())

    try:
        temp_reproj = out_path if not req.to_cog else str((processed_dir / f"_tmp_{out_name}").resolve())
        await GeoProcessExecutor.run_cpu_bound(
            RasterOps.reproject_raster,
            input_path=str(in_p.resolve()),
            target_crs=req.target_crs,
            output_path=temp_reproj,
            resampling_method=req.resampling_method,
        )
        if req.to_cog:
            await GeoProcessExecutor.run_cpu_bound(RasterOps.build_cog, temp_reproj, out_path)
            Path(temp_reproj).unlink(missing_ok=True)
        meta = await GeoProcessExecutor.run_cpu_bound(RasterOps.validate_raster, out_path)
        return {
            "status": "completed",
            "operation": "REPROJECT_COG",
            "output_path": out_path,
            "filename": Path(out_path).name,
            "crs": meta.get("crs"),
            "width": meta.get("width"),
            "height": meta.get("height"),
            "band_count": meta.get("count"),
            "metadata": meta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reprojection failed: {str(e)}")


@router.post("/raster-stats")
async def execute_raster_stats(req: RasterStatsRequest):
    """Computes raster metadata, per-band statistics, and histograms (optionally within AOI)."""
    target_in = req.input_file_path or req.input_path
    if not target_in or not Path(target_in).exists():
        raise HTTPException(status_code=404, detail=f"Input raster not found: {target_in}")

    try:
        return await GeoProcessExecutor.run_cpu_bound(RasterOps.compute_raster_stats, target_in, req.aoi_geometry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute raster stats: {str(e)}")

