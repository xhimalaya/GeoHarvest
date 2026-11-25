import asyncio
import copy
import datetime
import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import (
    Job,
    Download,
    Dataset,
    Asset,
    AssetLineage,
    JobStatus,
    DownloadStatus,
)
from backend.app.schemas.schemas import SearchResultItem
from backend.core.download.engine import DownloadEngine, DownloadCancelledException
from backend.core.geoserver import geoserver_manager
from backend.core.catalog.engine import catalog_engine
from backend.core.crs.engine import STRICT_OUTPUT_CRS, enforce_strict_epsg4326
from backend.core.processing.executor import GeoProcessExecutor
from backend.core.processing.workflows import jobs as workflow_jobs
from backend.core.processing.scene_stacker import (
    scene_stacking_service,
    run_scene_stack_task,
    run_single_raster_publish_task,
    reproject_file_to_crs_task,
    normalize_target_crs,
)
from backend.core.satellites.bands import (
    resolve_scene_band_selection,
    sanitize_path_component,
)
from backend.core.satellites.catalog import master_catalog

logger = logging.getLogger("geoharvest.jobs.engine")


def _extract_scene_year_month(scene: SearchResultItem) -> Tuple[str, str, Optional[datetime.datetime]]:
    """Extract 4-digit year, 2-digit month, and naive UTC datetime from a scene."""
    acq_dt: Optional[datetime.datetime] = None
    year: Optional[str] = None
    month: Optional[str] = None

    if scene.datetime:
        try:
            dt = datetime.datetime.fromisoformat(scene.datetime.replace("Z", "+00:00"))
            year = f"{dt.year:04d}"
            month = f"{dt.month:02d}"
            acq_dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            pass

    if not year or not month:
        m = re.search(r"(\d{4})(\d{2})(\d{2})", scene.id or "")
        if m:
            year, month = m.group(1), m.group(2)
            if acq_dt is None:
                try:
                    acq_dt = datetime.datetime(int(year), int(month), int(m.group(3)))
                except Exception:
                    pass
        else:
            now_utc = datetime.datetime.utcnow()
            year = f"{now_utc.year:04d}"
            month = f"{now_utc.month:02d}"

    return str(year), str(month), acq_dt


def _infer_platform_name(collection: Optional[str]) -> Optional[str]:
    if not collection:
        return None
    coll_str = str(collection)
    for mission in master_catalog.list_missions():
        if mission.collection_id == coll_str or mission.id == coll_str:
            return mission.name
    return None


def _cleanup_staging_dir(staging_dir_str: Optional[str]) -> None:
    """Remove scene staging folder and prune empty .staging parent directories."""
    if not staging_dir_str:
        return
    staging_path = Path(staging_dir_str)
    if staging_path.exists():
        shutil.rmtree(staging_path, ignore_errors=True)
    # Prune empty .staging/<job_id> and .staging directories cleanly
    for parent in (staging_path.parent, staging_path.parent.parent):
        try:
            if parent.exists() and parent.is_dir() and not any(parent.iterdir()):
                if parent.name == ".staging" or parent.parent.name == ".staging":
                    parent.rmdir()
        except Exception:
            pass


def resolve_download_byte_progress(
    status: DownloadStatus,
    downloaded_bytes: Optional[int],
    total_bytes: Optional[int],
) -> Tuple[int, int, float]:
    """Normalize (downloaded_bytes, total_bytes, progress_percentage) for a download record."""
    dn_raw = max(0, downloaded_bytes or 0)
    tot_raw = max(0, total_bytes or 0)
    if status == DownloadStatus.COMPLETED:
        final_total = max(tot_raw, dn_raw)
        return final_total, final_total, 100.0
    dn = min(tot_raw, dn_raw) if tot_raw > 0 else dn_raw
    pct = round((dn / tot_raw * 100.0), 1) if tot_raw > 0 else 0.0
    return dn, tot_raw, min(100.0, max(0.0, pct))


