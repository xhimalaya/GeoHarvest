import asyncio
import datetime
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import ProcessingTask, Asset, AssetLineage
from backend.core.processing.recipes import recipe_registry, ProcessingRecipe
from backend.core.processing.raster_ops import RasterOps
from backend.core.processing.executor import GeoProcessExecutor
from backend.core.crs.engine import STRICT_OUTPUT_CRS, crs_engine, enforce_strict_epsg4326


_BAND_ALIASES: Dict[str, List[str]] = {
    "green": ["green", "b03", "band3", "b3", "sr_b3"],
    "red": ["red", "b04", "band4", "b4", "sr_b4"],
    "nir": ["nir", "nir08", "b08", "b8a", "band8", "b8", "sr_b5", "b5"],
    "nir08": ["nir08", "b08", "nir", "sr_b5", "b5", "band5"],
    "swir16": ["swir16", "swir1", "swir_1", "b11", "band11", "sr_b6", "b6"],
    "blue": ["blue", "b02", "band2", "b2", "sr_b2"],
    "swir22": ["swir22", "swir2", "b12", "band12", "sr_b7", "b7"],
}


def _match_band_file(files: List[Path], band_key: str) -> Optional[Path]:
    """Find the best matching raster file in a scene directory for a band key (e.g. green, swir16, nir)."""
    aliases = _BAND_ALIASES.get(band_key.lower(), [band_key.lower()])
    candidates: List[tuple[int, Path]] = []
    for path in files:
        stem_lower = path.stem.lower()
        tokens = [t for t in re.split(r"[^a-z0-9]+", stem_lower) if t]
        # Never confuse RGB visual quicklook GeoTIFFs with single scientific reflectance bands
        if "visual" in tokens or "tci" in tokens:
            continue
        for rank, alias in enumerate(aliases):
            if alias in tokens or stem_lower.endswith(f"_{alias}") or stem_lower == alias:
                candidates.append((rank, path))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], str(item[1])))
    return candidates[0][1]


def _resolve_target_crs(target_crs: Optional[str], aoi_geometry: Optional[Dict[str, Any]], sample_file: str) -> str:
    """Strictly enforce EPSG:4326 for all saved processing pipeline outputs."""
    return enforce_strict_epsg4326(target_crs, reject_invalid=False)


def _is_aoi_non_overlap_error(exc: Exception) -> bool:
    """Return True if rasterio/shapely rejected a clip because the AOI does not overlap the raster."""
    msg = str(exc).lower()
    return "do not overlap" in msg or "window" in msg or "empty geometry" in msg


