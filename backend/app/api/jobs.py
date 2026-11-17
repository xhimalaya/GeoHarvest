from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import get_db
from backend.app.models.models import Job, Download, JobStatus, DownloadStatus
from backend.app.schemas.schemas import (
    JobCreateRequest,
    JobResponse,
    JobDetailResponse,
    DownloadProgress,
    SceneBandProgress,
    SceneProgressItem,
)
from backend.core.jobs.engine import job_engine, resolve_download_byte_progress, compute_job_progress_stats

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse)
async def create_harvest_job(request: JobCreateRequest, db: Session = Depends(get_db)):
    if not request.scenes:
        raise HTTPException(status_code=400, detail="Cannot create harvest job without any selected scenes.")
    
    job = job_engine.create_harvest_job(
        name=request.name or "Sentinel-2 Harvest",
        scenes=request.scenes,
        selected_bands=request.bands,
        db=db,
        destination_dir=request.destination_dir,
        aoi=request.aoi,
        target_resolution=request.target_resolution,
        resampling_method=request.resampling_method,
        allow_reproject=request.allow_reproject,
        order_by=request.order_by,
    )
    
    downloads_count = db.query(Download).filter(Download.job_id == job.id).count()
    meta = job.job_metadata or {}
    return JobResponse(
        id=job.id,
        name=meta.get("name") or job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        total_downloads=downloads_count,
        completed_downloads=0,
        job_metadata=meta,
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    results = []
    for j in jobs:
        dls = db.query(Download).filter(Download.job_id == j.id).all()
        completed_dls, total_dls, _, _, computed_pct = compute_job_progress_stats(dls)
        meta = j.job_metadata or {}
        s_plans = meta.get("scene_plans") or {}
        if j.status == JobStatus.COMPLETED:
            display_progress = 100.0
        elif s_plans:
            tot_sc = max(1, len(s_plans))
            comp_sc = sum(1 for sp in s_plans.values() if sp.get("status") == "completed")
            rem_sc = tot_sc - comp_sc
            display_progress = round(min(99.0, (comp_sc * 100.0 + rem_sc * (computed_pct * 0.9)) / tot_sc), 1)
        else:
            display_progress = min(99.0, computed_pct) if total_dls > 0 else j.progress
        results.append(
            JobResponse(
                id=j.id,
                name=meta.get("name") or j.id,
                type=j.type,
                status=j.status,
                progress=display_progress,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                error=j.error,
                total_downloads=total_dls,
                completed_downloads=completed_dls,
                job_metadata=meta,
            )
        )
    return results


_FRIENDLY_BAND_LABELS: Dict[str, str] = {
    "coastal": "Coastal Aerosol",
    "blue": "Blue",
    "green": "Green",
    "red": "Red",
    "rededge1": "Red Edge 1",
    "rededge2": "Red Edge 2",
    "rededge3": "Red Edge 3",
    "nir": "NIR",
    "nir08": "NIR Narrow",
    "nir09": "Water Vapour",
    "swir16": "SWIR 1",
    "swir22": "SWIR 2",
    "lwir11": "Thermal IR 1",
    "lwir12": "Thermal IR 2",
    "visual": "True Color (RGB)",
    "vv": "SAR VV",
    "vh": "SAR VH",
    "hh": "SAR HH",
    "hv": "SAR HV",
    "dem": "Elevation (DEM)",
    "data": "Data",
}


def _format_band_label(key: str, fallback: str = "") -> str:
    k = (key or "").strip().lower()
    if k in _FRIENDLY_BAND_LABELS:
        return _FRIENDLY_BAND_LABELS[k]
    if fallback:
        return fallback
    return (key or "Band").upper()


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    dls = db.query(Download).filter(Download.job_id == job_id).all()
    completed_dls, total_dls, _, _, computed_pct = compute_job_progress_stats(dls)
    display_progress = 100.0 if job.status == JobStatus.COMPLETED else (computed_pct if total_dls > 0 else job.progress)

    meta = job.job_metadata or {}
    scene_plans: Dict[str, Any] = meta.get("scene_plans") or {}
    dl_meta_lookup: Dict[str, Dict[str, Any]] = {}
    for s_id, sp in scene_plans.items():
        f_out = sp.get("final_output_path")
        for b_entry in sp.get("bands") or []:
            did = b_entry.get("download_id")
            if did:
                dl_meta_lookup[did] = {
                    "scene_id": s_id,
                    "band": b_entry.get("key") or b_entry.get("band"),
                    "final_output_path": f_out,
                }

    progress_items: List[DownloadProgress] = []
    dl_progress_by_id: Dict[str, DownloadProgress] = {}
    for d in dls:
        dn_bytes, tot_bytes, pct = resolve_download_byte_progress(d.status, d.downloaded_bytes, d.total_bytes)
        extra = dl_meta_lookup.get(d.id, {})
        item = DownloadProgress(
            id=d.id,
            asset_name=d.asset_id or "",
            destination=d.destination,
            total_bytes=tot_bytes,
            downloaded_bytes=dn_bytes,
            status=d.status,
            progress_percentage=pct,
            attempt_count=d.attempt_count,
            error=d.last_error,
            scene_id=extra.get("scene_id"),
            band=extra.get("band"),
            final_output_path=extra.get("final_output_path"),
        )
        progress_items.append(item)
        dl_progress_by_id[d.id] = item

    scene_items: List[SceneProgressItem] = []
    if scene_plans:
        scene_order = meta.get("scene_order") or list(scene_plans.keys())
        dl_root = settings.downloads_dir.resolve()
        for s_id in scene_order:
            sp = scene_plans.get(s_id)
            if not sp:
                continue
            final_out = sp.get("final_output_path")
            output_filename = Path(final_out).name if final_out else f"{s_id}.tif"
            rel_out = final_out
            if final_out:
                try:
                    rel_out = str(Path(final_out).resolve().relative_to(dl_root)).replace("\\", "/")
                except ValueError:
                    proj_part = sp.get("project_dir") or sp.get("project_name") or meta.get("task_name") or ""
                    ds_part = sp.get("dataset_dir") or sp.get("collection") or ""
                    rel_out = f"{proj_part}/{ds_part}/{sp.get('year', '')}/{sp.get('month', '')}/{output_filename}".strip("/")

            bands_list: List[SceneBandProgress] = []
            s_dn_bytes = 0
            s_tot_bytes = 0
            s_comp_bands = 0
            raw_bands = sp.get("bands") or []
            for b_entry in raw_bands:
                did = b_entry.get("download_id") or ""
                b_key = str(b_entry.get("key") or b_entry.get("band") or "band")
                b_label = _format_band_label(b_key, str(b_entry.get("description") or ""))
                dp = dl_progress_by_id.get(did)
                if dp:
                    b_status = dp.status.value if hasattr(dp.status, "value") else str(dp.status)
                    b_dn = dp.downloaded_bytes
                    b_tot = dp.total_bytes
                    b_pct = dp.progress_percentage
                    b_err = dp.error
                else:
                    b_status = "COMPLETED" if sp.get("status") == "completed" else "PENDING"
                    b_dn = 0
                    b_tot = 0
                    b_pct = 100.0 if b_status == "COMPLETED" else 0.0
                    b_err = None

                if b_status == "COMPLETED":
                    s_comp_bands += 1
                s_dn_bytes += b_dn
                s_tot_bytes += b_tot
                bands_list.append(
                    SceneBandProgress(
                        download_id=did,
                        band=b_key,
                        label=b_label,
                        status=b_status,
                        downloaded_bytes=b_dn,
                        total_bytes=b_tot,
                        progress_percentage=b_pct,
                        error=b_err,
                    )
                )

            tot_bands = len(bands_list)
            raw_status = str(sp.get("status") or "pending").lower()
            is_stacked_scene = bool(sp.get("stack_enabled", True))
            if s_tot_bytes > 0:
                band_pct = min(100.0, max(0.0, (s_dn_bytes / s_tot_bytes) * 100.0))
            elif tot_bands > 0:
                band_pct = (s_comp_bands / tot_bands) * 100.0
            else:
                band_pct = 0.0

            if raw_status == "completed":
                s_pct = 100.0
            elif is_stacked_scene:
                if raw_status == "stacking":
                    s_pct = 95.0
                else:
                    s_pct = round(min(90.0, band_pct * 0.9), 1)
            else:
                s_pct = round(band_pct, 1)

            scene_items.append(
                SceneProgressItem(
                    scene_id=s_id,
                    collection=sp.get("collection"),
                    dataset_dir=sp.get("dataset_dir"),
                    datetime=sp.get("datetime"),
                    year=sp.get("year"),
                    month=sp.get("month"),
                    mode=sp.get("mode") or "stack_bands",
                    stack_enabled=is_stacked_scene,
                    status=raw_status,
                    output_filename=output_filename,
                    final_output_path=final_out,
                    relative_output_path=rel_out,
                    selected_bands=list(sp.get("selected_bands") or [b.band for b in bands_list]),
                    completed_bands=s_comp_bands,
                    total_bands=tot_bands,
                    downloaded_bytes=s_dn_bytes,
                    total_bytes=s_tot_bytes,
                    progress_percentage=s_pct,
                    bands=bands_list,
                    output_metadata=sp.get("output_metadata"),
                    error=sp.get("error"),
                )
            )

        if job.status != JobStatus.COMPLETED and scene_items:
            display_progress = round(
                min(99.0, sum(si.progress_percentage for si in scene_items) / len(scene_items)),
                1,
            )

    return JobDetailResponse(
        id=job.id,
        name=meta.get("name") or job.id,
        type=job.type,
        status=job.status,
        progress=display_progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        total_downloads=total_dls,
        completed_downloads=completed_dls,
        downloads=progress_items,
        scenes=scene_items,
        job_metadata=meta
    )


@router.post("/{job_id}/pause")
async def pause_job(job_id: str, db: Session = Depends(get_db)):
    success = job_engine.pause_job(job_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to pause job (job may not be running)")
    return {"status": "ok", "job_id": job_id, "action": "paused"}


@router.post("/{job_id}/resume")
async def resume_job(job_id: str, db: Session = Depends(get_db)):
    success = job_engine.resume_job(job_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to resume job")
    return {"status": "ok", "job_id": job_id, "action": "resumed"}


@router.post("/{job_id}/restart")
async def restart_job(job_id: str, reset_all: bool = False, db: Session = Depends(get_db)):
    success = job_engine.restart_job(job_id, db, reset_all=reset_all)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to restart job")
    return {"status": "ok", "job_id": job_id, "action": "restarted", "reset_all": reset_all}


@router.post("/{job_id}/scenes/{scene_id}/restart")
async def restart_scene(job_id: str, scene_id: str, db: Session = Depends(get_db)):
    success = job_engine.restart_scene(job_id, scene_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to restart scene")
    return {"status": "ok", "job_id": job_id, "scene_id": scene_id, "action": "scene_restarted"}


@router.post("/{job_id}/downloads/{download_id}/restart")
async def restart_download(job_id: str, download_id: str, db: Session = Depends(get_db)):
    success = job_engine.restart_download(job_id, download_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to restart download")
    return {"status": "ok", "job_id": job_id, "download_id": download_id, "action": "download_restarted"}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    success = job_engine.cancel_job(job_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to cancel job")
    return {"status": "ok", "job_id": job_id, "action": "cancelled"}
