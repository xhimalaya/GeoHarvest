import json
import uuid
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.app.schemas.schemas import AOIValidateRequest, AOIValidateResponse
from backend.core.aoi.engine import AOIEngine
from backend.app.dependencies.config import settings

router = APIRouter(prefix="/api/aoi", tags=["aoi"])


class SaveAOIRequest(BaseModel):
    geojson: Dict[str, Any]
    name: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None


class SavedAOIItem(BaseModel):
    id: str
    name: str
    created_at: str
    area_km2: float
    crs: str
    bbox: List[float]
    file_name: str
    download_url: str


@router.post("/validate", response_model=AOIValidateResponse)
async def validate_aoi(request: AOIValidateRequest):
    result = AOIEngine.validate_and_analyze(geojson_data=request.geometry, bbox=request.bbox)
    return AOIValidateResponse(**result)


@router.post("/upload", response_model=AOIValidateResponse)
async def upload_aoi(file: UploadFile = File(...)):
    try:
        content = await file.read()
        geojson_data = json.loads(content.decode("utf-8"))
        result = AOIEngine.validate_and_analyze(geojson_data=geojson_data)
        if not result["valid"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return AOIValidateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse GeoJSON file: {str(e)}")


@router.get("/samples/ladakh")
async def get_ladakh_sample():
    sample_path = settings.base_dir / "resources" / "samples" / "ladakh.geojson"
    if sample_path.exists():
        with open(sample_path, "r") as f:
            data = json.load(f)
        analysis = AOIEngine.validate_and_analyze(geojson_data=data)
        return {
            "name": "Ladakh Region",
            "geojson": data,
            "analysis": analysis
        }
    raise HTTPException(status_code=404, detail="Ladakh sample GeoJSON not found")


@router.post("/save")
async def save_aoi(req: SaveAOIRequest):
    """Saves a drawn or imported AOI as a downloadable GeoJSON file."""
    try:
        analysis = req.analysis
        if not analysis:
            analysis = AOIEngine.validate_and_analyze(geojson_data=req.geojson)
            if not analysis.get("valid"):
                raise HTTPException(status_code=400, detail=analysis.get("error", "Invalid geometry"))

        aoi_id = f"aoi_{uuid.uuid4().hex[:8]}"
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        area_km2 = float(analysis.get("area_km2", 0.0))
        default_name = f"Drawn Polygon ({round(area_km2, 1)} km²)" if area_km2 > 0 else "Drawn AOI Polygon"
        name = req.name or default_name

        raw = req.geojson
        if raw.get("type") == "FeatureCollection":
            feature_collection = raw
        elif raw.get("type") == "Feature":
            feature_collection = {
                "type": "FeatureCollection",
                "features": [raw]
            }
        else:
            feature_collection = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": raw,
                        "properties": {
                            "name": name,
                            "id": aoi_id,
                            "area_km2": area_km2,
                            "crs": analysis.get("crs", "EPSG:4326"),
                            "created_at": created_at
                        },
                        "bbox": analysis.get("bbox")
                    }
                ]
            }

        file_path = settings.aois_dir / f"{aoi_id}.geojson"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feature_collection, f, indent=2)

        return {
            "id": aoi_id,
            "name": name,
            "created_at": created_at,
            "area_km2": area_km2,
            "crs": analysis.get("crs", "EPSG:4326"),
            "bbox": analysis.get("bbox", []),
            "file_name": f"{aoi_id}.geojson",
            "download_url": f"/api/aoi/download/{aoi_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save AOI: {str(e)}")


@router.get("/saved", response_model=List[SavedAOIItem])
async def list_saved_aois():
    """Lists all saved AOI GeoJSON files."""
    items = []
    if not settings.aois_dir.exists():
        return items

    for f_path in sorted(settings.aois_dir.glob("*.geojson"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            aoi_id = f_path.stem
            features = data.get("features", [])
            props = features[0].get("properties", {}) if features else {}
            created_at = props.get("created_at") or datetime.datetime.fromtimestamp(f_path.stat().st_mtime, datetime.timezone.utc).isoformat()
            name = props.get("name") or aoi_id
            area_km2 = float(props.get("area_km2", 0.0))
            crs = props.get("crs", "EPSG:4326")
            bbox = props.get("bbox") or (features[0].get("bbox", []) if features else [])

            items.append(SavedAOIItem(
                id=aoi_id,
                name=name,
                created_at=created_at,
                area_km2=area_km2,
                crs=crs,
                bbox=bbox or [],
                file_name=f_path.name,
                download_url=f"/api/aoi/download/{aoi_id}"
            ))
        except Exception:
            continue

    return items


@router.get("/download/{aoi_id}")
async def download_aoi_file(aoi_id: str):
    """Downloads a saved AOI GeoJSON file."""
    file_path = settings.aois_dir / f"{aoi_id}.geojson"
    if not file_path.exists():
        file_path = settings.aois_dir / f"{aoi_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="AOI file not found")

    download_filename = f"{aoi_id}.geojson"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            props = data.get("features", [{}])[0].get("properties", {})
            raw_name = props.get("name")
            if raw_name:
                safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw_name)
                download_filename = f"{safe_name}.geojson"
    except Exception:
        pass

    return FileResponse(
        path=file_path,
        media_type="application/geo+json",
        filename=download_filename
    )


@router.delete("/saved/{aoi_id}")
async def delete_saved_aoi(aoi_id: str):
    """Deletes a saved AOI file."""
    file_path = settings.aois_dir / f"{aoi_id}.geojson"
    if file_path.exists():
        file_path.unlink()
        return {"deleted": True, "id": aoi_id}
    raise HTTPException(status_code=404, detail="AOI not found")