def compute_job_progress_stats(all_dls: List[Download]) -> Tuple[int, int, int, int, float]:
    """Aggregate completed count, byte totals, and overall completion percentage for a job."""
    comp = sum(1 for d in all_dls if d.status == DownloadStatus.COMPLETED)
    tot = len(all_dls)
    tot_b = 0
    dn_b = 0
    for d in all_dls:
        item_dn, item_tot, _ = resolve_download_byte_progress(d.status, d.downloaded_bytes, d.total_bytes)
        tot_b += item_tot
        dn_b += item_dn

    if tot_b > 0:
        pct = min(100.0, round((dn_b / tot_b * 100.0), 1))
    elif tot > 0:
        pct = round((comp / tot * 100.0), 1)
    else:
        pct = 0.0
    return comp, tot, tot_b, dn_b, pct


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

    async def _publish_to_geoserver(self, path: Path) -> Optional[Dict[str, Any]]:
        """Mirror/publish a finalized download to GeoServer without altering job completion."""
        if not settings.geoserver_enabled or ".staging" in path.parts:
            return None
        try:
            publish_result = await geoserver_manager.ingest(path)
            if publish_result.get("published"):
                logger.info(
                    "Published raster to GeoServer WMS: %s",
                    publish_result.get("layer"),
                )
            return publish_result
        except Exception as geoserver_exc:
            # GeoServer publishing must not change the download or scene's success state.
            logger.warning(
                "Download completed, but GeoServer sync failed for %s: %s",
                path,
                geoserver_exc,
            )
            return {"published": False, "error": str(geoserver_exc)}

    def create_harvest_job(
        self,
        name: str,
        scenes: List[SearchResultItem],
        selected_bands: List[str],
        db: Session,
        destination_dir: Optional[str] = None,
        aoi: Optional[Dict[str, Any]] = None,
        is_toposheet: bool = False,
        target_resolution: Union[str, float] = "finest",
        resampling_method: str = "bilinear",
        allow_reproject: bool = False,
        target_crs: Optional[str] = "EPSG:4326",
        order_by: Optional[str] = None,
    ) -> Job:
        try:
            resolved_target_crs = enforce_strict_epsg4326(target_crs, reject_invalid=True)
        except Exception as exc:
            raise ValueError(f"Invalid target_crs '{target_crs}': {exc}") from exc

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow()

        # Resolve destination root
        if destination_dir and str(destination_dir).strip():
            dest_root = Path(str(destination_dir).strip()).expanduser().resolve()
        else:
            dest_root = settings.downloads_dir.resolve()
        dest_root.mkdir(parents=True, exist_ok=True)

        safe_task_name = sanitize_path_component(name, default="harvest_task")

        # Insert Job row before Download children so foreign key constraints always hold on flush
        job = Job(
            id=job_id,
            type="harvest",
            status=JobStatus.QUEUED,
            progress=0.0,
            created_at=now,
            job_metadata={},
        )
        db.add(job)
        db.flush()

        scene_plans: Dict[str, Dict[str, Any]] = {}
        dl_to_scene: Dict[str, str] = {}
        scene_order: List[str] = []
        deduped_scenes: List[SearchResultItem] = []
        seen_scene_ids: set[str] = set()

        for scene in scenes:
            if scene.id in seen_scene_ids:
                continue
            seen_scene_ids.add(scene.id)
            deduped_scenes.append(scene)
            scene_order.append(scene.id)

            year, month, acq_dt = _extract_scene_year_month(scene)
            safe_scene_name = sanitize_path_component(scene.id, default="scene")
            safe_dataset_name = sanitize_path_component(scene.collection, default="satellite_dataset")

            # Ensure Dataset record exists
            dataset = db.query(Dataset).filter(Dataset.id == scene.id).first()
            if not dataset:
                dataset = Dataset(
                    id=scene.id,
                    provider_id=scene.provider_id,
                    collection=scene.collection,
                    dataset_id=scene.id,
                    title=scene.title or scene.id,
                    platform=_infer_platform_name(scene.collection),
                    acquisition_date=acq_dt,
                    bbox=scene.bbox,
                    geometry=scene.geometry,
                    cloud_cover=scene.cloud_cover,
                    resolution=scene.resolution_meters,
                )
                db.add(dataset)
                db.flush()
            else:
                if dataset.acquisition_date is None and acq_dt is not None:
                    dataset.acquisition_date = acq_dt
                if dataset.platform is None:
                    dataset.platform = _infer_platform_name(scene.collection)

            band_specs: List[Dict[str, Any]] = []
            scene_download_ids: List[str] = []
            skipped_ancillary: List[str] = []
            staging_dir_str: Optional[str] = None
            final_output_str: Optional[str] = None

            if is_toposheet:
                mode = "direct"
                stack_enabled = False
                effective_order_by = "explicit"
                scene_dir = dest_root / safe_task_name / str(year) / str(month) / safe_scene_name
                scene_dir.mkdir(parents=True, exist_ok=True)
                req_lower = {b.lower() for b in (selected_bands or [])}
                all_items = list(scene.assets.items())
                chosen_items = [
                    (k, v)
                    for k, v in all_items
                    if not req_lower
                    or "all" in req_lower
                    or k.lower() in req_lower
                    or (v.band and v.band.lower() in req_lower)
                ]
                if not chosen_items:
                    chosen_items = all_items

                selected_entries = []
                for a_key, a_val in chosen_items:
                    from backend.core.satellites.bands import infer_asset_extension

                    ext = infer_asset_extension(a_key, a_val)
                    dest_file = scene_dir / f"{scene.id}_{a_key}{ext}"
                    selected_entries.append((a_key, a_key, a_key, a_val, dest_file))
            else:
                resolution = resolve_scene_band_selection(
                    scene,
                    selected_bands,
                    include_ancillary_with_spectral=False,
                    fallback_to_primary=True,
                )
                mode = resolution.mode
                stack_enabled = resolution.is_stackable and len(resolution.selected_assets) > 0
                effective_order_by = order_by or resolution.order_by
                skipped_ancillary = list(resolution.skipped_ancillary)

                selected_entries = []
                if stack_enabled:
                    staging_dir = dest_root / ".staging" / job_id / safe_scene_name
                    staging_dir.mkdir(parents=True, exist_ok=True)
                    staging_dir_str = str(staging_dir.resolve())
                    final_output_path = (
                        dest_root
                        / safe_task_name
                        / safe_dataset_name
                        / str(year)
                        / str(month)
                        / f"{safe_scene_name}.tif"
                    )
                    final_output_str = str(final_output_path.resolve())
                    for idx, resolved in enumerate(resolution.selected_assets):
                        safe_asset_key = sanitize_path_component(
                            resolved.asset_key, default=f"band_{idx + 1}"
                        )
                        dest_file = staging_dir / f"{safe_scene_name}_{safe_asset_key}{resolved.extension}"
                        selected_entries.append(
                            (
                                resolved.asset_key,
                                resolved.requested_band,
                                resolved.canonical_band,
                                resolved.asset,
                                dest_file,
                            )
                        )
                else:
                    direct_dir = (
                        dest_root
                        / safe_task_name
                        / safe_dataset_name
                        / str(year)
                        / str(month)
                        / safe_scene_name
                    )
                    direct_dir.mkdir(parents=True, exist_ok=True)
                    for idx, resolved in enumerate(resolution.selected_assets):
                        safe_asset_key = sanitize_path_component(
                            resolved.asset_key, default=f"asset_{idx + 1}"
                        )
                        dest_file = direct_dir / f"{safe_scene_name}_{safe_asset_key}{resolved.extension}"
                        selected_entries.append(
                            (
                                resolved.asset_key,
                                resolved.requested_band,
                                resolved.canonical_band,
                                resolved.asset,
                                dest_file,
                            )
                        )

            for idx, (asset_key, req_band, canon_band, asset, dest_file) in enumerate(selected_entries):
                asset_db_id = f"{scene.id}_{asset_key}"
                asset_rec = db.query(Asset).filter(Asset.id == asset_db_id).first()
                if not asset_rec:
                    asset_rec = Asset(
                        id=asset_db_id,
                        dataset_id=scene.id,
                        asset_name=asset_key,
                        url=asset.url,
                        asset_type="staging" if stack_enabled else "local_raw",
                        size=asset.size_bytes or 0,
                        mime_type=asset.mime_type,
                        band=asset.band,
                        status="pending",
                    )
                    db.add(asset_rec)
                    db.flush()
                else:
                    asset_rec.url = asset.url
                    if asset.size_bytes:
                        asset_rec.size = asset.size_bytes
                    if asset.mime_type and not asset_rec.mime_type:
                        asset_rec.mime_type = asset.mime_type
                    if asset.band and not asset_rec.band:
                        asset_rec.band = asset.band

                dl_id = f"dl_{uuid.uuid4().hex[:12]}"
                dl = Download(
                    id=dl_id,
                    job_id=job_id,
                    asset_id=asset_db_id,
                    destination=str(dest_file.resolve()),
                    total_bytes=asset.size_bytes or 0,
                    downloaded_bytes=0,
                    status=DownloadStatus.PENDING,
                    attempt_count=0,
                    range_supported=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(dl)
                scene_download_ids.append(dl_id)
                dl_to_scene[dl_id] = scene.id
                band_specs.append(
                    {
                        "key": asset_key,
                        "requested_band": req_band,
                        "canonical_band": canon_band,
                        "path": str(dest_file.resolve()),
                        "band_id": asset.band,
                        "order_index": idx,
                        "download_id": dl_id,
                        "asset_id": asset_db_id,
                    }
                )

            scene_plans[scene.id] = {
                "scene_id": scene.id,
                "safe_scene_name": safe_scene_name,
                "collection": scene.collection,
                "provider_id": scene.provider_id,
                "year": str(year),
                "month": str(month),
                "datetime": scene.datetime or "",
                "bbox": list(scene.bbox or [0, 0, 0, 0]),
                "geometry": dict(scene.geometry or {}),
                "mode": mode,
                "stack_enabled": stack_enabled,
                "order_by": effective_order_by,
                "staging_dir": staging_dir_str,
                "final_output_path": final_output_str,
                "download_ids": scene_download_ids,
                "bands": band_specs,
                "skipped_ancillary": skipped_ancillary,
                "status": "downloading",
                "error": None,
                "output_metadata": None,
                "warnings": [],
            }

        job.job_metadata = {
            "name": name,
            "task_name": safe_task_name,
            "destination_dir": str(dest_root),
            "scene_count": len(deduped_scenes),
            "selected_bands": selected_bands,
            "scenes": [s.model_dump() for s in deduped_scenes],
            "aoi": aoi,
            "is_toposheet": is_toposheet,
            "stacking_config": {
                "target_resolution": target_resolution,
                "resampling_method": resampling_method,
                "allow_reproject": allow_reproject,
                "target_crs": resolved_target_crs,
                "order_by": order_by,
            },
            "scene_order": scene_order,
            "scene_plans": scene_plans,
            "dl_to_scene": dl_to_scene,
        }
        flag_modified(job, "job_metadata")
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

            if job.type == workflow_jobs.WORKFLOW_JOB:
                db.close()
                await workflow_jobs.run(job_id, self._broadcast)
                return

            job.status = JobStatus.RUNNING
            job.started_at = datetime.datetime.utcnow()
            job.error = None
            db.commit()
            self._broadcast({"type": "job_status", "job_id": job_id, "status": "RUNNING"})

            # Gather pending downloads
            downloads = db.query(Download).filter(
                Download.job_id == job_id,
                Download.status.in_([DownloadStatus.PENDING, DownloadStatus.RETRYING, DownloadStatus.DOWNLOADING])
            ).all()

            meta_snapshot = dict(job.job_metadata or {})
            scenes_meta = meta_snapshot.get("scenes", [])
            scene_plans_snapshot = meta_snapshot.get("scene_plans")
            has_scene_plans = isinstance(scene_plans_snapshot, dict) and len(scene_plans_snapshot) > 0
            scene_order: List[str] = list(
                meta_snapshot.get("scene_order")
                or (list(scene_plans_snapshot.keys()) if has_scene_plans else [])
            )
            dl_to_scene: Dict[str, str] = dict(meta_snapshot.get("dl_to_scene") or {})
            stacking_cfg: Dict[str, Any] = dict(meta_snapshot.get("stacking_config") or {})
            job_target_crs = STRICT_OUTPUT_CRS

            # Map asset url lookup
            asset_urls: Dict[str, str] = {}
            scene_info_map: Dict[str, Dict[str, Any]] = {}
            for s in scenes_meta:
                scene_info_map[s["id"]] = s
                for a_key, a_val in s.get("assets", {}).items():
                    asset_urls[f"{s['id']}_{a_key}"] = a_val.get("url")

            cancel_event = self._cancellation_events.get(job_id)
            metadata_lock = asyncio.Lock()
            scene_locks: Dict[str, asyncio.Lock] = {
                s_id: asyncio.Lock() for s_id in scene_order
            }

            async def update_scene_plan_metadata(scene_id: str, **updates: Any) -> None:
                async with metadata_lock:
                    m_db = SessionLocal()
                    try:
                        j_rec = m_db.query(Job).filter(Job.id == job_id).first()
                        if not j_rec:
                            return
                        j_meta = copy.deepcopy(j_rec.job_metadata or {})
                        plans = j_meta.get("scene_plans") or {}
                        if scene_id in plans:
                            plans[scene_id].update(updates)
                            j_meta["scene_plans"] = plans
                            j_rec.job_metadata = j_meta
                            flag_modified(j_rec, "job_metadata")
                            m_db.commit()
                    finally:
                        m_db.close()

            async def get_latest_scene_plan(scene_id: str) -> Optional[Dict[str, Any]]:
                async with metadata_lock:
                    m_db = SessionLocal()
                    try:
                        j_rec = m_db.query(Job).filter(Job.id == job_id).first()
                        if not j_rec:
                            return None
                        plans = (j_rec.job_metadata or {}).get("scene_plans") or {}
                        plan_entry = plans.get(scene_id)
                        return copy.deepcopy(plan_entry) if plan_entry else None
                    finally:
                        m_db.close()

            async def finalize_scene(scene_id: str) -> None:
                lock = scene_locks.setdefault(scene_id, asyncio.Lock())
                async with lock:
                    if cancel_event and cancel_event.is_set():
                        return
                    plan = await get_latest_scene_plan(scene_id)
                    if not plan or plan.get("status") == "completed":
                        return

                    dl_ids: List[str] = list(plan.get("download_ids") or [])
                    c_db = SessionLocal()
                    try:
                        if dl_ids:
                            scene_dls = c_db.query(Download).filter(Download.id.in_(dl_ids)).all()
                        else:
                            scene_dls = []
                        dl_by_id = {d.id: d for d in scene_dls}
                        if len(scene_dls) != len(dl_ids):
                            return
                        if any(d.status != DownloadStatus.COMPLETED for d in scene_dls):
                            # Reconcile non-completed download state on the scene plan when appropriate
                            if any(d.status == DownloadStatus.FAILED for d in scene_dls):
                                await update_scene_plan_metadata(
                                    scene_id,
                                    status="failed",
                                    error="One or more band downloads failed",
                                )
                            elif any(d.status == DownloadStatus.CANCELLED for d in scene_dls):
                                await update_scene_plan_metadata(scene_id, status="cancelled")
                            elif any(d.status == DownloadStatus.PAUSED for d in scene_dls):
                                await update_scene_plan_metadata(scene_id, status="paused")
                            return
                    finally:
                        c_db.close()

                    scene_payload = scene_info_map.get(scene_id) or {
                        "id": scene_id,
                        "collection": plan.get("collection"),
                        "provider_id": plan.get("provider_id"),
                        "datetime": plan.get("datetime"),
                        "bbox": plan.get("bbox"),
                        "geometry": plan.get("geometry"),
                        "assets": {},
                    }

                    if not plan.get("stack_enabled"):
                        direct_raster_exts = {".tif", ".tiff", ".jp2", ".img", ".vrt"}
                        direct_crs: Optional[str] = None
                        cat_db = SessionLocal()
                        try:
                            downloaded_assets: Dict[str, Path] = {}
                            for bs in plan.get("bands") or []:
                                did = bs.get("download_id")
                                dl_obj = dl_by_id.get(did)
                                dest_str = dl_obj.destination if dl_obj else bs.get("path")
                                if not dest_str:
                                    continue
                                dest_p = Path(dest_str)
                                if (
                                    job_target_crs
                                    and dest_p.exists()
                                    and dest_p.is_file()
                                    and dest_p.suffix.lower() in direct_raster_exts
                                ):
                                    reproj_res = await GeoProcessExecutor.run_cpu_bound(
                                        reproject_file_to_crs_task,
                                        str(dest_p),
                                        job_target_crs,
                                        stacking_cfg.get("resampling_method", "bilinear"),
                                    )
                                    out_p = Path(reproj_res.get("output_path") or dest_p)
                                    if reproj_res.get("crs"):
                                        direct_crs = reproj_res["crs"]
                                    if out_p != dest_p or reproj_res.get("reprojected"):
                                        dest_p = out_p
                                        bs["path"] = str(out_p)
                                        if did:
                                            db_dl = cat_db.query(Download).filter(Download.id == did).first()
                                            if db_dl:
                                                db_dl.destination = str(out_p)
                                                if out_p.exists():
                                                    sz = out_p.stat().st_size
                                                    db_dl.total_bytes = sz
                                                    db_dl.downloaded_bytes = sz
                                downloaded_assets[bs["key"]] = dest_p
                            cat_db.commit()
                            direct_meta = {"crs": direct_crs} if direct_crs else None
                            try:
                                catalog_engine.add_scene_to_catalog(
                                    collection_id=plan.get("collection") or "sentinel-2-l2a",
                                    scene_id=scene_id,
                                    geometry=plan.get("geometry", {}),
                                    bbox=plan.get("bbox", [0, 0, 0, 0]),
                                    acquisition_time=plan.get("datetime", ""),
                                    downloaded_assets=downloaded_assets,
                                    db=cat_db,
                                    stacked_metadata=direct_meta,
                                )
                            except TypeError:
                                catalog_engine.add_scene_to_catalog(
                                    collection_id=plan.get("collection") or "sentinel-2-l2a",
                                    scene_id=scene_id,
                                    geometry=plan.get("geometry", {}),
                                    bbox=plan.get("bbox", [0, 0, 0, 0]),
                                    acquisition_time=plan.get("datetime", ""),
                                    downloaded_assets=downloaded_assets,
                                    db=cat_db,
                                )
                        finally:
                            cat_db.close()

                        for asset_path in dict.fromkeys(downloaded_assets.values()):
                            await self._publish_to_geoserver(asset_path)

                        await update_scene_plan_metadata(scene_id, status="completed", error=None)
                        self._broadcast({
                            "type": "scene_progress",
                            "job_id": job_id,
                            "scene_id": scene_id,
                            "status": "completed",
                            "mode": plan.get("mode", "direct"),
                        })
                        return

                    # Stackable scene barrier passed: stack & validate before cleanup
                    await update_scene_plan_metadata(scene_id, status="stacking", error=None)
                    final_output_str = plan.get("final_output_path")
                    self._broadcast({
                        "type": "scene_progress",
                        "job_id": job_id,
                        "scene_id": scene_id,
                        "status": "stacking",
                        "output_path": final_output_str,
                    })

                    try:
                        if not final_output_str:
                            raise RuntimeError(f"Scene '{scene_id}' has no final_output_path configured")
                        final_path = Path(final_output_str)

                        # Resolve current band paths from DB downloads
                        raw_band_specs = copy.deepcopy(plan.get("bands") or [])
                        if not raw_band_specs:
                            raise RuntimeError(f"Scene '{scene_id}' has no band downloads to stack")

                        for bs in raw_band_specs:
                            dl_obj = dl_by_id.get(bs.get("download_id"))
                            if dl_obj and dl_obj.destination:
                                bs["path"] = dl_obj.destination

                        mode = plan.get("mode", "stack_bands")
                        order_by = plan.get("order_by", "explicit")

                        if mode == "stack_bands":
                            expected_specs = scene_stacking_service.resolve_band_order(
                                scene_payload, raw_band_specs, order_by=order_by
                            )
                            expected_val_target: Any = expected_specs
                        else:
                            first_path = Path(raw_band_specs[0]["path"])
                            first_key_l = str(raw_band_specs[0]["key"]).lower()
                            if first_path.exists() and first_path.is_file() and first_path.stat().st_size > 0:
                                src_meta = scene_stacking_service.get_stack_metadata(first_path)
                                raw_descs = list(src_meta.get("band_descriptions") or [])
                                if (
                                    src_meta["count"] == 3
                                    and first_key_l in {"visual", "tci", "tci_10m", "tci_20m", "tci_60m"}
                                    and raw_descs in ([], ["Band 1", "Band 2", "Band 3"])
                                ):
                                    expected_val_target = ["Red", "Green", "Blue"]
                                else:
                                    expected_val_target = src_meta["count"]
                            elif first_key_l in {"visual", "tci", "tci_10m", "tci_20m", "tci_60m"}:
                                expected_val_target = ["Red", "Green", "Blue"]
                            else:
                                expected_val_target = None

                        result: Optional[Dict[str, Any]] = None
                        if final_path.exists() and final_path.is_file() and final_path.stat().st_size > 0:
                            existing_val = scene_stacking_service.validate_stacked_output(
                                output_path=final_path,
                                expected_bands=expected_val_target,
                                expected_crs=job_target_crs,
                                check_data_readable=True,
                            )
                            if existing_val.get("valid"):
                                existing_meta = scene_stacking_service.get_stack_metadata(final_path)
                                result = {
                                    "success": True,
                                    "scene_id": scene_id,
                                    "output_path": str(final_path),
                                    "file_size": existing_meta["file_size_bytes"],
                                    "band_count": existing_meta["count"],
                                    "band_keys": [b["key"] for b in raw_band_specs],
                                    "band_descriptions": list(existing_meta["band_descriptions"]),
                                    "crs": existing_meta["crs"],
                                    "resolution": existing_meta["resolution"],
                                    "width": existing_meta["width"],
                                    "height": existing_meta["height"],
                                    "dtype": existing_meta["dtypes"][0] if existing_meta["dtypes"] else None,
                                    "nodata": existing_meta["nodata"],
                                    "tiled": existing_meta["tiled"],
                                    "compression": existing_meta["compression"],
                                    "warnings": ["Reused existing validated scene GeoTIFF"],
                                    "metadata": existing_meta,
                                    "reused_existing": True,
                                }

                        if result is None:
                            for bs in raw_band_specs:
                                p = Path(bs["path"])
                                if not p.exists() or not p.is_file() or p.stat().st_size == 0:
                                    raise FileNotFoundError(
                                        f"Staged band file missing or empty for '{scene_id}' ({bs['key']}): {p}"
                                    )
                            if mode != "stack_bands" and expected_val_target is None:
                                src_meta = scene_stacking_service.get_stack_metadata(raw_band_specs[0]["path"])
                                expected_val_target = src_meta["count"]

                            if mode == "stack_bands":
                                result = await GeoProcessExecutor.run_cpu_bound(
                                    run_scene_stack_task,
                                    scene_payload,
                                    raw_band_specs,
                                    str(final_path),
                                    target_resolution=stacking_cfg.get("target_resolution", "finest"),
                                    resampling_method=stacking_cfg.get("resampling_method", "bilinear"),
                                    allow_reproject=bool(stacking_cfg.get("allow_reproject", False)),
                                    target_crs=job_target_crs,
                                    order_by=order_by,
                                    compression="deflate",
                                    tiled=True,
                                    build_overviews=False,
                                )
                            else:
                                first_band = raw_band_specs[0]
                                result = await GeoProcessExecutor.run_cpu_bound(
                                    run_single_raster_publish_task,
                                    scene_payload,
                                    first_band["key"],
                                    first_band["path"],
                                    str(final_path),
                                    target_crs=job_target_crs,
                                    resampling_method=stacking_cfg.get("resampling_method", "bilinear"),
                                    compression="deflate",
                                    tiled=True,
                                )

                            # Verify final file on disk and validate before cleanup
                            post_val = scene_stacking_service.validate_stacked_output(
                                output_path=final_path,
                                expected_bands=expected_val_target,
                                expected_crs=job_target_crs,
                                check_data_readable=True,
                            )
                            if not post_val.get("valid"):
                                raise RuntimeError(
                                    f"Post-stack validation failed for '{scene_id}': {post_val.get('errors')}"
                                )

                        stacked_meta = {
                            "output_path": str(final_path),
                            "file_size": result.get("file_size"),
                            "band_count": result.get("band_count"),
                            "band_keys": result.get("band_keys"),
                            "band_descriptions": result.get("band_descriptions"),
                            "crs": result.get("crs"),
                            "resolution": result.get("resolution"),
                            "width": result.get("width"),
                            "height": result.get("height"),
                            "dtype": result.get("dtype"),
                            "nodata": result.get("nodata"),
                            "tiled": result.get("tiled"),
                            "compression": result.get("compression"),
                        }

                        # Register stacked scene in STAC catalog, update raw assets & create lineage
                        cat_db = SessionLocal()
                        try:
                            try:
                                catalog_engine.add_scene_to_catalog(
                                    collection_id=plan.get("collection") or "sentinel-2-l2a",
                                    scene_id=scene_id,
                                    geometry=plan.get("geometry", {}),
                                    bbox=plan.get("bbox", [0, 0, 0, 0]),
                                    acquisition_time=plan.get("datetime", ""),
                                    downloaded_assets={"stacked": final_path},
                                    db=cat_db,
                                    stacked_metadata=stacked_meta,
                                )
                            except TypeError:
                                catalog_engine.add_scene_to_catalog(
                                    collection_id=plan.get("collection") or "sentinel-2-l2a",
                                    scene_id=scene_id,
                                    geometry=plan.get("geometry", {}),
                                    bbox=plan.get("bbox", [0, 0, 0, 0]),
                                    acquisition_time=plan.get("datetime", ""),
                                    downloaded_assets={"stacked": final_path},
                                    db=cat_db,
                                )

                            derived_asset = (
                                cat_db.query(Asset)
                                .filter(Asset.id == f"{scene_id}_stacked")
                                .first()
                            )
                            for bs in raw_band_specs:
                                src_asset = (
                                    cat_db.query(Asset)
                                    .filter(Asset.id == bs.get("asset_id"))
                                    .first()
                                )
                                if src_asset:
                                    src_asset.local_path = None
                                    src_asset.status = "processed"
                                    if derived_asset:
                                        existing_lin = (
                                            cat_db.query(AssetLineage)
                                            .filter(
                                                AssetLineage.source_asset_id == src_asset.id,
                                                AssetLineage.derived_asset_id == derived_asset.id,
                                                AssetLineage.operation == "scene_stack",
                                            )
                                            .first()
                                        )
                                        lin_meta = {
                                            "job_id": job_id,
                                            "band_key": bs.get("key"),
                                            "output_path": str(final_path),
                                            "band_count": stacked_meta["band_count"],
                                            "band_descriptions": stacked_meta["band_descriptions"],
                                            "crs": stacked_meta["crs"],
                                        }
                                        if existing_lin:
                                            existing_lin.metadata_info = lin_meta
                                        else:
                                            cat_db.add(
                                                AssetLineage(
                                                    id=f"lin_{uuid.uuid4().hex[:12]}",
                                                    source_asset_id=src_asset.id,
                                                    derived_asset_id=derived_asset.id,
                                                    operation="scene_stack",
                                                    metadata_info=lin_meta,
                                                )
                                            )
                            cat_db.commit()
                        finally:
                            cat_db.close()

                        # Only clean temporary staging folder AFTER final stacked file is confirmed & cataloged
                        _cleanup_staging_dir(plan.get("staging_dir"))

                        publish_result = await self._publish_to_geoserver(final_path)
                        if publish_result:
                            stacked_meta["geoserver"] = publish_result

                        await update_scene_plan_metadata(
                            scene_id,
                            status="completed",
                            error=None,
                            output_metadata=stacked_meta,
                            warnings=list(result.get("warnings") or []),
                        )
                        self._broadcast({
                            "type": "scene_progress",
                            "job_id": job_id,
                            "scene_id": scene_id,
                            "status": "completed",
                            "mode": mode,
                            "output_path": str(final_path),
                            "band_count": stacked_meta["band_count"],
                            "band_descriptions": stacked_meta["band_descriptions"],
                            "file_size": stacked_meta["file_size"],
                        })
                    except Exception as exc:
                        logger.exception("Scene stacking failed for scene %s (job %s)", scene_id, job_id)
                        await update_scene_plan_metadata(
                            scene_id,
                            status="failed",
                            error=str(exc),
                        )
                        self._broadcast({
                            "type": "scene_progress",
                            "job_id": job_id,
                            "scene_id": scene_id,
                            "status": "failed",
                            "error": str(exc),
                        })

            def update_and_broadcast_job_progress(session: Session, j_id: str):
                try:
                    session.expire_all()
                    all_dls = session.query(Download).filter(Download.job_id == j_id).all()
                    comp, tot, tot_b, dn_b, pct = compute_job_progress_stats(all_dls)
                    if has_scene_plans and pct >= 100.0:
                        pct = 95.0

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

            async def process_download(dl_id: str, auto_finalize: bool = True):
                finalize_scene_id: Optional[str] = None
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
                            broadcast_total = total
                            p_db = SessionLocal()
                            try:
                                d_rec = p_db.query(Download).filter(Download.id == dl_id).first()
                                if d_rec:
                                    if total > 0:
                                        d_rec.total_bytes = total
                                    d_rec.downloaded_bytes = (
                                        (d_rec.total_bytes or downloaded)
                                        if status == DownloadStatus.COMPLETED
                                        else downloaded
                                    )
                                    d_rec.status = status
                                    d_rec.last_error = err
                                    d_rec.updated_at = datetime.datetime.utcnow()
                                    p_db.commit()
                                    if d_rec.total_bytes and d_rec.total_bytes > 0:
                                        broadcast_total = d_rec.total_bytes
                            finally:
                                p_db.close()

                            # Broadcast real-time update
                            self._broadcast({
                                "type": "download_progress",
                                "job_id": job_id,
                                "download_id": dl_id,
                                "asset_id": dl.asset_id,
                                "downloaded_bytes": broadcast_total if status == DownloadStatus.COMPLETED and broadcast_total > 0 else downloaded,
                                "total_bytes": broadcast_total,
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

                        # Refresh session state so progress updates made on p_db (e.g. fallback Content-Length) are not overwritten
                        sub_db.expire_all()
                        dl = sub_db.query(Download).filter(Download.id == dl_id).first()
                        if success:
                            actual_bytes = dest.stat().st_size if dest.exists() else 0
                            dl.status = DownloadStatus.COMPLETED
                            if actual_bytes > 0:
                                dl.total_bytes = actual_bytes
                                dl.downloaded_bytes = actual_bytes
                            elif (dl.total_bytes or 0) > 0:
                                dl.downloaded_bytes = dl.total_bytes
                            elif (dl.downloaded_bytes or 0) > 0:
                                dl.total_bytes = dl.downloaded_bytes
                            dl.last_error = None
                            asset_rec = sub_db.query(Asset).filter(Asset.id == dl.asset_id).first()
                            if asset_rec:
                                asset_rec.local_path = str(dest.resolve())
                                asset_rec.status = "downloaded"
                                if actual_bytes > 0:
                                    asset_rec.size = actual_bytes
                            finalize_scene_id = dl_to_scene.get(dl_id)
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

                        if success and ".staging" not in dest.parts and not (has_scene_plans and finalize_scene_id):
                            await self._publish_to_geoserver(dest)

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

                if auto_finalize and finalize_scene_id and has_scene_plans and not (cancel_event and cancel_event.is_set()):
                    await finalize_scene(finalize_scene_id)

            async def try_skip_existing_scene_output(s_id: str) -> bool:
                """If a valid stacked GeoTIFF already exists at final_output_path, mark scene downloads completed without re-downloading."""
                plan = await get_latest_scene_plan(s_id)
                if not plan or not plan.get("stack_enabled"):
                    return False
                final_str = plan.get("final_output_path")
                if not final_str:
                    return False
                final_path = Path(final_str)
                if not final_path.exists() or not final_path.is_file() or final_path.stat().st_size == 0:
                    return False

                raw_band_specs = copy.deepcopy(plan.get("bands") or [])
                if not raw_band_specs:
                    return False

                scene_payload = scene_info_map.get(s_id) or {
                    "id": s_id,
                    "collection": plan.get("collection"),
                    "provider_id": plan.get("provider_id"),
                    "datetime": plan.get("datetime"),
                    "bbox": plan.get("bbox"),
                    "geometry": plan.get("geometry"),
                    "assets": {},
                }
                mode = plan.get("mode", "stack_bands")
                order_by = plan.get("order_by", "explicit")
                if mode == "stack_bands":
                    expected_val_target: Any = scene_stacking_service.resolve_band_order(
                        scene_payload, raw_band_specs, order_by=order_by
                    )
                else:
                    first_key_l = str(raw_band_specs[0]["key"]).lower()
                    expected_val_target = (
                        ["Red", "Green", "Blue"]
                        if first_key_l in {"visual", "tci", "tci_10m", "tci_20m", "tci_60m"}
                        else None
                    )

                existing_val = scene_stacking_service.validate_stacked_output(
                    output_path=final_path,
                    expected_bands=expected_val_target,
                    expected_crs=job_target_crs,
                    check_data_readable=True,
                )
                if not existing_val.get("valid"):
                    return False

                dl_ids = list(plan.get("download_ids") or [])
                if not dl_ids:
                    return False

                s_db = SessionLocal()
                try:
                    s_dls = s_db.query(Download).filter(Download.id.in_(dl_ids)).all()
                    per_band_fallback = max(1, final_path.stat().st_size // max(1, len(dl_ids)))
                    for d_rec in s_dls:
                        if d_rec.status != DownloadStatus.COMPLETED:
                            d_rec.status = DownloadStatus.COMPLETED
                            if (d_rec.total_bytes or 0) <= 0:
                                d_rec.total_bytes = per_band_fallback
                            d_rec.downloaded_bytes = d_rec.total_bytes
                            d_rec.last_error = None
                            self._broadcast({
                                "type": "download_progress",
                                "job_id": job_id,
                                "download_id": d_rec.id,
                                "asset_id": d_rec.asset_id,
                                "downloaded_bytes": d_rec.downloaded_bytes,
                                "total_bytes": d_rec.total_bytes,
                                "speed_bytes_sec": 0.0,
                                "status": DownloadStatus.COMPLETED.value,
                                "error": None,
                            })
                    s_db.commit()
                    update_and_broadcast_job_progress(s_db, job_id)
                finally:
                    s_db.close()
                return True

            if has_scene_plans and scene_order:
                # Keep four scene pipelines active independently of how many bands each scene needs.
                # Limit bands within each scene so the global download pool is shared fairly.
                concurrent_scenes = min(4, len(scene_order), max(1, self.max_workers))
                per_scene_band_workers = max(1, self.max_workers // concurrent_scenes)
                scene_dl_sem = asyncio.Semaphore(concurrent_scenes)
                assigned_dl_ids = {
                    did
                    for s_id in scene_order
                    for did in ((scene_plans_snapshot or {}).get(s_id, {}).get("download_ids") or [])
                }
                unassigned_dl_ids = [d.id for d in downloads if d.id not in assigned_dl_ids]

                async def run_scene_pipeline(s_id: str):
                    if cancel_event and cancel_event.is_set():
                        return
                    s_plan = (scene_plans_snapshot or {}).get(s_id) or {}
                    s_dl_ids = list(s_plan.get("download_ids") or [])
                    async with scene_dl_sem:
                        if cancel_event and cancel_event.is_set():
                            return
                        skipped = await try_skip_existing_scene_output(s_id)
                        if not skipped and s_dl_ids:
                            await update_scene_plan_metadata(s_id, status="downloading", error=None)

                            scene_band_sem = asyncio.Semaphore(per_scene_band_workers)

                            async def process_scene_download(did: str):
                                async with scene_band_sem:
                                    await process_download(did, auto_finalize=False)

                            scene_tasks = [
                                asyncio.create_task(process_scene_download(did))
                                for did in s_dl_ids
                            ]
                            await asyncio.gather(*scene_tasks, return_exceptions=True)

                        # Keep this slot until stacking releases the scene's staged band files.
                        if not (cancel_event and cancel_event.is_set()):
                            await finalize_scene(s_id)

                all_pipeline_tasks = [asyncio.create_task(run_scene_pipeline(s_id)) for s_id in scene_order]
                if unassigned_dl_ids:
                    all_pipeline_tasks.extend(
                        asyncio.create_task(process_download(did, auto_finalize=False))
                        for did in unassigned_dl_ids
                    )
                await asyncio.gather(*all_pipeline_tasks, return_exceptions=True)
            else:
                # Execute downloads concurrently with semaphore
                tasks = [asyncio.create_task(process_download(d.id)) for d in downloads]
                await asyncio.gather(*tasks, return_exceptions=True)

            # Reconcile any remaining scenes (covers resume when downloads already finished prior to pause/failure)
            if has_scene_plans and not (cancel_event and cancel_event.is_set()):
                for s_id in scene_order:
                    await finalize_scene(s_id)

            # Refresh job and evaluate final status
            db.expire_all()
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return
            was_cancelled = (job.status == JobStatus.CANCELLED)

            all_dls = db.query(Download).filter(Download.job_id == job_id).all()
            if was_cancelled:
                for d in all_dls:
                    if d.status != DownloadStatus.COMPLETED:
                        d.status = DownloadStatus.CANCELLED
                db.commit()

            completed, total, tot_bytes, dn_bytes, job.progress = compute_job_progress_stats(all_dls)
            failed = sum(1 for d in all_dls if d.status == DownloadStatus.FAILED)

            if has_scene_plans:
                final_plans = (job.job_metadata or {}).get("scene_plans") or {}
                failed_scenes = [
                    (s_id, sp.get("error"))
                    for s_id, sp in final_plans.items()
                    if sp.get("status") == "failed"
                ]
                incomplete_scenes = [
                    s_id
                    for s_id, sp in final_plans.items()
                    if sp.get("status") != "completed"
                ]

                total_scenes_cnt = max(1, len(final_plans))
                completed_scenes_cnt = total_scenes_cnt - len(incomplete_scenes)
                # Each scene is 90% band download + 10% stacking verification
                non_complete_pct = round(
                    min(
                        99.0,
                        (completed_scenes_cnt * 100.0 + len(incomplete_scenes) * (job.progress * 0.9))
                        / total_scenes_cnt,
                    ),
                    1,
                )

                if was_cancelled:
                    job.status = JobStatus.CANCELLED
                    job.progress = non_complete_pct
                elif cancel_event and cancel_event.is_set():
                    job.status = JobStatus.PAUSED
                    job.progress = non_complete_pct
                elif failed > 0:
                    job.status = JobStatus.FAILED
                    job.progress = non_complete_pct
                    job.error = f"{failed} of {total} assets failed to download"
                elif failed_scenes:
                    job.status = JobStatus.FAILED
                    job.progress = non_complete_pct
                    first_err = failed_scenes[0][1] or "Stacking validation failed"
                    job.error = (
                        f"Scene stacking failed for {len(failed_scenes)} scene(s) "
                        f"({failed_scenes[0][0]}): {first_err}"
                    )
                elif completed == total and not incomplete_scenes:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.datetime.utcnow()
                    job.progress = 100.0
                    job.error = None
                else:
                    job.status = JobStatus.PAUSED
                    job.progress = non_complete_pct
            else:
                if was_cancelled:
                    job.status = JobStatus.CANCELLED
                elif cancel_event and cancel_event.is_set():
                    job.status = JobStatus.PAUSED
                elif completed == total:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.datetime.utcnow()
                    job.progress = 100.0

                    # Strictly enforce EPSG:4326 on all legacy raster downloads before cataloging
                    legacy_raster_exts = {".tif", ".tiff", ".jp2", ".img", ".vrt"}
                    for s_id, s_info in scene_info_map.items():
                        scene_dls = [d for d in all_dls if d.asset_id and d.asset_id.startswith(s_id)]
                        downloaded_assets: Dict[str, Path] = {}
                        for dl in scene_dls:
                            a_key = dl.asset_id.split(f"{s_id}_")[-1]
                            dest_p = Path(dl.destination)
                            if (
                                dest_p.exists()
                                and dest_p.is_file()
                                and dest_p.suffix.lower() in legacy_raster_exts
                            ):
                                try:
                                    reproj_res = await GeoProcessExecutor.run_cpu_bound(
                                        reproject_file_to_crs_task,
                                        str(dest_p),
                                        STRICT_OUTPUT_CRS,
                                        stacking_cfg.get("resampling_method", "bilinear"),
                                    )
                                    out_p = Path(reproj_res.get("output_path") or dest_p)
                                    if out_p != dest_p or reproj_res.get("reprojected"):
                                        dest_p = out_p
                                        dl.destination = str(out_p)
                                        if out_p.exists():
                                            sz = out_p.stat().st_size
                                            dl.total_bytes = sz
                                            dl.downloaded_bytes = sz
                                        await self._publish_to_geoserver(dest_p)
                                except Exception as reproj_exc:
                                    logger.warning(f"Legacy raster reprojection skipped for {dest_p}: {reproj_exc}")
                            downloaded_assets[a_key] = dest_p

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
        job = db.query(Job).filter(Job.id == job_id).first()
        if job and job.type == workflow_jobs.WORKFLOW_JOB:
            return False
        if job_id in self._cancellation_events:
            self._cancellation_events[job_id].set()

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
        if job.type == workflow_jobs.WORKFLOW_JOB:
            return self._retry_workflow(job, db)

        # Reset paused/failed downloads to pending
        downloads = db.query(Download).filter(
            Download.job_id == job_id,
            Download.status.in_([DownloadStatus.PAUSED, DownloadStatus.FAILED, DownloadStatus.RETRYING])
        ).all()
        for d in downloads:
            d.status = DownloadStatus.PENDING

        if isinstance(job.job_metadata, dict) and isinstance(job.job_metadata.get("scene_plans"), dict):
            meta = copy.deepcopy(job.job_metadata)
            all_job_dls = {
                d.id: d
                for d in db.query(Download).filter(Download.job_id == job_id).all()
            }
            for sp in meta["scene_plans"].values():
                final_out = sp.get("final_output_path")
                has_final = bool(final_out and Path(final_out).exists() and Path(final_out).stat().st_size > 0)
                if sp.get("status") == "completed" and has_final:
                    continue
                was_failed_scene = sp.get("status") == "failed"
                if sp.get("status") in ("failed", "paused", "stacking", "completed"):
                    sp["status"] = "downloading"
                    sp["error"] = None
                if sp.get("stack_enabled") and not has_final:
                    dl_ids_for_scene = list(sp.get("download_ids") or [])
                    existing_band_crs: Dict[str, Tuple[Optional[str], int, int, int]] = {}
                    if was_failed_scene and len(dl_ids_for_scene) > 1:
                        import rasterio
                        for dl_id in dl_ids_for_scene:
                            d_obj = all_job_dls.get(dl_id)
                            if not d_obj:
                                continue
                            dest_p = Path(d_obj.destination)
                            if dest_p.exists() and dest_p.is_file() and dest_p.stat().st_size > 0:
                                try:
                                    with rasterio.open(dest_p) as src:
                                        existing_band_crs[dl_id] = (
                                            src.crs.to_string() if src.crs else None,
                                            src.width,
                                            src.height,
                                            dest_p.stat().st_size,
                                        )
                                except Exception:
                                    existing_band_crs[dl_id] = (None, 0, 0, 0)

                    distinct_crs = {info[0] for info in existing_band_crs.values() if info[0]}
                    has_crs_conflict = len(distinct_crs) > 1
                    preferred_crs = None
                    if has_crs_conflict:
                        # Prefer the CRS of the highest-resolution / largest real band over 512x512 EPSG:4326 fallbacks
                        best_entry = max(existing_band_crs.values(), key=lambda x: (x[1] * x[2], x[3]))
                        preferred_crs = best_entry[0]

                    for dl_id in dl_ids_for_scene:
                        d_obj = all_job_dls.get(dl_id)
                        if not d_obj:
                            continue
                        dest_p = Path(d_obj.destination)
                        part_p = Path(f"{d_obj.destination}.part")
                        info = existing_band_crs.get(dl_id)
                        is_corrupt_or_mismatched = (
                            (info is not None and info[0] is None)
                            or (has_crs_conflict and preferred_crs and info is not None and info[0] != preferred_crs)
                        )
                        if is_corrupt_or_mismatched and dest_p.exists():
                            try:
                                dest_p.unlink()
                            except OSError:
                                pass
                        if not (dest_p.exists() and dest_p.is_file() and dest_p.stat().st_size > 0):
                            d_obj.status = DownloadStatus.PENDING
                            d_obj.downloaded_bytes = (
                                part_p.stat().st_size if part_p.exists() and part_p.stat().st_size > 0 else 0
                            )
            job.job_metadata = meta
            flag_modified(job, "job_metadata")

        job.status = JobStatus.QUEUED
        job.error = None
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

    def _enqueue_job_execution(self, job_id: str) -> None:
        existing_task = self._active_tasks.get(job_id)
        if existing_task and not existing_task.done():
            return
        self._cancellation_events[job_id] = asyncio.Event()
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._run_job(job_id))
            self._active_tasks[job_id] = task
        except RuntimeError:
            pass

    def enqueue_workflow(self, job_id: str) -> None:
        self._enqueue_job_execution(job_id)

    def _retry_workflow(self, job: Job, db: Session) -> bool:
        task = self._active_tasks.get(job.id)
        if task and not task.done():
            return False
        job.status = JobStatus.QUEUED
        job.progress = 0.0
        job.error = None
        job.completed_at = None
        db.commit()
        self._enqueue_job_execution(job.id)
        self._broadcast({"type": "job_status", "job_id": job.id, "status": "QUEUED"})
        return True

    @staticmethod
    def _unlink_download_files(dest_str: Optional[str]) -> None:
        if not dest_str:
            return
        for candidate in (Path(dest_str), Path(f"{dest_str}.part")):
            if candidate.exists() and candidate.is_file():
                try:
                    candidate.unlink()
                except OSError:
                    pass

    @staticmethod
    def _unlink_scene_outputs(final_out: Optional[str]) -> None:
        if not final_out:
            return
        fp = Path(final_out)
        for candidate in (
            fp,
            fp.with_name(f"{fp.stem}.partial{fp.suffix}"),
            Path(f"{final_out}.partial.tif"),
            Path(f"{final_out}.partial"),
        ):
            if candidate.exists() and candidate.is_file():
                try:
                    candidate.unlink()
                except OSError:
                    pass

    def restart_job(self, job_id: str, db: Session, reset_all: bool = False) -> bool:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False
        if job.type == workflow_jobs.WORKFLOW_JOB:
            if job.status == JobStatus.RUNNING:
                return False
            return self._retry_workflow(job, db)

        all_dls = db.query(Download).filter(Download.job_id == job_id).all()
        dls_by_id = {d.id: d for d in all_dls}

        completed_scene_dl_ids = set()
        if isinstance(job.job_metadata, dict) and isinstance(job.job_metadata.get("scene_plans"), dict):
            meta = copy.deepcopy(job.job_metadata)
            plans = meta["scene_plans"]
            all_scenes_completed = all(
                sp.get("status") == "completed"
                and sp.get("final_output_path")
                and Path(sp["final_output_path"]).exists()
                for sp in plans.values()
            )
            effective_reset_all = reset_all or all_scenes_completed

            for s_id, sp in plans.items():
                final_out = sp.get("final_output_path")
                has_final = bool(final_out and Path(final_out).exists() and Path(final_out).stat().st_size > 0)
                if not effective_reset_all and sp.get("status") == "completed" and has_final:
                    completed_scene_dl_ids.update(sp.get("download_ids") or [])
                    continue

                self._unlink_scene_outputs(final_out)
                sp["status"] = "downloading"
                sp["error"] = None
                sp["output_metadata"] = None
                for dl_id in sp.get("download_ids") or []:
                    d_obj = dls_by_id.get(dl_id)
                    if d_obj:
                        self._unlink_download_files(d_obj.destination)
                        d_obj.status = DownloadStatus.PENDING
                        d_obj.downloaded_bytes = 0
                        d_obj.last_error = None
                        d_obj.attempt_count = 0

            job.job_metadata = meta
            flag_modified(job, "job_metadata")
        else:
            effective_reset_all = reset_all or all(d.status == DownloadStatus.COMPLETED for d in all_dls)

        for d in all_dls:
            if d.id in completed_scene_dl_ids:
                continue
            if effective_reset_all or d.status != DownloadStatus.COMPLETED or not Path(d.destination).exists():
                self._unlink_download_files(d.destination)
                d.status = DownloadStatus.PENDING
                d.downloaded_bytes = 0
                d.last_error = None
                d.attempt_count = 0

        job.status = JobStatus.QUEUED
        job.error = None
        job.completed_at = None
        db.commit()

        self._enqueue_job_execution(job_id)
        self._broadcast({"type": "job_status", "job_id": job_id, "status": "QUEUED"})
        return True

    def restart_scene(self, job_id: str, scene_id: str, db: Session) -> bool:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or not isinstance(job.job_metadata, dict):
            return False
        plans = (job.job_metadata or {}).get("scene_plans")
        if not isinstance(plans, dict) or scene_id not in plans:
            return False

        meta = copy.deepcopy(job.job_metadata)
        sp = meta["scene_plans"][scene_id]
        self._unlink_scene_outputs(sp.get("final_output_path"))
        sp["status"] = "downloading"
        sp["error"] = None
        sp["output_metadata"] = None

        dl_ids = list(sp.get("download_ids") or [])
        if dl_ids:
            scene_dls = db.query(Download).filter(Download.job_id == job_id, Download.id.in_(dl_ids)).all()
            for d_obj in scene_dls:
                self._unlink_download_files(d_obj.destination)
                d_obj.status = DownloadStatus.PENDING
                d_obj.downloaded_bytes = 0
                d_obj.last_error = None
                d_obj.attempt_count = 0

        job.job_metadata = meta
        flag_modified(job, "job_metadata")
        if job.status != JobStatus.RUNNING:
            job.status = JobStatus.QUEUED
        job.error = None
        job.completed_at = None
        db.commit()

        self._enqueue_job_execution(job_id)
        self._broadcast({
            "type": "scene_progress",
            "job_id": job_id,
            "scene_id": scene_id,
            "status": "downloading",
            "error": None,
        })
        self._broadcast({"type": "job_status", "job_id": job_id, "status": job.status.value})
        return True

    def restart_download(self, job_id: str, download_id: str, db: Session) -> bool:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False
        dl = db.query(Download).filter(Download.job_id == job_id, Download.id == download_id).first()
        if not dl:
            return False

        self._unlink_download_files(dl.destination)
        dl.status = DownloadStatus.PENDING
        dl.downloaded_bytes = 0
        dl.last_error = None
        dl.attempt_count = 0

        if isinstance(job.job_metadata, dict) and isinstance(job.job_metadata.get("scene_plans"), dict):
            meta = copy.deepcopy(job.job_metadata)
            dl_to_scene = meta.get("dl_to_scene") or {}
            s_id = dl_to_scene.get(download_id)
            if not s_id:
                for cand_sid, sp in meta["scene_plans"].items():
                    if download_id in (sp.get("download_ids") or []):
                        s_id = cand_sid
                        break
            if s_id and s_id in meta["scene_plans"]:
                sp = meta["scene_plans"][s_id]
                self._unlink_scene_outputs(sp.get("final_output_path"))
                sp["status"] = "downloading"
                sp["error"] = None
                sp["output_metadata"] = None
                job.job_metadata = meta
                flag_modified(job, "job_metadata")

        if job.status != JobStatus.RUNNING:
            job.status = JobStatus.QUEUED
        job.error = None
        job.completed_at = None
        db.commit()

        self._enqueue_job_execution(job_id)
        self._broadcast({
            "type": "download_progress",
            "job_id": job_id,
            "download_id": dl.id,
            "asset_id": dl.asset_id,
            "downloaded_bytes": 0,
            "total_bytes": dl.total_bytes,
            "speed_bytes_sec": 0.0,
            "status": DownloadStatus.PENDING.value,
            "error": None,
        })
        self._broadcast({"type": "job_status", "job_id": job_id, "status": job.status.value})
        return True

    def cancel_job(self, job_id: str, db: Session) -> bool:
        if job_id in self._cancellation_events:
            self._cancellation_events[job_id].set()

        job = db.query(Job).filter(Job.id == job_id).first()
        if job and job.type == workflow_jobs.WORKFLOW_JOB:
            if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
                return False
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
