import copy
import os
import shutil
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import Job, Download, JobStatus, DownloadStatus
from backend.core.jobs.engine import job_engine
from backend.core.processing.scene_stacker import scene_stacking_service
from backend.core.crs.engine import STRICT_OUTPUT_CRS

logger = logging.getLogger("geoharvest.recovery")


class CrashRecoveryManager:
    """Inspects database on application startup, recovers interrupted jobs, checks .part and stacked .tif files, and resumes."""

    @classmethod
    def _prune_orphaned_staging_dirs(cls, db: Session) -> None:
        staging_root = settings.downloads_dir / ".staging"
        if not staging_root.exists() or not staging_root.is_dir():
            return
        try:
            existing_jobs = {
                j.id: j.status
                for j in db.query(Job).all()
            }
            for entry in staging_root.iterdir():
                if not entry.is_dir():
                    continue
                j_status = existing_jobs.get(entry.name)
                if j_status is None or j_status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
                    shutil.rmtree(entry, ignore_errors=True)
                    logger.info(f"Pruned orphaned staging directory: {entry}")
        except Exception as exc:
            logger.warning(f"Failed to prune orphaned staging directories: {exc}")

    @classmethod
    def recover_interrupted_jobs(cls):
        db: Session = SessionLocal()
        try:
            cls._prune_orphaned_staging_dirs(db)

            interrupted_jobs = db.query(Job).filter(
                Job.status.in_([
                    JobStatus.RUNNING,
                    JobStatus.QUEUED,
                    JobStatus.RETRYING,
                    JobStatus.PROCESSING,
                    JobStatus.VERIFYING
                ])
            ).all()

            if not interrupted_jobs:
                logger.info("Crash recovery check: No interrupted jobs found.")
                return 0

            logger.info(f"Crash recovery: Found {len(interrupted_jobs)} interrupted job(s). Initiating recovery...")
            recovered_count = 0

            for job in interrupted_jobs:
                completed_scene_dl_ids = set()
                unstacked_scene_dl_ids = set()

                if isinstance(job.job_metadata, dict) and isinstance(job.job_metadata.get("scene_plans"), dict):
                    meta = copy.deepcopy(job.job_metadata)
                    expected_job_crs = STRICT_OUTPUT_CRS
                    for scene_id, sp in meta["scene_plans"].items():
                        dl_ids = list(sp.get("download_ids") or [])
                        final_out = sp.get("final_output_path")
                        if final_out:
                            final_path = Path(final_out)
                            # Remove any leftover partial GeoTIFF from an interrupted atomic write
                            for partial_candidate in (
                                final_path.with_name(f"{final_path.stem}.partial{final_path.suffix}"),
                                Path(f"{final_out}.partial.tif"),
                                Path(f"{final_out}.partial"),
                            ):
                                if partial_candidate.exists():
                                    try:
                                        partial_candidate.unlink()
                                    except OSError:
                                        pass

                            if final_path.exists() and final_path.is_file() and final_path.stat().st_size > 0:
                                val = scene_stacking_service.validate_stacked_output(
                                    output_path=final_path,
                                    expected_crs=expected_job_crs,
                                    check_data_readable=True,
                                )
                                if val.get("valid"):
                                    sp["status"] = "completed"
                                    sp["error"] = None
                                    completed_scene_dl_ids.update(dl_ids)
                                    _staging = sp.get("staging_dir")
                                    if _staging and Path(_staging).exists():
                                        shutil.rmtree(_staging, ignore_errors=True)
                                    continue

                        if sp.get("stack_enabled"):
                            unstacked_scene_dl_ids.update(dl_ids)
                        if sp.get("status") in ("stacking", "completed", "failed", "paused"):
                            sp["status"] = "downloading"
                            sp["error"] = None

                    job.job_metadata = meta
                    flag_modified(job, "job_metadata")

                downloads = db.query(Download).filter(Download.job_id == job.id).all()
                for dl in downloads:
                    if dl.id in completed_scene_dl_ids:
                        dl.status = DownloadStatus.COMPLETED
                        if (dl.downloaded_bytes or 0) <= 0 and (dl.total_bytes or 0) > 0:
                            dl.downloaded_bytes = dl.total_bytes
                        continue

                    dest_path = Path(dl.destination)
                    part_path = Path(str(dest_path) + ".part")

                    if dest_path.exists() and dest_path.stat().st_size > 0:
                        # File was already fully downloaded before crash
                        dl.status = DownloadStatus.COMPLETED
                        dl.downloaded_bytes = dest_path.stat().st_size
                        if dl.total_bytes == 0:
                            dl.total_bytes = dest_path.stat().st_size
                    elif part_path.exists() and part_path.stat().st_size > 0:
                        # Partial .part file exists on disk
                        part_size = part_path.stat().st_size
                        dl.downloaded_bytes = part_size
                        dl.status = DownloadStatus.PENDING
                        logger.info(f"Recovered partial download {dl.id} with {part_size} bytes already downloaded.")
                    else:
                        if dl.status != DownloadStatus.COMPLETED or dl.id in unstacked_scene_dl_ids:
                            dl.status = DownloadStatus.PENDING
                            dl.downloaded_bytes = 0

                # Mark job as QUEUED for worker engine to resume
                job.status = JobStatus.QUEUED
                recovered_count += 1
                db.commit()

                # Resume job in job engine
                job_engine.resume_job(job.id, db)
                logger.info(f"Job {job.id} successfully recovered and enqueued for resume.")

            return recovered_count
        except Exception as e:
            logger.error(f"Error during crash recovery: {e}")
            return 0
        finally:
            db.close()


crash_recovery_manager = CrashRecoveryManager()
