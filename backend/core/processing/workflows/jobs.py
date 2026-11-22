"""Persist and run scientific workflows through GeoHarvest's job lifecycle."""
from datetime import datetime, timezone
import logging
import traceback

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.dependencies.config import settings
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import Job, JobStatus, ProcessingTask
from backend.core.processing.executor import GeoProcessExecutor
from backend.core.processing.workflows.engine import execute_workflow
from backend.core.processing.workflows.operators import OPERATORS

WORKFLOW_JOB = "raster_workflow"
logger = logging.getLogger("geoharvest.raster_workflows")


def workflow_root():
    return settings.data_dir / "processed" / "workflows"


def submit(db: Session, plan: dict, name: str) -> Job:
    job_id = f"raster_{plan['key']}"
    job = db.get(Job, job_id)
    if not job:
        job = Job(id=job_id, type=WORKFLOW_JOB, status=JobStatus.QUEUED, job_metadata={"name": name})
        task = ProcessingTask(
            id=job_id, job=job, task_type=WORKFLOW_JOB, status="queued", parameters=plan,
            input_assets=list(dict.fromkeys(file["asset_id"] for source in plan["sources"].values()
                                            for file in source["files"] if file["asset_id"])),
        )
        db.add_all((job, task))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            job = db.get(Job, job_id)
            if job is None:
                raise
    return job


async def run(job_id, broadcast):
    with SessionLocal() as db:
        started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        claimed = db.query(Job).filter(Job.id == job_id, Job.status == JobStatus.QUEUED).update({
            Job.status: JobStatus.RUNNING, Job.started_at: started_at, Job.error: None, Job.progress: 0.0,
        })
        if not claimed:
            return
        task = db.get(ProcessingTask, job_id)
        plan = task.parameters
        task.status = "running"
        task.started_at = started_at
        task.attempt_count = (task.attempt_count or 0) + 1
        task.error = None
        db.commit()
    broadcast({"type": "job_status", "job_id": job_id, "status": "RUNNING"})

    manifest, error = None, None
    try:
        operators = {(step["operator"], step["version"]): OPERATORS[step["operator"], step["version"]]
                     for step in plan["steps"]}
        manifest = await GeoProcessExecutor.run_cpu_bound(execute_workflow, plan, workflow_root(), operators)
    except Exception as exc:
        logger.error("Raster workflow %s failed\n%s", job_id, traceback.format_exc())
        error = str(exc)[:1000]

    with SessionLocal() as db:
        status = JobStatus.COMPLETED if manifest is not None else JobStatus.FAILED
        progress = 100.0 if manifest is not None else 0.0
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        updated = db.query(Job).filter(Job.id == job_id, Job.status == JobStatus.RUNNING).update({
            Job.status: status, Job.progress: progress, Job.error: error, Job.completed_at: finished_at,
        })
        if not updated:
            return
        task = db.get(ProcessingTask, job_id)
        task.status = status.value.lower()
        task.completed_at = finished_at
        task.progress = progress
        task.error = error
        if manifest is not None:
            task.checkpoint = {"manifest": manifest}
            task.output_assets = [item["filename"] for item in manifest["outputs"] if item["kind"] == "raster"]
        db.commit()
    broadcast({"type": "job_status", "job_id": job_id, "status": status.value, "progress": progress})
