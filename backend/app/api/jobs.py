from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.dependencies.database import get_db
from backend.app.models.models import Job, Download, JobStatus, DownloadStatus
from backend.app.schemas.schemas import JobCreateRequest, JobResponse, JobDetailResponse, DownloadProgress
from backend.core.jobs.engine import job_engine

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
        aoi=request.aoi
    )
    
    downloads_count = db.query(Download).filter(Download.job_id == job.id).count()
    return JobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        total_downloads=downloads_count,
        completed_downloads=0
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    results = []
    for j in jobs:
        dls = db.query(Download).filter(Download.job_id == j.id).all()
        total_dls = len(dls)
        completed_dls = sum(1 for d in dls if d.status == DownloadStatus.COMPLETED)
        results.append(
            JobResponse(
                id=j.id,
                type=j.type,
                status=j.status,
                progress=j.progress,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                error=j.error,
                total_downloads=total_dls,
                completed_downloads=completed_dls
            )
        )
    return results


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    dls = db.query(Download).filter(Download.job_id == job_id).all()
    total_dls = len(dls)
    completed_dls = sum(1 for d in dls if d.status == DownloadStatus.COMPLETED)

    progress_items = []
    for d in dls:
        pct = (d.downloaded_bytes / d.total_bytes * 100.0) if d.total_bytes > 0 else (100.0 if d.status == DownloadStatus.COMPLETED else 0.0)
        progress_items.append(
            DownloadProgress(
                id=d.id,
                asset_name=d.asset_id or "",
                destination=d.destination,
                total_bytes=d.total_bytes,
                downloaded_bytes=d.downloaded_bytes,
                status=d.status,
                progress_percentage=round(pct, 1),
                attempt_count=d.attempt_count,
                error=d.last_error
            )
        )

    return JobDetailResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        total_downloads=total_dls,
        completed_downloads=completed_dls,
        downloads=progress_items,
        job_metadata=job.job_metadata or {}
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


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    success = job_engine.cancel_job(job_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to cancel job")
    return {"status": "ok", "job_id": job_id, "action": "cancelled"}
