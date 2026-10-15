import asyncio
import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from sqlalchemy.orm import Session
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import Job, Download, Dataset, Asset, JobStatus, DownloadStatus
from backend.app.schemas.schemas import SearchResultItem
from backend.core.download.engine import DownloadEngine, DownloadCancelledException
from backend.core.catalog.engine import catalog_engine


class JobEngine:
    def __init__(self, max_workers: int = settings.max_download_workers):
        self.max_workers = max_workers
        self.download_engine = DownloadEngine(chunk_size=settings.chunk_size)
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._cancellation_events: Dict[str, asyncio.Event] = {}
        self._event_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._semaphore = asyncio.Semaphore(max_workers)

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self._event_listeners.append(callback)

    def _broadcast(self, event_data: Dict[str, Any]):
        for listener in self._event_listeners:
            try:
                listener(event_data)
            except Exception:
                pass

    def create_harvest_job(
        self,
        name: str,
        scenes: List[SearchResultItem],
        selected_bands: List[str],
        db: Session,
        destination_dir: Optional[str] = None,
        aoi: Optional[Dict[str, Any]] = None,
        is_toposheet: bool = False
    ) -> Job:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow()

        # Map band aliases
        band_aliases = {
            "b02": ["b02", "blue"],
            "b03": ["b03", "green"],
            "b04": ["b04", "red"],
            "b08": ["b08", "nir"],
            "b05": ["b05", "rededge1"],
            "b06": ["b06", "rededge2"],
            "b07": ["b07", "rededge3"],
            "b11": ["b11", "swir16"],
            "b12": ["b12", "swir22"],
            "visual": ["visual", "tci"],
            "thumbnail": ["thumbnail", "rendered_preview"],
        }
        normalized_requested = set()
        for b in selected_bands:
            b_lower = b.lower()
            normalized_requested.add(b_lower)
            if b_lower in band_aliases:
                normalized_requested.update(band_aliases[b_lower])

        # Resolve destination root
        import re
        if destination_dir and str(destination_dir).strip():
            dest_root = Path(str(destination_dir).strip()).expanduser().resolve()
        else:
            dest_root = settings.downloads_dir.resolve()
        dest_root.mkdir(parents=True, exist_ok=True)

        # Sanitize task name for folder hierarchy
        safe_task_name = re.sub(r'[^\w\-.]', '_', (name or "harvest_task").strip()).strip('._')
        if not safe_task_name:
            safe_task_name = "harvest_task"

        job = Job(
            id=job_id,
            type="harvest",
            status=JobStatus.QUEUED,
            progress=0.0,
            created_at=now,
            job_metadata={
                "name": name,
                "task_name": safe_task_name,
                "destination_dir": str(dest_root),
                "scene_count": len(scenes),
                "selected_bands": selected_bands,
                "scenes": [s.model_dump() for s in scenes],
                "aoi": aoi,
                "is_toposheet": is_toposheet
            }
        )
        db.add(job)

        total_downloads = 0
        from backend.app.models.models import Dataset, Asset

        for scene in scenes:
            # Determine acquisition year (4-digit) and month (2-digit 01-12)
            year = None
            month = None
            if scene.datetime:
                try:
                    dt = datetime.datetime.fromisoformat(scene.datetime.replace("Z", "+00:00"))
                    year = f"{dt.year:04d}"
                    month = f"{dt.month:02d}"
                except Exception:
                    pass

            if not year or not month:
                # Try parsing timestamp from scene id (e.g. S2A_MSIL2A_20240915T... or LC08_..._20240915_...)
                m = re.search(r'(\d{4})(\d{2})\d{2}', scene.id)
                if m:
                    year = m.group(1)
                    month = m.group(2)
                else:
                    now_utc = datetime.datetime.utcnow()
                    year = f"{now_utc.year:04d}"
                    month = f"{now_utc.month:02d}"

            safe_scene_name = re.sub(r'[^\w\-.]', '_', scene.id.strip()).strip('._')
            if not safe_scene_name:
                safe_scene_name = scene.id

            # Hierarchical structure: task_name > year > month > scene_name
            scene_dir = dest_root / safe_task_name / str(year) / str(month) / safe_scene_name
            scene_dir.mkdir(parents=True, exist_ok=True)

            # Ensure Dataset record exists
            dataset = db.query(Dataset).filter(Dataset.id == scene.id).first()
            if not dataset:
                dataset = Dataset(
                    id=scene.id,
                    provider_id=scene.provider_id,
                    collection=scene.collection,
                    dataset_id=scene.id,
                    title=scene.title or scene.id,
                    bbox=scene.bbox,
                    geometry=scene.geometry,
                    cloud_cover=scene.cloud_cover,
                    resolution=scene.resolution_meters
                )
                db.add(dataset)
                db.flush()

            matched_assets = set()
            for asset_key, asset in scene.assets.items():
                k_lower = asset_key.lower()
                band_lower = asset.band.lower() if asset.band else ""
                is_match = (
                    not normalized_requested or
                    "all" in normalized_requested or
                    k_lower in normalized_requested or
                    band_lower in normalized_requested or
                    any(alias in normalized_requested for alias in band_aliases.get(k_lower, []))
                )

                if is_match and asset_key not in matched_assets:
                    matched_assets.add(asset_key)
                    # Determine extension
                    if "jp2" in (asset.mime_type or "") or asset.url.lower().endswith(".jp2"):
                        ext = ".jp2"
                    elif "tif" in asset.url.lower() or "tiff" in (asset.mime_type or ""):
                        ext = ".tif"
                    elif "jpeg" in (asset.mime_type or "") or "jpg" in asset.url.lower():
                        ext = ".jpg"
                    elif "pdf" in asset.url.lower() or "pdf" in (asset.mime_type or ""):
                        ext = ".pdf"
                    elif "zip" in asset.url.lower() or "zip" in (asset.mime_type or ""):
                        ext = ".zip"
                    else:
                        ext = ".tif"
                    dest_file = scene_dir / f"{scene.id}_{asset_key}{ext}"
                    asset_db_id = f"{scene.id}_{asset_key}"

                    # Ensure Asset record exists
                    asset_rec = db.query(Asset).filter(Asset.id == asset_db_id).first()
                    if not asset_rec:
                        asset_rec = Asset(
                            id=asset_db_id,
                            dataset_id=scene.id,
                            asset_name=asset_key,
                            url=asset.url,
                            size=asset.size_bytes or 0,
                            mime_type=asset.mime_type,
                            band=asset.band,
                            status="pending"
                        )
                        db.add(asset_rec)
                        db.flush()

                    dl = Download(
                        id=f"dl_{uuid.uuid4().hex[:12]}",
                        job_id=job_id,
                        asset_id=asset_db_id,
                        destination=str(dest_file.resolve()),
                        total_bytes=asset.size_bytes or 0,
                        downloaded_bytes=0,
                        status=DownloadStatus.PENDING,
                        attempt_count=0,
                        range_supported=True,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(dl)
                    total_downloads += 1

        db.commit()
        db.refresh(job)

        # Start execution in background if event loop is running
        self._cancellation_events[job_id] = asyncio.Event()
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._run_job(job_id))
            self._active_tasks[job_id] = task
        except RuntimeError:
            pass

        self._broadcast({"type": "job_created", "job_id": job_id, "status": "QUEUED"})
        return job

    async def _run_job(self, job_id: str):
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job or job.status in [JobStatus.PAUSED, JobStatus.CANCELLED]:
                return

            job.status = JobStatus.RUNNING
            job.started_at = datetime.datetime.utcnow()
            db.commit()
            self._broadcast({"type": "job_status", "job_id": job_id, "status": "RUNNING"})

            # Gather pending downloads
            downloads = db.query(Download).filter(
                Download.job_id == job_id,
                Download.status.in_([DownloadStatus.PENDING, DownloadStatus.RETRYING, DownloadStatus.DOWNLOADING])
            ).all()

            scenes_meta = job.job_metadata.get("scenes", [])
            # Map asset url lookup
            asset_urls: Dict[str, str] = {}
            scene_info_map: Dict[str, Dict[str, Any]] = {}
            for s in scenes_meta:
                scene_info_map[s["id"]] = s
                for a_key, a_val in s.get("assets", {}).items():
                    asset_urls[f"{s['id']}_{a_key}"] = a_val.get("url")

            cancel_event = self._cancellation_events.get(job_id)

            def update_and_broadcast_job_progress(session: Session, j_id: str):
                try:
                    all_dls = session.query(Download).filter(Download.job_id == j_id).all()
                    comp = sum(1 for d in all_dls if d.status == DownloadStatus.COMPLETED)
                    tot = len(all_dls)
                    tot_b = sum(d.total_bytes for d in all_dls)
                    dn_b = sum(d.downloaded_bytes for d in all_dls)

                    if tot_b > 0:
                        pct = round((dn_b / tot_b * 100.0), 1)
                    elif tot > 0:
                        pct = round((comp / tot * 100.0), 1)
                    else:
                        pct = 0.0

                    j_rec = session.query(Job).filter(Job.id == j_id).first()
                    if j_rec and j_rec.status == JobStatus.RUNNING:
                        j_rec.progress = pct
                        session.commit()

                    self._broadcast({
                        "type": "job_progress",
                        "job_id": j_id,
                        "progress": pct,
                        "completed_downloads": comp,
                        "total_downloads": tot,
                        "downloaded_bytes": dn_b,
                        "total_bytes": tot_b,
                    })
                except Exception:
                    pass

            async def process_download(dl_id: str):
                async with self._semaphore:
                    if cancel_event and cancel_event.is_set():
                        return

                    sub_db = SessionLocal()
                    try:
                        dl = sub_db.query(Download).filter(Download.id == dl_id).first()
                        if not dl or dl.status == DownloadStatus.COMPLETED:
                            return

                        url = asset_urls.get(dl.asset_id)
                        if not url:
                            dl.status = DownloadStatus.FAILED
                            dl.last_error = "Asset URL not found"
                            sub_db.commit()
                            self._broadcast({
                                "type": "download_progress",
                                "job_id": job_id,
                                "download_id": dl_id,
                                "asset_id": dl.asset_id,
                                "downloaded_bytes": dl.downloaded_bytes,
                                "total_bytes": dl.total_bytes,
                                "speed_bytes_sec": 0.0,
                                "status": dl.status.value,
                                "error": dl.last_error
                            })
                            update_and_broadcast_job_progress(sub_db, job_id)
                            return

                        dest = Path(dl.destination)

                        def on_progress(downloaded: int, total: int, speed: float, status: DownloadStatus, err: Optional[str]):
                            p_db = SessionLocal()
                            try:
                                d_rec = p_db.query(Download).filter(Download.id == dl_id).first()
                                if d_rec:
                                    d_rec.downloaded_bytes = downloaded
                                    if total > 0:
                                        d_rec.total_bytes = total
                                    d_rec.status = status
                                    d_rec.last_error = err
                                    d_rec.updated_at = datetime.datetime.utcnow()
                                    p_db.commit()
                            finally:
                                p_db.close()

                            # Broadcast real-time update
                            self._broadcast({
                                "type": "download_progress",
                                "job_id": job_id,
                                "download_id": dl_id,
                                "asset_id": dl.asset_id,
                                "downloaded_bytes": downloaded,
                                "total_bytes": total,
                                "speed_bytes_sec": speed,
                                "status": status.value,
                                "error": err
                            })

                        # Resolve authentication headers if provider requires credentials
                        download_headers = {}
                        if "bhoonidhi" in url:
                            from backend.core.credentials.manager import CredentialManager
                            cm = CredentialManager()
                            download_headers = await cm.get_bhoonidhi_auth_headers()
                        elif "dataspace.copernicus.eu" in url and getattr(settings, "cdse_access_token", None):
                            download_headers = {"Authorization": f"Bearer {settings.cdse_access_token}"}

                        # Execute download with resume and .part support
                        success = await self.download_engine.download_file(
                            url=url,
                            destination_path=dest,
                            expected_size=dl.total_bytes if dl.total_bytes > 0 else None,
                            progress_callback=on_progress,
                            cancellation_event=cancel_event,
                            headers=download_headers if download_headers else None
                        )

                        dl = sub_db.query(Download).filter(Download.id == dl_id).first()
                        if success:
                            dl.status = DownloadStatus.COMPLETED
                            if dl.total_bytes > 0:
                                dl.downloaded_bytes = dl.total_bytes
                            dl.last_error = None
                            asset_rec = sub_db.query(Asset).filter(Asset.id == dl.asset_id).first()
                            if asset_rec:
                                asset_rec.local_path = str(dest.resolve())
                                asset_rec.status = "downloaded"
                        elif cancel_event and cancel_event.is_set():
                            dl.status = DownloadStatus.PAUSED
                        else:
                            dl.status = DownloadStatus.FAILED
                        sub_db.commit()

                        # Broadcast completion status and update aggregate progress
                        self._broadcast({
                            "type": "download_progress",
                            "job_id": job_id,
                            "download_id": dl_id,
                            "asset_id": dl.asset_id,
                            "downloaded_bytes": dl.downloaded_bytes,
                            "total_bytes": dl.total_bytes,
                            "speed_bytes_sec": 0.0,
                            "status": dl.status.value,
                            "error": dl.last_error
                        })
                        update_and_broadcast_job_progress(sub_db, job_id)

                    except DownloadCancelledException:
                        dl = sub_db.query(Download).filter(Download.id == dl_id).first()
                        if dl:
                            dl.status = DownloadStatus.PAUSED
                            sub_db.commit()
                            self._broadcast({
                                "type": "download_progress",
                                "job_id": job_id,
                                "download_id": dl_id,
                                "asset_id": dl.asset_id,
                                "downloaded_bytes": dl.downloaded_bytes,
                                "total_bytes": dl.total_bytes,
                                "speed_bytes_sec": 0.0,
                                "status": dl.status.value,
                                "error": None
                            })
                            update_and_broadcast_job_progress(sub_db, job_id)
                    except Exception as ex:
                        dl = sub_db.query(Download).filter(Download.id == dl_id).first()
                        if dl:
                            dl.status = DownloadStatus.FAILED
                            dl.last_error = str(ex)
                            sub_db.commit()
                            self._broadcast({
                                "type": "download_progress",
                                "job_id": job_id,
                                "download_id": dl_id,
                                "asset_id": dl.asset_id,
                                "downloaded_bytes": dl.downloaded_bytes,
                                "total_bytes": dl.total_bytes,
                                "speed_bytes_sec": 0.0,
                                "status": dl.status.value,
                                "error": str(ex)
                            })
                            update_and_broadcast_job_progress(sub_db, job_id)
                    finally:
                        sub_db.close()

            # Execute downloads concurrently with semaphore
            tasks = [asyncio.create_task(process_download(d.id)) for d in downloads]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Check status of all downloads
            db.expire_all()
            all_dls = db.query(Download).filter(Download.job_id == job_id).all()
            completed = sum(1 for d in all_dls if d.status == DownloadStatus.COMPLETED)
            failed = sum(1 for d in all_dls if d.status == DownloadStatus.FAILED)
            paused = sum(1 for d in all_dls if d.status == DownloadStatus.PAUSED)
            total = len(all_dls)

            tot_bytes = sum(d.total_bytes for d in all_dls)
            dn_bytes = sum(d.downloaded_bytes for d in all_dls)
            job.progress = round((dn_bytes / tot_bytes * 100.0), 1) if tot_bytes > 0 else (100.0 if completed == total and total > 0 else 0.0)

            if cancel_event and cancel_event.is_set():
                job.status = JobStatus.PAUSED
            elif completed == total:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.datetime.utcnow()
                job.progress = 100.0

                # Catalog all scenes in local STAC catalog
                for s_id, s_info in scene_info_map.items():
                    scene_dls = [d for d in all_dls if d.asset_id and d.asset_id.startswith(s_id)]
                    downloaded_assets: Dict[str, Path] = {}
                    for dl in scene_dls:
                        a_key = dl.asset_id.split(f"{s_id}_")[-1]
                        downloaded_assets[a_key] = Path(dl.destination)

                    catalog_engine.add_scene_to_catalog(
                        collection_id=s_info.get("collection", "sentinel-2-l2a"),
                        scene_id=s_id,
                        geometry=s_info.get("geometry", {}),
                        bbox=s_info.get("bbox", [0, 0, 0, 0]),
                        acquisition_time=s_info.get("datetime", ""),
                        downloaded_assets=downloaded_assets,
                        db=db
                    )
            elif failed > 0:
                job.status = JobStatus.FAILED
                job.error = f"{failed} of {total} assets failed to download"
            else:
                job.status = JobStatus.PAUSED

            db.commit()
            self._broadcast({
                "type": "job_status",
                "job_id": job_id,
                "status": job.status.value,
                "progress": job.progress,
                "completed_downloads": completed,
                "total_downloads": total
            })


        finally:
            db.close()
            if job_id in self._active_tasks:
                del self._active_tasks[job_id]

    def pause_job(self, job_id: str, db: Session) -> bool:
        if job_id in self._cancellation_events:
            self._cancellation_events[job_id].set()

        job = db.query(Job).filter(Job.id == job_id).first()
        if job and job.status == JobStatus.RUNNING:
            job.status = JobStatus.PAUSED
            db.commit()
            self._broadcast({"type": "job_status", "job_id": job_id, "status": "PAUSED"})
            return True
        return False

    def resume_job(self, job_id: str, db: Session) -> bool:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status not in [JobStatus.PAUSED, JobStatus.FAILED, JobStatus.QUEUED]:
            return False

        # Reset paused/failed downloads to pending
        downloads = db.query(Download).filter(
            Download.job_id == job_id,
            Download.status.in_([DownloadStatus.PAUSED, DownloadStatus.FAILED, DownloadStatus.RETRYING])
        ).all()
        for d in downloads:
            d.status = DownloadStatus.PENDING
        
        job.status = JobStatus.QUEUED
        db.commit()

        self._cancellation_events[job_id] = asyncio.Event()
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._run_job(job_id))
            self._active_tasks[job_id] = task
        except RuntimeError:
            pass

        self._broadcast({"type": "job_status", "job_id": job_id, "status": "QUEUED"})
        return True

    def cancel_job(self, job_id: str, db: Session) -> bool:
        if job_id in self._cancellation_events:
            self._cancellation_events[job_id].set()

        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.CANCELLED
            downloads = db.query(Download).filter(Download.job_id == job_id).all()
            for d in downloads:
                if d.status != DownloadStatus.COMPLETED:
                    d.status = DownloadStatus.CANCELLED
            db.commit()
            self._broadcast({"type": "job_status", "job_id": job_id, "status": "CANCELLED"})
            return True
        return False


job_engine = JobEngine()
