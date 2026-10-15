import asyncio
import datetime
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import ProcessingTask, Asset, AssetLineage
from backend.core.processing.recipes import recipe_registry, ProcessingRecipe
from backend.core.processing.raster_ops import RasterOps
from backend.core.crs.engine import crs_engine


class ProcessingPipelineRunner:
    """Executes multi-stage recipe pipelines with checkpoints and lineage registration."""

    @classmethod
    async def run_task(
        cls,
        task_id: str,
        input_file_path: str,
        recipe_id: str,
        aoi_geometry: Dict[str, Any],
        target_crs: Optional[str] = None
    ) -> bool:
        db: Session = SessionLocal()
        try:
            task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
            if not task:
                return False

            task.status = "running"
            task.started_at = datetime.datetime.utcnow()
            db.commit()

            recipe = recipe_registry.get(recipe_id)
            checkpoint = task.checkpoint or {}
            completed_steps = set(checkpoint.get("completed_steps", []))
            intermediate_files = checkpoint.get("intermediate_files", {})

            # Determine target CRS if auto_utm or None
            if not target_crs or target_crs.lower() == "auto_utm":
                rec = crs_engine.recommend(aoi_geometry)
                target_crs = rec["recommended_crs"]

            proc_dir = settings.data_dir / "processed" / task_id
            proc_dir.mkdir(parents=True, exist_ok=True)

            current_file = input_file_path
            total_steps = len(recipe.steps)

            for idx, step in enumerate(recipe.steps):
                step_name = step.name
                if step_name in completed_steps and step_name in intermediate_files:
                    # Step already completed in a previous attempt (checkpointed)
                    current_file = intermediate_files[step_name]
                    continue

                task.checkpoint["current_step"] = step_name
                task.progress = round((idx / total_steps) * 100.0, 1)
                db.commit()

                # Execute step
                if step_name == "validate":
                    val_res = RasterOps.validate_raster(current_file)
                    if not val_res.get("valid"):
                        raise ValueError(f"Raster validation failed: {val_res.get('error')}")
                    intermediate_files[step_name] = current_file

                elif step_name == "clip":
                    out_path = str((proc_dir / "clipped.tif").resolve())
                    current_file = RasterOps.clip_raster(
                        input_path=current_file,
                        aoi_geometry=aoi_geometry,
                        output_path=out_path,
                        nodata=step.parameters.get("nodata", 0.0)
                    )
                    intermediate_files[step_name] = current_file

                elif step_name == "reproject":
                    out_path = str((proc_dir / f"reprojected_{target_crs.replace(':', '_')}.tif").resolve())
                    current_file = RasterOps.reproject_raster(
                        input_path=current_file,
                        target_crs=target_crs,
                        output_path=out_path,
                        resampling_method=step.parameters.get("resampling", "bilinear")
                    )
                    intermediate_files[step_name] = current_file

                elif step_name == "cog":
                    out_path = str((proc_dir / "output_cog.tif").resolve())
                    current_file = RasterOps.build_cog(
                        input_path=current_file,
                        output_path=out_path,
                        tile_size=step.parameters.get("tile_size", 512),
                        compress=step.parameters.get("compress", "deflate"),
                        overview_levels=step.parameters.get("overviews", [2, 4, 8, 16])
                    )
                    intermediate_files[step_name] = current_file

                # Record checkpoint
                completed_steps.add(step_name)
                checkpoint["completed_steps"] = list(completed_steps)
                checkpoint["intermediate_files"] = intermediate_files
                task.checkpoint = checkpoint
                db.commit()

            # Task successfully completed all steps
            task.status = "completed"
            task.progress = 100.0
            task.completed_at = datetime.datetime.utcnow()
            task.output_assets = [current_file]

            # Register processed asset and lineage in database
            processed_asset_id = f"proc_{uuid.uuid4().hex[:12]}"
            source_asset = db.query(Asset).filter(Asset.url == input_file_path).first()
            if not source_asset:
                source_asset = db.query(Asset).filter(Asset.local_path == input_file_path).first()

            dataset_id = source_asset.dataset_id if source_asset else f"dataset_{task_id}"

            processed_asset = Asset(
                id=processed_asset_id,
                dataset_id=dataset_id,
                asset_name="processed_cog",
                url=current_file,
                local_path=current_file,
                asset_type="local_processed",
                parent_asset_id=source_asset.id if source_asset else None,
                size=Path(current_file).stat().st_size if Path(current_file).exists() else 0,
                mime_type="image/tiff; application=geotiff; profile=cloud-optimized",
                status="processed"
            )
            db.add(processed_asset)
            db.flush()

            if source_asset:
                lineage = AssetLineage(
                    id=f"lin_{uuid.uuid4().hex[:12]}",
                    source_asset_id=source_asset.id,
                    derived_asset_id=processed_asset.id,
                    operation=recipe.name,
                    recipe_id=recipe.id,
                    metadata_info={
                        "target_crs": target_crs,
                        "task_id": task_id,
                        "output_path": current_file
                    }
                )
                db.add(lineage)

            db.commit()
            return True

        except Exception as e:
            if task:
                task.status = "failed"
                task.error = str(e)
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

            # Execute mosaic & clip in a threadpool so it doesn't block the async event loop
            final_path = await asyncio.to_thread(
                RasterOps.mosaic_rasters,
                input_paths=input_file_paths,
                output_path=output_path,
                aoi_geometry=aoi_geometry,
                target_crs=target_crs,
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
                            "target_crs": target_crs,
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
