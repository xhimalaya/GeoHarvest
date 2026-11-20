import asyncio
import re
import shutil
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import anyio
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.app.dependencies.database import get_db
from backend.app.models.models import ProcessingTask, Asset, AssetLineage
from backend.core.crs.engine import STRICT_OUTPUT_CRS, enforce_strict_epsg4326
from backend.core.processing.recipes import recipe_registry
from backend.core.processing.pipeline import pipeline_runner
from backend.core.processing.raster_ops import RasterOps
from backend.core.processing.executor import GeoProcessExecutor

router = APIRouter(prefix="/api/processing", tags=["processing"])


class ExecuteProcessingRequest(BaseModel):
    input_file_path: Optional[str] = None
    input_file_paths: Optional[List[str]] = None
    input_asset_ids: Optional[List[str]] = None
    directory: Optional[str] = None
    recursive: bool = True
    recipe_id: str = "s2-aoi-cog"
    aoi_geometry: Optional[Dict[str, Any]] = None
    clip_to_aoi: bool = True
    target_crs: Optional[str] = "EPSG:4326"
    job_id: Optional[str] = None


async def _resolve_execute_inputs(request: ExecuteProcessingRequest, db: Session) -> List[str]:
    """Resolve input raster file paths from explicit files, a folder, or catalog asset IDs."""
    candidates: List[str] = []

    if request.input_file_paths:
        for p_str in request.input_file_paths:
            p = Path(p_str).expanduser().resolve()
            if not p.exists() or not p.is_file():
                raise HTTPException(status_code=404, detail=f"Input raster not found: {p_str}")
            if p.suffix.lower() not in _VALID_RASTER_EXTS:
                raise HTTPException(status_code=400, detail=f"Unsupported raster extension: {p.name}")
            candidates.append(str(p))

    if request.input_file_path:
        p = Path(request.input_file_path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=404, detail=f"Input raster not found: {request.input_file_path}")
        if p.suffix.lower() not in _VALID_RASTER_EXTS:
            raise HTTPException(status_code=400, detail=f"Unsupported raster extension: {p.name}")
        candidates.append(str(p))

    if request.directory and not request.input_file_paths:
        try:
            scanned = await anyio.to_thread.run_sync(_scan_rasters_sync, request.directory, request.recursive)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except NotADirectoryError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        candidates.extend(item["absolute_path"] for item in scanned)

    if request.input_asset_ids:
        assets = db.query(Asset).filter(Asset.id.in_(request.input_asset_ids)).all()
        for asset in assets:
            path_candidate = asset.local_path or asset.url
            if not path_candidate:
                continue
            p = Path(path_candidate).expanduser()
            if p.exists() and p.is_file() and p.suffix.lower() in _VALID_RASTER_EXTS:
                candidates.append(str(p.resolve()))

    # Deduplicate preserving discovery order
    unique_paths: List[str] = []
    seen: set[str] = set()
    for p_str in candidates:
        if p_str not in seen:
            seen.add(p_str)
            unique_paths.append(p_str)

    if not unique_paths:
        raise HTTPException(
            status_code=400,
            detail="No valid raster files (.tif/.tiff/.jp2/.img/.vrt) found in the selected folder, files, or catalog assets.",
        )
    return unique_paths


@router.get("/recipes")
async def list_recipes():
    return recipe_registry.list_recipes()