class ProcessingPipelineRunner:
    """Executes multi-stage recipe pipelines with checkpoints and lineage registration."""

    @classmethod
    async def _run_standard_file(
        cls,
        src_path: Path,
        out_cog_path: Path,
        recipe: ProcessingRecipe,
        aoi_geometry: Optional[Dict[str, Any]],
        target_crs: str,
        clip_to_aoi: bool,
        preserve_step_map: Optional[Dict[str, str]] = None,
    ) -> str:
        """Run single-raster recipe steps (validate -> optional clip -> reproject -> COG) in process pool."""
        work_dir = Path(tempfile.mkdtemp(prefix="geoharvest_step_"))
        try:
            current_file = str(src_path.resolve())
            step_files = preserve_step_map if preserve_step_map is not None else {}

            for step in recipe.steps:
                step_name = step.name
                if step_name in step_files and Path(step_files[step_name]).exists():
                    current_file = step_files[step_name]
                    continue

                if step_name == "validate":
                    val_res = await GeoProcessExecutor.run_cpu_bound(RasterOps.validate_raster, current_file)
                    if not val_res.get("valid"):
                        raise ValueError(f"Raster validation failed for {src_path.name}: {val_res.get('error')}")
                    step_files[step_name] = current_file

                elif step_name == "clip":
                    if clip_to_aoi and aoi_geometry:
                        clip_out = str((work_dir / "clipped.tif").resolve())
                        current_file = await GeoProcessExecutor.run_cpu_bound(
                            RasterOps.clip_raster,
                            input_path=current_file,
                            aoi_geometry=aoi_geometry,
                            output_path=clip_out,
                            nodata=step.parameters.get("nodata", 0.0),
                        )
                    step_files[step_name] = current_file

                elif step_name == "reproject":
                    reproj_out = str((work_dir / f"reprojected_{target_crs.replace(':', '_')}.tif").resolve())
                    current_file = await GeoProcessExecutor.run_cpu_bound(
                        RasterOps.reproject_raster,
                        input_path=current_file,
                        target_crs=target_crs,
                        output_path=reproj_out,
                        resampling_method=step.parameters.get("resampling", "bilinear"),
                    )
                    step_files[step_name] = current_file

                elif step_name == "cog":
                    current_file = await GeoProcessExecutor.run_cpu_bound(
                        RasterOps.build_cog,
                        input_path=current_file,
                        output_path=str(out_cog_path.resolve()),
                        tile_size=step.parameters.get("tile_size", 512),
                        compress=step.parameters.get("compress", "deflate"),
                        overview_levels=step.parameters.get("overviews", [2, 4, 8, 16]),
                    )
                    step_files[step_name] = current_file

            if not out_cog_path.exists():
                shutil.copyfile(current_file, str(out_cog_path))
            return str(out_cog_path.resolve())
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    @classmethod
    async def _run_index_scene(
        cls,
        scene_dir: Path,
        scene_files: List[Path],
        out_cog_path: Path,
        recipe: ProcessingRecipe,
        aoi_geometry: Optional[Dict[str, Any]],
        target_crs: str,
        clip_to_aoi: bool,
    ) -> str:
        """Compute spectral index recipe (e.g. NDVI/NDSI) for a grouped scene directory."""
        index_step = next((s for s in recipe.steps if s.name in {"ndsi", "ndvi"}), None)
        if not index_step:
            raise ValueError(f"Recipe '{recipe.id}' does not define an index step")

        b1_key = index_step.parameters.get("band1", "green")
        b2_key = index_step.parameters.get("band2", "swir16")
        b1_path = _match_band_file(scene_files, b1_key)
        b2_path = _match_band_file(scene_files, b2_key)
        if not b1_path or not b2_path:
            missing = [k for k, p in [(b1_key, b1_path), (b2_key, b2_path)] if p is None]
            available = ", ".join(p.name for p in scene_files)
            raise ValueError(
                f"Missing required band(s) {', '.join(missing)} for '{recipe.name}' in scene '{scene_dir.name}' "
                f"(found: {available})"
            )

        work_dir = Path(tempfile.mkdtemp(prefix="geoharvest_idx_scene_"))
        try:
            for band_file in (b1_path, b2_path):
                val_res = await GeoProcessExecutor.run_cpu_bound(RasterOps.validate_raster, str(band_file))
                if not val_res.get("valid"):
                    raise ValueError(f"Band validation failed for {band_file.name}: {val_res.get('error')}")

            b1_in = str(b1_path.resolve())
            b2_in = str(b2_path.resolve())
            if clip_to_aoi and aoi_geometry:
                b1_in = await GeoProcessExecutor.run_cpu_bound(
                    RasterOps.clip_raster,
                    input_path=b1_in,
                    aoi_geometry=aoi_geometry,
                    output_path=str(work_dir / "b1_clip.tif"),
                    nodata=0.0,
                )
                b2_in = await GeoProcessExecutor.run_cpu_bound(
                    RasterOps.clip_raster,
                    input_path=b2_in,
                    aoi_geometry=aoi_geometry,
                    output_path=str(work_dir / "b2_clip.tif"),
                    nodata=0.0,
                )

            raw_idx_path = str((work_dir / f"{index_step.name}_raw.tif").resolve())
            await GeoProcessExecutor.run_cpu_bound(
                RasterOps.calc_spectral_index_advanced,
                index_type=index_step.name,
                output_path=raw_idx_path,
                band1_path=b1_in,
                band2_path=b2_in,
                to_cog=False,
            )

            current_file = raw_idx_path
            if any(s.name == "reproject" for s in recipe.steps):
                reproj_out = str((work_dir / f"reproj_{target_crs.replace(':', '_')}.tif").resolve())
                current_file = await GeoProcessExecutor.run_cpu_bound(
                    RasterOps.reproject_raster,
                    input_path=current_file,
                    target_crs=target_crs,
                    output_path=reproj_out,
                    resampling_method="bilinear",
                )

            cog_step = next((s for s in recipe.steps if s.name == "cog"), None)
            cog_params = cog_step.parameters if cog_step else {}
            return await GeoProcessExecutor.run_cpu_bound(
                RasterOps.build_cog,
                input_path=current_file,
                output_path=str(out_cog_path.resolve()),
                tile_size=cog_params.get("tile_size", 512),
                compress=cog_params.get("compress", "deflate"),
                overview_levels=cog_params.get("overviews", [2, 4, 8, 16]),
            )
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    @classmethod
    async def run_task(
        cls,
        task_id: str,
        input_file_path: str,
        recipe_id: str,
        aoi_geometry: Optional[Dict[str, Any]] = None,
        target_crs: Optional[str] = None,
        input_file_paths: Optional[List[str]] = None,
        clip_to_aoi: bool = True,
    ) -> bool:
        db: Session = SessionLocal()
        task = None
        try:
            task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
            if not task:
                return False

            task.status = "running"
            task.started_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            db.commit()

            recipe = recipe_registry.get(recipe_id)
            raw_inputs = input_file_paths if input_file_paths else [input_file_path]
            resolved_inputs = [Path(p).resolve() for p in raw_inputs if p and Path(p).exists()]
            if not resolved_inputs:
                raise ValueError("No valid input raster files exist on disk.")

            resolved_crs = _resolve_target_crs(target_crs, aoi_geometry, str(resolved_inputs[0]))
            proc_dir = settings.data_dir / "processed" / task_id
            proc_dir.mkdir(parents=True, exist_ok=True)

            is_index_recipe = any(s.name in {"ndsi", "ndvi"} for s in recipe.steps)
            checkpoint = dict(task.checkpoint or {})
            completed_steps = set(checkpoint.get("completed_steps", []))
            intermediate_files = dict(checkpoint.get("intermediate_files", {}))
            processed_outputs: List[str] = []
            skipped_items: List[Dict[str, str]] = []
            lineage_pairs: List[tuple[Path, str]] = []

            if is_index_recipe:
                # Group raster files by scene folder so each scene produces one spectral index COG
                scene_groups: Dict[Path, List[Path]] = {}
                for path in resolved_inputs:
                    scene_groups.setdefault(path.parent, []).append(path)

                total = len(scene_groups)
                for idx, (scene_dir, scene_files) in enumerate(scene_groups.items()):
                    index_name = next(s.name for s in recipe.steps if s.name in {"ndsi", "ndvi"})
                    safe_scene = re.sub(r"[^A-Za-z0-9._-]", "_", scene_dir.name) or f"scene_{idx + 1}"
                    out_cog = proc_dir / f"{safe_scene}_{index_name}_cog.tif"
                    checkpoint["current_step"] = f"{index_name} ({scene_dir.name})"
                    checkpoint["total_items"] = total
                    checkpoint["completed_items"] = idx
                    task.checkpoint = dict(checkpoint)
                    task.progress = round((idx / max(total, 1)) * 100.0, 1)
                    db.commit()

                    try:
                        out_path = await cls._run_index_scene(
                            scene_dir=scene_dir,
                            scene_files=scene_files,
                            out_cog_path=out_cog,
                            recipe=recipe,
                            aoi_geometry=aoi_geometry,
                            target_crs=resolved_crs,
                            clip_to_aoi=clip_to_aoi,
                        )
                        processed_outputs.append(out_path)
                        lineage_pairs.append((scene_files[0], out_path))
                    except Exception as exc:
                        if total > 1 and _is_aoi_non_overlap_error(exc):
                            skipped_items.append({"item": scene_dir.name, "reason": "AOI does not overlap scene"})
                            continue
                        raise

                completed_steps.update([s.name for s in recipe.steps])
            elif len(resolved_inputs) == 1:
                # Single-file execution preserves per-step checkpoints inside proc_dir for compatibility
                src_path = resolved_inputs[0]
                out_cog = proc_dir / "output_cog.tif"
                total_steps = len(recipe.steps)
                current_file = str(src_path)

                for idx, step in enumerate(recipe.steps):
                    step_name = step.name
                    if step_name in completed_steps and step_name in intermediate_files:
                        current_file = intermediate_files[step_name]
                        continue

                    checkpoint["current_step"] = step_name
                    task.checkpoint = dict(checkpoint)
                    task.progress = round((idx / max(total_steps, 1)) * 100.0, 1)
                    db.commit()

                    if step_name == "validate":
                        val_res = await GeoProcessExecutor.run_cpu_bound(RasterOps.validate_raster, current_file)
                        if not val_res.get("valid"):
                            raise ValueError(f"Raster validation failed: {val_res.get('error')}")
                        intermediate_files[step_name] = current_file
                    elif step_name == "clip":
                        if clip_to_aoi and aoi_geometry:
                            out_path = str((proc_dir / "clipped.tif").resolve())
                            current_file = await GeoProcessExecutor.run_cpu_bound(
                                RasterOps.clip_raster,
                                input_path=current_file,
                                aoi_geometry=aoi_geometry,
                                output_path=out_path,
                                nodata=step.parameters.get("nodata", 0.0),
                            )
                        intermediate_files[step_name] = current_file
                    elif step_name == "reproject":
                        out_path = str((proc_dir / f"reprojected_{resolved_crs.replace(':', '_')}.tif").resolve())
                        current_file = await GeoProcessExecutor.run_cpu_bound(
                            RasterOps.reproject_raster,
                            input_path=current_file,
                            target_crs=resolved_crs,
                            output_path=out_path,
                            resampling_method=step.parameters.get("resampling", "bilinear"),
                        )
                        intermediate_files[step_name] = current_file
                    elif step_name == "cog":
                        current_file = await GeoProcessExecutor.run_cpu_bound(
                            RasterOps.build_cog,
                            input_path=current_file,
                            output_path=str(out_cog.resolve()),
                            tile_size=step.parameters.get("tile_size", 512),
                            compress=step.parameters.get("compress", "deflate"),
                            overview_levels=step.parameters.get("overviews", [2, 4, 8, 16]),
                        )
                        intermediate_files[step_name] = current_file

                    completed_steps.add(step_name)
                    checkpoint["completed_steps"] = list(completed_steps)
                    checkpoint["intermediate_files"] = intermediate_files
                    task.checkpoint = dict(checkpoint)
                    db.commit()

                processed_outputs.append(current_file)
                lineage_pairs.append((src_path, current_file))
            else:
                # Batch folder/scene mode: process every TIFF file in the selected scene or folder
                total = len(resolved_inputs)
                used_names: set[str] = set()
                multi_parents = len({p.parent for p in resolved_inputs}) > 1

                for idx, src_path in enumerate(resolved_inputs):
                    base_name = f"{src_path.parent.name}__{src_path.stem}" if multi_parents else src_path.stem
                    safe_base = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
                    out_name = f"{safe_base}_cog.tif"
                    if out_name in used_names:
                        out_name = f"{safe_base}_{idx + 1}_cog.tif"
                    used_names.add(out_name)

                    checkpoint["current_step"] = f"Processing {src_path.name} ({idx + 1}/{total})"
                    checkpoint["total_items"] = total
                    checkpoint["completed_items"] = idx
                    task.checkpoint = dict(checkpoint)
                    task.progress = round((idx / max(total, 1)) * 100.0, 1)
                    db.commit()

                    try:
                        out_path = await cls._run_standard_file(
                            src_path=src_path,
                            out_cog_path=proc_dir / out_name,
                            recipe=recipe,
                            aoi_geometry=aoi_geometry,
                            target_crs=resolved_crs,
                            clip_to_aoi=clip_to_aoi,
                        )
                        processed_outputs.append(out_path)
                        lineage_pairs.append((src_path, out_path))
                    except Exception as exc:
                        if _is_aoi_non_overlap_error(exc):
                            skipped_items.append({"item": src_path.name, "reason": "AOI does not overlap raster"})
                            continue
                        raise

                completed_steps.update([s.name for s in recipe.steps])

            if not processed_outputs:
                raise ValueError(
                    "None of the selected TIFF files overlapped the active AOI polygon. "
                    "Draw/select an overlapping AOI or uncheck 'Clip to AOI'."
                )

            checkpoint["completed_steps"] = list(completed_steps)
            checkpoint["intermediate_files"] = intermediate_files
            checkpoint["processed_files"] = processed_outputs
            checkpoint["skipped_files"] = skipped_items
            checkpoint["completed_items"] = len(processed_outputs)
            task.checkpoint = dict(checkpoint)
            task.status = "completed"
            task.progress = 100.0
            task.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            task.output_assets = processed_outputs

            from backend.app.models.models import Dataset, Job, JobStatus

            job = db.query(Job).filter(Job.id == task.job_id).first()
            if job:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

            for src_path, out_file in lineage_pairs:
                src_str = str(src_path)
                source_asset = db.query(Asset).filter(Asset.url == src_str).first()
                if not source_asset:
                    source_asset = db.query(Asset).filter(Asset.local_path == src_str).first()

                dataset_id = source_asset.dataset_id if source_asset else f"dataset_{task_id}"
                if not source_asset:
                    existing_ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
                    if not existing_ds:
                        db.add(
                            Dataset(
                                id=dataset_id,
                                collection="local_workspace",
                                dataset_id=src_path.parent.name or dataset_id,
                                title=f"Workspace Recipe ({recipe.name})",
                            )
                        )
                        db.flush()

                processed_asset = Asset(
                    id=f"proc_{uuid.uuid4().hex[:12]}",
                    dataset_id=dataset_id,
                    asset_name=Path(out_file).stem,
                    url=out_file,
                    local_path=out_file,
                    asset_type="local_processed",
                    parent_asset_id=source_asset.id if source_asset else None,
                    size=Path(out_file).stat().st_size if Path(out_file).exists() else 0,
                    mime_type="image/tiff; application=geotiff; profile=cloud-optimized",
                    status="processed",
                )
                db.add(processed_asset)
                db.flush()

                if source_asset:
                    db.add(
                        AssetLineage(
                            id=f"lin_{uuid.uuid4().hex[:12]}",
                            source_asset_id=source_asset.id,
                            derived_asset_id=processed_asset.id,
                            operation=recipe.name,
                            recipe_id=recipe.id,
                            metadata_info={
                                "target_crs": resolved_crs,
                                "task_id": task_id,
                                "output_path": out_file,
                            },
                        )
                    )

            db.commit()
            return True

        except Exception as e:
            if task:
                task.status = "failed"
                task.error = str(e)
                from backend.app.models.models import Job, JobStatus

                job = db.query(Job).filter(Job.id == task.job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                db.commit()
            return False
        finally:
            db.close()

    @classmethod
    async def run_mosaic_clip_task(
        cls,
        task_id: str,
        input_file_paths: List[str],
        output_path: str,
        aoi_geometry: Optional[Dict[str, Any]] = None,
        target_crs: Optional[str] = None,
        nodata: Optional[float] = 0.0,
        to_cog: bool = True
    ) -> bool:
        db: Session = SessionLocal()
        task = None
        try:
            task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
            if not task:
                return False

            task.status = "running"
            task.started_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            task.progress = 10.0
            db.commit()

            # Strictly enforce EPSG:4326 for all mosaic & clip outputs
            resolved_target_crs = enforce_strict_epsg4326(target_crs, reject_invalid=False)

            # Execute mosaic & clip in a dedicated process pool so it doesn't block the async event loop
            final_path = await GeoProcessExecutor.run_cpu_bound(
                RasterOps.mosaic_rasters,
                input_paths=input_file_paths,
                output_path=output_path,
                aoi_geometry=aoi_geometry,
                target_crs=resolved_target_crs,
                nodata=nodata,
                to_cog=to_cog
            )

            task.progress = 100.0
            task.status = "completed"
            task.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            task.output_assets = [final_path]
            task.checkpoint = {"output_path": final_path, "completed": True}

            # Update parent Job if associated
            from backend.app.models.models import Job, JobStatus
            job = db.query(Job).filter(Job.id == task.job_id).first()
            if job:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                if not job.job_metadata:
                    job.job_metadata = {}
                meta = dict(job.job_metadata)
                meta["mosaic_output"] = final_path
                job.job_metadata = meta

            # Resolve or create Dataset for processed assets
            from backend.app.models.models import Dataset
            dataset_id = None
            for inp_file in input_file_paths:
                sa = db.query(Asset).filter((Asset.local_path == inp_file) | (Asset.url == inp_file)).first()
                if sa and sa.dataset_id:
                    dataset_id = sa.dataset_id
                    break

            if not dataset_id:
                ds = db.query(Dataset).filter(Dataset.id == "processed_datasets").first()
                if not ds:
                    ds = Dataset(
                        id="processed_datasets",
                        collection="processed_mosaics",
                        dataset_id="processed_mosaics",
                        title="Processed Raster Products"
                    )
                    db.add(ds)
                    db.flush()
                dataset_id = ds.id

            # Register processed asset
            processed_asset_id = f"ast_mosaic_{uuid.uuid4().hex[:8]}"
            processed_asset = Asset(
                id=processed_asset_id,
                dataset_id=dataset_id,
                asset_name="mosaic_clipped_raster",
                url=final_path,
                local_path=final_path,
                asset_type="local_processed",
                size=Path(final_path).stat().st_size if Path(final_path).exists() else 0,
                mime_type="image/tiff; application=geotiff; profile=cloud-optimized" if to_cog else "image/tiff",
                status="processed"
            )
            db.add(processed_asset)
            db.flush()

            # Register lineage for input assets
            for inp_file in input_file_paths:
                src_asset = db.query(Asset).filter(Asset.local_path == inp_file).first()
                if src_asset:
                    lineage = AssetLineage(
                        id=f"lin_{uuid.uuid4().hex[:12]}",
                        source_asset_id=src_asset.id,
                        derived_asset_id=processed_asset.id,
                        operation="mosaic_clip",
                        recipe_id="mosaic-clip-aoi",
                        metadata_info={
                            "task_id": task_id,
                            "output_path": final_path,
                            "target_crs": resolved_target_crs,
                            "has_aoi_clip": aoi_geometry is not None
                        }
                    )
                    db.add(lineage)

            db.commit()
            return True
        except Exception as e:
            if task:
                task.status = "failed"
                task.error = str(e)
                from backend.app.models.models import Job, JobStatus
                job = db.query(Job).filter(Job.id == task.job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                db.commit()
            return False
        finally:
            db.close()


pipeline_runner = ProcessingPipelineRunner()
