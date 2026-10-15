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

    asyncio.create_task(
        pipeline_runner.run_mosaic_clip_task(
            task_id=task_id,
            input_file_paths=valid_paths,
            output_path=out_path,
            aoi_geometry=request.aoi_geometry,
            target_crs=request.target_crs,
            nodata=request.nodata,
            to_cog=request.to_cog
        )
    )

    return {
        "status": "queued",
        "task_id": task_id,
        "processing_job_id": proc_job_id,
        "input_files_count": len(valid_paths),
        "output_path": out_path
    }