@router.post("/execute")
async def execute_recipe(request: ExecuteProcessingRequest, db: Session = Depends(get_db)):
    try:
        strict_crs = enforce_strict_epsg4326(request.target_crs, reject_invalid=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resolved_files = await _resolve_execute_inputs(request, db)

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
        input_assets=resolved_files,
        parameters={
            "recipe_id": request.recipe_id,
            "target_crs": strict_crs,
            "directory": request.directory,
            "clip_to_aoi": request.clip_to_aoi,
            "input_count": len(resolved_files),
        },
        status="queued",
        progress=0.0,
        checkpoint={
            "completed_steps": [],
            "intermediate_files": {},
            "total_items": len(resolved_files),
            "completed_items": 0,
        },
    )
    db.add(task)
    db.commit()

    asyncio.create_task(
        pipeline_runner.run_task(
            task_id=task_id,
            input_file_path=resolved_files[0],
            input_file_paths=resolved_files,
            recipe_id=request.recipe_id,
            aoi_geometry=request.aoi_geometry,
            target_crs=strict_crs,
            clip_to_aoi=request.clip_to_aoi,
        )
    )

    return {
        "status": "queued",
        "task_id": task_id,
        "job_id": job_id,
        "recipe_id": request.recipe_id,
        "input_count": len(resolved_files),
        "input_files": resolved_files,
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
    target_crs: Optional[str] = "EPSG:4326"
    nodata: Optional[float] = 0.0
    to_cog: bool = True
    job_id: Optional[str] = None


class JobMosaicClipRequest(BaseModel):
    selected_download_ids: Optional[List[str]] = None
    band: Optional[str] = None
    aoi_geometry: Optional[Dict[str, Any]] = None
    target_crs: Optional[str] = "EPSG:4326"
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


def _collect_job_raster_candidates(job: Any, db: Session) -> tuple[List[Dict[str, Any]], set[str]]:
    """Collect deliverable raster candidates for a job (stacked scene GeoTIFFs + legacy direct rasters)."""
    from backend.app.models.models import Download, DownloadStatus

    valid_exts = {".tif", ".tiff", ".jp2", ".img", ".vrt"}
    meta = job.job_metadata or {}
    scene_plans = meta.get("scene_plans") if isinstance(meta.get("scene_plans"), dict) else {}
    stacked_dl_ids: set[str] = set()
    candidates: List[Dict[str, Any]] = []
    bands_found: set[str] = set()

    for s_id, sp in (scene_plans or {}).items():
        if not sp.get("stack_enabled"):
            continue
        stacked_dl_ids.update(sp.get("download_ids") or [])
        if sp.get("status") != "completed" or not sp.get("final_output_path"):
            continue
        out_path = Path(sp["final_output_path"])
        if not (
            out_path.suffix.lower() in valid_exts
            and _is_valid_raster_file(out_path)
        ):
            continue
        out_meta = sp.get("output_metadata") or {}
        band_keys = list(out_meta.get("band_keys") or [])
        band_descs = list(out_meta.get("band_descriptions") or [])
        bands_found.add("stacked")
        candidates.append({
            "id": f"scene_{s_id}",
            "scene_id": s_id,
            "asset_name": out_path.name,
            "destination": str(out_path.resolve()),
            "filename": out_path.name,
            "size_bytes": out_path.stat().st_size,
            "band": "stacked",
            "band_keys": band_keys,
            "band_descriptions": band_descs,
            "download_ids": list(sp.get("download_ids") or []),
            "is_stacked": True,
        })

    dls = (
        db.query(Download)
        .filter(Download.job_id == job.id, Download.status == DownloadStatus.COMPLETED)
        .all()
    )
    for d in dls:
        if d.id in stacked_dl_ids or not d.destination:
            continue
        p = Path(d.destination)
        if p.suffix.lower() in valid_exts and _is_valid_raster_file(p):
            band_name = d.asset.band if d.asset and d.asset.band else None
            if not band_name:
                stem_parts = p.stem.split("_")
                band_name = stem_parts[-1] if len(stem_parts) > 1 else "raster"
            bands_found.add(band_name)
            candidates.append({
                "id": d.id,
                "scene_id": d.asset.dataset_id if d.asset else None,
                "asset_name": d.asset.asset_name if d.asset else p.name,
                "destination": str(p.resolve()),
                "filename": p.name,
                "size_bytes": p.stat().st_size,
                "band": band_name,
                "band_keys": [band_name],
                "band_descriptions": [band_name],
                "download_ids": [d.id],
                "is_stacked": False,
            })

    return candidates, bands_found


@router.get("/jobs/{job_id}/mosaic-options")
async def get_job_mosaic_options(job_id: str, db: Session = Depends(get_db)):
    from backend.app.models.models import Job
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

    raster_dls, bands_found = _collect_job_raster_candidates(job, db)

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

    candidates, _ = _collect_job_raster_candidates(job, db)
    selected_ids = set(request.selected_download_ids or [])
    req_band = request.band.lower() if request.band else None

    selected_items: List[Dict[str, Any]] = []
    for item in candidates:
        if selected_ids:
            item_ids = {item["id"], *item.get("download_ids", [])}
            if not (selected_ids & item_ids):
                continue
        if req_band and req_band != "all":
            item_bands = {str(item.get("band") or "").lower(), *(str(b).lower() for b in item.get("band_keys", []))}
            if req_band not in item_bands:
                continue
        selected_items.append(item)

    if not selected_items:
        raise HTTPException(status_code=400, detail="No matching completed raster files found for mosaicking.")

    input_paths = [item["destination"] for item in selected_items]

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

    try:
        strict_crs = enforce_strict_epsg4326(request.target_crs, reject_invalid=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task = ProcessingTask(
        id=task_id,
        job_id=proc_job_id,
        task_type="mosaic-clip-aoi",
        input_assets=input_paths,
        parameters={
            "job_id": job_id,
            "band": request.band,
            "target_crs": strict_crs,
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
            target_crs=strict_crs,
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

    try:
        strict_crs = enforce_strict_epsg4326(request.target_crs, reject_invalid=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task = ProcessingTask(
        id=task_id,
        job_id=proc_job_id,
        task_type="mosaic-clip-aoi",
        input_assets=valid_paths,
        parameters={
            "target_crs": strict_crs,
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
        target_crs=strict_crs,
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
    target_crs: Optional[str] = "EPSG:4326"
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


_VALID_RASTER_EXTS = {".tif", ".tiff", ".jp2", ".img", ".vrt"}


def _get_workspace_scan_roots() -> List[tuple[str, str, Path]]:
    """Return deduplicated workspace roots (key, display_name, resolved_path)."""
    from backend.app.dependencies.config import settings
    from backend.app.api.storage import get_active_download_dir

    candidates = [
        ("downloads", "Active Downloads", get_active_download_dir().resolve()),
        ("default_downloads", "Default Downloads", settings.downloads_dir.resolve()),
        ("processed", "Processed Outputs", (settings.data_dir / "processed").resolve()),
        ("custom", "Custom Uploaded Data", (settings.data_dir / "custom").resolve()),
    ]
    roots: List[tuple[str, str, Path]] = []
    seen: set[Path] = set()
    for key, title, path in candidates:
        if path in seen:
            continue
        seen.add(path)
        roots.append((key, title, path))
    return roots


def _resolve_storage_location(file_path: Path) -> tuple[Optional[str], Optional[str]]:
    """Map an absolute file path onto an allowed storage root and relative path, if any."""
    from backend.app.api.storage import get_allowed_roots

    resolved_file = file_path.resolve()
    roots = get_allowed_roots()
    # Check deepest/most-specific roots first; keep generic 'data' as lowest priority tie-breaker.
    ordered_roots = sorted(
        roots.items(),
        key=lambda item: (len(item[1].resolve().parts), 0 if item[0] == "data" else 1),
        reverse=True,
    )
    for root_name, root_dir in ordered_roots:
        resolved_root = root_dir.resolve()
        if resolved_file.is_relative_to(resolved_root):
            return root_name, str(resolved_file.relative_to(resolved_root))
    return None, None


def _is_valid_raster_file(path: Path) -> bool:
    """Return True if path is a non-empty, non-hidden deliverable file with a supported raster extension."""
    try:
        return (
            path.is_file()
            and path.suffix.lower() in _VALID_RASTER_EXTS
            and not path.name.startswith(".")
            and not path.name.endswith(".partial.tif")
            and ".staging" not in path.parts
            and path.stat().st_size > 0
        )
    except OSError:
        return False


def _build_raster_info(path: Path, base_folder: Path, folder_label: str) -> Dict[str, Any]:
    """Construct serialized raster metadata dictionary for a discovered raster file."""
    import rasterio

    abs_path = path.resolve()
    abs_str = str(abs_path)
    try:
        rel_str = str(abs_path.relative_to(base_folder.resolve()))
    except ValueError:
        rel_str = abs_path.name

    parent_rel = ""
    try:
        rel_parent = abs_path.parent.relative_to(base_folder.resolve())
        parent_rel = "" if str(rel_parent) == "." else str(rel_parent)
    except ValueError:
        parent_rel = ""

    storage_root, storage_rel_path = _resolve_storage_location(abs_path)
    stat = abs_path.stat()

    info: Dict[str, Any] = {
        "name": abs_path.name,
        "path": abs_str,
        "absolute_path": abs_str,
        "relative_path": rel_str,
        "parent_folder": str(abs_path.parent),
        "subfolder": parent_rel,
        "folder": folder_label,
        "root": folder_label,
        "storage_root": storage_root,
        "storage_rel_path": storage_rel_path,
        "size_bytes": stat.st_size,
        "modified_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "bands": 1,
        "crs": "EPSG:4326",
        "dimensions": [0, 0],
    }
    try:
        with rasterio.open(abs_str) as src:
            info["bands"] = src.count
            info["crs"] = src.crs.to_string() if src.crs else "EPSG:4326"
            info["dimensions"] = [src.width, src.height]
            info["dtype"] = str(src.dtypes[0])
    except Exception:
        pass
    return info


def _scan_rasters_sync(directory: Optional[str] = None, recursive: bool = True) -> List[Dict[str, Any]]:
    """Scan either a requested directory or all workspace raster roots synchronously."""
    candidates: List[tuple[float, Path, Path, str]] = []
    seen_paths: set[str] = set()

    if directory:
        target_dir = Path(directory).expanduser().resolve()
        if not target_dir.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")

        folder_label = target_dir.name or "custom"
        for root_key, _title, root_path in _get_workspace_scan_roots():
            if target_dir == root_path or target_dir.is_relative_to(root_path):
                folder_label = root_key
                break
        scan_targets = [(folder_label, target_dir)]
    else:
        scan_targets = [(key, root_path) for key, _title, root_path in _get_workspace_scan_roots()]

    for folder_label, folder_path in scan_targets:
        if not folder_path.exists() or not folder_path.is_dir():
            continue
        iterator = folder_path.rglob("*") if recursive else folder_path.iterdir()
        for entry in iterator:
            try:
                if any(part.startswith(".") for part in entry.relative_to(folder_path).parts):
                    continue
            except ValueError:
                pass
            if not _is_valid_raster_file(entry):
                continue
            resolved_str = str(entry.resolve())
            if resolved_str in seen_paths:
                continue
            seen_paths.add(resolved_str)
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                mtime = 0.0
            candidates.append((mtime, entry, folder_path, folder_label))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [_build_raster_info(entry, base_folder, label) for _mtime, entry, base_folder, label in candidates]


def _discover_local_folders_sync() -> Dict[str, Any]:
    """Build a structured inventory of downloaded, processed, and custom raster folders."""
    scan_roots = _get_workspace_scan_roots()
    root_map = {key: str(path) for key, _title, path in scan_roots}
    folders: List[Dict[str, Any]] = []

    for root_key, title, root_path in scan_roots:
        if not root_path.exists() or not root_path.is_dir():
            continue

        dir_stats: Dict[Path, Dict[str, Any]] = {}
        for p in root_path.rglob("*"):
            try:
                if any(part.startswith(".") for part in p.relative_to(root_path).parts):
                    continue
            except ValueError:
                pass
            if not _is_valid_raster_file(p):
                continue
            stat = p.stat()
            parent = p.parent.resolve()
            # Ensure root and all ancestors up to root_path are tracked
            cur = parent
            direct = True
            while cur == root_path or cur.is_relative_to(root_path):
                entry = dir_stats.setdefault(
                    cur,
                    {
                        "file_count": 0,
                        "direct_file_count": 0,
                        "total_size_bytes": 0,
                        "child_dirs": set(),
                    },
                )
                entry["file_count"] += 1
                if direct:
                    entry["direct_file_count"] += 1
                entry["total_size_bytes"] += stat.st_size
                if cur == root_path:
                    break
                parent_dir = cur.parent.resolve()
                parent_entry = dir_stats.setdefault(
                    parent_dir,
                    {
                        "file_count": 0,
                        "direct_file_count": 0,
                        "total_size_bytes": 0,
                        "child_dirs": set(),
                    },
                )
                parent_entry["child_dirs"].add(cur)
                cur = parent_dir
                direct = False

        # Always expose primary roots if they contain rasters or are downloads/processed
        if root_path not in dir_stats and root_key in {"downloads", "processed"}:
            dir_stats[root_path] = {
                "file_count": 0,
                "direct_file_count": 0,
                "total_size_bytes": 0,
                "child_dirs": set(),
            }

        sorted_dirs = sorted(
            dir_stats.keys(),
            key=lambda d: (0 if d == root_path else len(d.relative_to(root_path).parts), str(d)),
        )
        for dir_path in sorted_dirs:
            meta = dir_stats[dir_path]
            rel_path = "." if dir_path == root_path else str(dir_path.relative_to(root_path))
            depth = 0 if dir_path == root_path else len(dir_path.relative_to(root_path).parts)

            include_dir = (
                depth <= 1
                or meta["direct_file_count"] > 0
                or len(meta["child_dirs"]) > 1
            )
            if not include_dir:
                continue

            display_name = title if depth == 0 else rel_path
            folders.append(
                {
                    "id": f"{root_key}:{rel_path}",
                    "name": dir_path.name if depth > 0 else title,
                    "label": display_name,
                    "path": str(dir_path),
                    "relative_path": rel_path,
                    "root": root_key,
                    "depth": depth,
                    "file_count": meta["file_count"],
                    "direct_file_count": meta["direct_file_count"],
                    "total_size_bytes": meta["total_size_bytes"],
                }
            )

    return {
        "active_download_dir": root_map.get("downloads", ""),
        "processed_dir": root_map.get("processed", ""),
        "custom_dir": root_map.get("custom", ""),
        "folders": folders,
    }


def _save_uploaded_raster_sync(file_obj: Any, original_filename: str) -> Dict[str, Any]:
    """Validate and persist an uploaded custom raster into data/custom."""
    import rasterio
    from backend.app.dependencies.config import settings

    raw_name = Path(original_filename or "custom_raster.tif").name
    ext = Path(raw_name).suffix.lower()
    if ext not in _VALID_RASTER_EXTS:
        raise ValueError(f"Unsupported raster extension '{ext}'. Allowed: {', '.join(sorted(_VALID_RASTER_EXTS))}")

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(raw_name).stem).strip("._") or "custom_raster"
    custom_dir = (settings.data_dir / "custom").resolve()
    custom_dir.mkdir(parents=True, exist_ok=True)

    target_path = custom_dir / f"{stem}{ext}"
    if target_path.exists():
        target_path = custom_dir / f"{stem}_{uuid.uuid4().hex[:6]}{ext}"

    try:
        file_obj.seek(0)
        with open(target_path, "wb") as out_f:
            shutil.copyfileobj(file_obj, out_f)
        if target_path.stat().st_size == 0:
            raise ValueError("Uploaded file is empty")
        with rasterio.open(str(target_path)) as src:
            _ = src.width, src.height, src.count

        # Strictly enforce EPSG:4326 on all saved/uploaded rasters
        from backend.core.processing.scene_stacker import reproject_file_to_crs_task
        reproj_res = reproject_file_to_crs_task(str(target_path), STRICT_OUTPUT_CRS)
        target_path = Path(reproj_res.get("output_path") or target_path)
    except Exception as exc:
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise ValueError(f"Uploaded file is not a valid readable raster: {exc}") from exc

    return _build_raster_info(target_path, custom_dir, "custom")


@router.get("/local-rasters")
async def list_local_rasters(
    directory: Optional[str] = Query(None, description="Optional folder path to filter raster discovery"),
    recursive: bool = Query(True, description="Include rasters in nested subdirectories"),
):
    """Scan workspace roots or a selected folder for available local raster files."""
    try:
        return await anyio.to_thread.run_sync(_scan_rasters_sync, directory, recursive)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/local-folders")
async def list_local_folders():
    """List downloaded, processed, and custom folders containing local rasters."""
    return await anyio.to_thread.run_sync(_discover_local_folders_sync)


@router.post("/upload-raster")
async def upload_custom_raster(file: UploadFile = File(...)):
    """Upload a custom local GeoTIFF/raster file into data/custom for geoprocessing."""
    try:
        info = await anyio.to_thread.run_sync(
            _save_uploaded_raster_sync,
            file.file,
            file.filename or "custom_raster.tif",
        )
        return {"status": "uploaded", "raster": info, **info}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        await file.close()


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
        strict_crs = enforce_strict_epsg4326(req.target_crs, reject_invalid=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        final_path = await GeoProcessExecutor.run_cpu_bound(
            RasterOps.stack_bands,
            input_paths=req.input_file_paths,
            output_path=out_path,
            band_names=req.band_names,
            aoi_geometry=req.aoi_geometry,
            target_crs=strict_crs,
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
        strict_crs = enforce_strict_epsg4326(req.target_crs, reject_invalid=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        temp_reproj = out_path if not req.to_cog else str((processed_dir / f"_tmp_{out_name}").resolve())
        await GeoProcessExecutor.run_cpu_bound(
            RasterOps.reproject_raster,
            input_path=str(in_p.resolve()),
            target_crs=strict_crs,
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

