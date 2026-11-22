"""Scientific raster workflow and Atlas display endpoints."""
from datetime import timezone
import math
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from rasterio.errors import RasterioError
from shapely.errors import ShapelyError
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from backend.app.api.storage import get_allowed_roots
from backend.app.dependencies.database import get_db
from backend.app.models.models import Asset, Dataset, Job, JobStatus, ProcessingTask
from backend.core.jobs.engine import job_engine
from backend.core.processing.workflows import jobs
from backend.core.processing.workflows.engine import point_values, result_directory, tile
from backend.core.processing.workflows.operators import OPERATORS
from backend.core.processing.workflows.plan import Workflow, compile_workflow, identity, local_path

PREFIX = "/api/processing/workflows"
router = APIRouter(prefix=PREFIX, tags=["raster-workflows"])


@router.get("/operators")
def list_operators():
    return [spec.metadata() for spec in OPERATORS.values()]


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    result = []
    query = (db.query(Asset).join(Dataset).options(joinedload(Asset.dataset))
             .filter(Asset.local_path.isnot(None)).order_by(Dataset.collection, Dataset.acquisition_date, Asset.id))
    for asset in query:
        if asset.asset_type == "staging" or not local_path(asset.local_path):
            continue
        scene = asset.dataset
        day = scene.acquisition_date
        result.append({
            "id": asset.id, "dataset_id": scene.id, "collection": scene.collection,
            "title": scene.title or scene.id, "name": asset.asset_name,
            "date": (day.astimezone(timezone.utc) if day.tzinfo else day).date().isoformat() if day else None,
        })
    return result


@router.post("", status_code=202)
async def submit_workflow(request: Workflow, db: Session = Depends(get_db)):
    try:
        plan = await run_in_threadpool(compile_workflow, request, db, get_allowed_roots())
        job = jobs.submit(db, plan, request.name)
    except (ValueError, RasterioError, ShapelyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    if job.status == JobStatus.QUEUED:
        job_engine.enqueue_workflow(job.id)
    return {"job_id": job.id, "status": job.status, "status_url": f"/api/jobs/{job.id}",
            "result_url": f"{PREFIX}/{job.id}/result"}


def _manifest(db, job_id):
    job = db.get(Job, job_id)
    if not job or job.type != jobs.WORKFLOW_JOB:
        raise HTTPException(404, "Raster workflow not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(409, f"Workflow is {job.status.value}")
    task = db.get(ProcessingTask, job_id)
    if not task or "manifest" not in task.checkpoint:
        raise HTTPException(410, "Workflow manifest is unavailable")
    return task.checkpoint["manifest"]


@router.get("/{job_id}/result")
def get_result(job_id: str, db: Session = Depends(get_db)):
    manifest = _manifest(db, job_id)
    outputs = []
    for item in manifest["outputs"]:
        if item["kind"] != "raster":
            outputs.append(item)
            continue
        base = f"{PREFIX}/{job_id}/{item['id']}"
        outputs.append({**item, "tiles": f"{base}/tiles/{{z}}/{{x}}/{{y}}.png",
                        "point": f"{base}/point", "export": f"{base}/export.tif"})
    return {**manifest, "outputs": outputs}


def _output(db, job_id, output_id):
    manifest = _manifest(db, job_id)
    item = next((output for output in manifest["outputs"]
                 if output["id"] == output_id and output["kind"] == "raster"), None)
    if item is None:
        raise HTTPException(404, "Raster output not found")
    path = result_directory(jobs.workflow_root(), manifest["key"]) / item["filename"]
    if not path.is_file():
        raise HTTPException(410, "Published raster is unavailable")
    return manifest, item, path


@router.get("/{job_id}/{output_id}/tiles/{z}/{x}/{y}.png")
def get_tile(
    job_id: str, output_id: str, z: int, x: int, y: int,
    band: Annotated[int, Query(ge=1)] = 1,
    palette: Literal["gray", "viridis", "diverging"] = "viridis",
    low: float | None = None, high: float | None = None,
    db: Session = Depends(get_db),
):
    if not (0 <= z <= 30 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(404, "Invalid XYZ tile coordinates")
    manifest, item, path = _output(db, job_id, output_id)
    if band > len(item["bands"]):
        raise HTTPException(422, "Requested output band is unavailable")
    metadata = item["bands"][band - 1]
    low = (metadata["min"] or 0.0) if low is None else low
    high = (metadata["max"] or 0.0) if high is None else high
    if not all(map(math.isfinite, (low, high, high - low))) or high < low:
        raise HTTPException(422, "Invalid display range")
    # The workflow key includes resolved source versions, all operator versions and the analysis grid.
    try:
        pixels, hit = tile(path, manifest["key"], band, z, x, y, palette, low, high)
    except RasterioError as exc:
        raise HTTPException(410, "Published raster cannot be read") from exc
    etag = identity([manifest["key"], output_id, band, z, x, y, palette, low, high])
    return Response(pixels, media_type="image/png", headers={
        "Cache-Control": "private, max-age=86400", "ETag": f'"{etag}"', "X-Tile-Cache": "HIT" if hit else "MISS",
    })


@router.get("/{job_id}/{output_id}/point")
def get_point(
    job_id: str, output_id: str,
    lon: Annotated[float, Query(ge=-180, le=180)], lat: Annotated[float, Query(ge=-90, le=90)],
    db: Session = Depends(get_db),
):
    _, item, path = _output(db, job_id, output_id)
    try:
        values = point_values(path, lon, lat)
    except RasterioError as exc:
        raise HTTPException(422, "Point cannot be read on the analysis grid") from exc
    return {"lon": lon, "lat": lat, "bands": [
        {"index": band["index"], "name": band["name"], "unit": band["unit"], "date": band["date"], "value": value}
        for band, value in zip(item["bands"], values)
    ]}


@router.get("/{job_id}/{output_id}/export.tif")
def export_result(job_id: str, output_id: str, db: Session = Depends(get_db)):
    _, _, path = _output(db, job_id, output_id)
    return FileResponse(path, media_type="image/tiff", filename=Path(path).name)
