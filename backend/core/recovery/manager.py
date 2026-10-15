import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import Job, Download, JobStatus, DownloadStatus
from backend.core.jobs.engine import job_engine

logger = logging.getLogger("geoharvest.recovery")


class CrashRecoveryManager:
    """Inspects SQLite on application startup, recovers interrupted jobs, checks .part files, and resumes."""

    @classmethod
    def recover_interrupted_jobs(cls):
        db: Session = SessionLocal()
        try:
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
                downloads = db.query(Download).filter(Download.job_id == job.id).all()
                for dl in downloads:
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
                        if dl.status != DownloadStatus.COMPLETED:
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
