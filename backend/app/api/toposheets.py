"""Survey of India topo-sheet index and assisted-acquisition endpoints.

SOI's public portal does not expose an unauthenticated public download API. GeoHarvest
indexes sheet-footprint GeoJSON (either generated from the authoritative SOI grid system
or supplied by the user) and links users to the official portal for any required CAPTCHA,
declaration, login, or purchase.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from shapely.geometry import box, shape, mapping
from shapely.validation import make_valid
from sqlalchemy.orm import Session

from backend.app.dependencies.config import settings
from backend.app.dependencies.database import get_db
from backend.app.models.models import Download
from backend.app.schemas.schemas import SearchResultItem, AssetInfo, JobResponse
from backend.core.jobs.engine import job_engine
from backend.core.toposheets.grid import generate_soi_grid
from backend.core.toposheets.catalog import get_sheet_release_info

router = APIRouter(prefix="/api/toposheets", tags=["toposheets"])
logger = logging.getLogger(__name__)

SOI_FREE_MAP_URL = "https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx"
SOI_CATALOG_URL = "https://onlinemaps.surveyofindia.gov.in/Digital_Product_Show.aspx/Home.aspx"
SOI_FAQ_URL = "https://onlinemaps.surveyofindia.gov.in/FAQs.aspx"
OPEN_TOPO_PDF_BASE = "https://github.com/ramSeraph/india_topo_maps/releases/download/50k-osm-orig"
OPEN_TOPO_GEOREF_BASE = "https://github.com/ramSeraph/india_topo_maps/releases/download/50k-osm-georef"
INDEX_DIR = settings.catalog_dir / "toposheets"
INDEX_PATH = INDEX_DIR / "sheet_index.geojson"

PRODUCTS = [
    {"id": "osm_pdf", "label": "Open Series Map PDF", "format": "PDF", "scale": "1:50,000", "access": "Free; portal declaration and CAPTCHA may be required"},
    {"id": "degree_sheet_pdf", "label": "Degree Sheet PDF", "format": "PDF", "scale": "1:250,000", "access": "Free; portal declaration and CAPTCHA may be required"},
    {"id": "georeferenced_raster", "label": "Geo-referenced colour raster", "format": "TIFF", "scale": "1:50,000 / 1:250,000", "access": "Availability and price must be checked in the SOI catalogue"},
    {"id": "topo_vector", "label": "Topographical map full sheet", "format": "SHP / GDB", "scale": "1:50,000", "access": "Availability and price must be checked in the SOI catalogue"},
    {"id": "dtm", "label": "Digital Terrain Model", "format": "IMG / TIFF", "scale": "Varies", "access": "Availability and price must be checked in the SOI catalogue"},
]


class TopoSheetSearchRequest(BaseModel):
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = Field(default=None, description="[minx, miny, maxx, maxy] in EPSG:4326")
    query: Optional[str] = None
    limit: int = Field(default=500, ge=1, le=5000)
    scale_filter: Optional[str] = None  # '1:50,000', '1:250,000' or None for all


class GenerateGridRequest(BaseModel):
    bbox: Optional[List[float]] = Field(default=None, description="[minx, miny, maxx, maxy] in EPSG:4326")
    include_250k: bool = True
    include_50k: bool = True


class ToposheetHarvestItem(BaseModel):
    sheet_number: str
    formats: List[str] = Field(default_factory=lambda: ["pdf"])  # "pdf", "tif", or both
    bbox: Optional[List[float]] = None
    geometry: Optional[Dict[str, Any]] = None


class ToposheetHarvestRequest(BaseModel):
    name: Optional[str] = "TopoSheet Harvest"
    sheets: List[ToposheetHarvestItem]
    destination_dir: Optional[str] = None


def _index_features() -> List[Dict[str, Any]]:
    if not INDEX_PATH.exists():
        return []
    try:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return payload.get("features", []) if payload.get("type") == "FeatureCollection" else []
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read Survey of India sheet index")
        return []


def _normalise_geojson(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("type") == "FeatureCollection":
        features = payload.get("features", [])
    elif payload.get("type") == "Feature":
        features = [payload]
    elif payload.get("type") in {"Polygon", "MultiPolygon"}:
        features = [{"type": "Feature", "properties": {}, "geometry": payload}]
    else:
        raise ValueError("Expected a GeoJSON FeatureCollection, Feature, Polygon, or MultiPolygon")

    valid_features = []
    for index, feature in enumerate(features):
        geometry_data = feature.get("geometry") if isinstance(feature, dict) else None
        if not geometry_data:
            continue
        geom = shape(geometry_data)
        if geom.geom_type not in {"Polygon", "MultiPolygon"}:
            continue
        if not geom.is_valid:
            geom = make_valid(geom)
        if geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            continue
        properties = feature.get("properties") or {}
        valid_features.append({
            "type": "Feature",
            "id": str(feature.get("id", properties.get("sheet_no") or properties.get("osm_no") or index)),
            "properties": properties,
            "geometry": mapping(geom),
        })
    if not valid_features:
        raise ValueError("The GeoJSON contains no valid Polygon or MultiPolygon features")
    return {"type": "FeatureCollection", "features": valid_features}


@router.get("/status")
async def get_toposheet_status():
    features = _index_features()
    return {
        "provider_id": "survey-of-india-toposheets",
        "name": "Survey of India Toposheets",
        "index_loaded": INDEX_PATH.exists() and bool(features),
        "index_feature_count": len(features),
        "index_path": str(INDEX_PATH) if INDEX_PATH.exists() else None,
        "crs": "EPSG:4326",
        "products": PRODUCTS,
        "official_urls": {
            "free_osm_pdf": SOI_FREE_MAP_URL,
            "digital_catalogue": SOI_CATALOG_URL,
            "faq": SOI_FAQ_URL,
        },
        "download_mode": "assisted",
        "supports_grid_generation": True,
        "notice": "GeoHarvest computes accurate sheet coordinates according to the official Survey of India grid system. Product acquisition and per-sheet downloads are accessed via the official SOI portal.",
    }


@router.post("/index/upload")
async def upload_toposheet_index(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".geojson", ".json")):
        raise HTTPException(status_code=400, detail="Upload a GeoJSON (.geojson or .json) sheet-footprint index")
    try:
        raw = await file.read()
        if len(raw) > 100 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Sheet index must be smaller than 100 MB")
        payload = json.loads(raw.decode("utf-8-sig"))
        normalized = _normalise_geojson(payload)
    except HTTPException:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid sheet index: {exc}") from exc

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = INDEX_PATH.with_suffix(".geojson.tmp")
    temp_path.write_text(json.dumps(normalized, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(INDEX_PATH)
    return {
        "uploaded": True,
        "feature_count": len(normalized["features"]),
        "index_path": str(INDEX_PATH),
        "crs": "EPSG:4326",
    }


@router.post("/index/generate-standard")
async def generate_standard_grid(request: GenerateGridRequest):
    """Generate and install standard Survey of India grid footprints."""
    bbox_tuple = tuple(request.bbox) if request.bbox and len(request.bbox) == 4 else None
    grid = generate_soi_grid(
        bbox=bbox_tuple,
        include_250k=request.include_250k,
        include_50k=request.include_50k,
    )
    if not grid["features"]:
        raise HTTPException(status_code=400, detail="No Survey of India sheets generated for given bounds")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = INDEX_PATH.with_suffix(".geojson.tmp")
    temp_path.write_text(json.dumps(grid, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(INDEX_PATH)
    return {
        "generated": True,
        "feature_count": len(grid["features"]),
        "index_path": str(INDEX_PATH),
        "crs": "EPSG:4326",
    }


@router.post("/search")
async def search_toposheets(request: TopoSheetSearchRequest):
    if request.geometry:
        try:
            aoi = shape(request.geometry)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid AOI geometry: {exc}") from exc
    elif request.bbox:
        if len(request.bbox) != 4 or request.bbox[0] >= request.bbox[2] or request.bbox[1] >= request.bbox[3]:
            raise HTTPException(status_code=400, detail="bbox must be [minx, miny, maxx, maxy] with min < max")
        aoi = box(*request.bbox)
    else:
        raise HTTPException(status_code=400, detail="Provide an AOI geometry or bbox in EPSG:4326")
    if aoi.is_empty or not aoi.is_valid:
        aoi = make_valid(aoi)
    if aoi.is_empty:
        raise HTTPException(status_code=400, detail="AOI geometry is empty")

    features = _index_features()
    # If no custom index is installed, generate the standard SOI grid on-the-fly for the AOI!
    if not features:
        minx, miny, maxx, maxy = aoi.bounds
        dynamic_grid = generate_soi_grid(
            bbox=(minx, miny, maxx, maxy),
            include_250k=True,
            include_50k=True,
            query=request.query,
        )
        features = dynamic_grid.get("features", [])

    if not features:
        raise HTTPException(
            status_code=409,
            detail="No topo-sheet index is installed and no sheets could be resolved for this region. Upload a GeoJSON index or generate the standard SOI grid.",
        )

    query = (request.query or "").strip().casefold()
    results = []
    for feature in features:
        try:
            sheet_geom = shape(feature["geometry"])
            if not sheet_geom.intersects(aoi):
                continue
            props = feature.get("properties") or {}
            
            # Optional scale filter
            scale_prop = str(props.get("scale", ""))
            if request.scale_filter and request.scale_filter not in scale_prop:
                continue

            searchable = " ".join(str(v) for v in props.values()).casefold()
            if query and query not in searchable and query not in str(feature.get("id", "")).casefold():
                continue
            sheet_no = next((props.get(k) for k in ("sheet_no", "sheet_number", "osm_no", "osm_number", "map_number", "name") if props.get(k)), None)
            sheet_str = str(sheet_no) if sheet_no is not None else "Unlabelled sheet"
            
            # Construct direct search link on SOI portal
            encoded_sheet = quote(sheet_str)
            direct_portal_url = f"{SOI_FREE_MAP_URL}?sheet={encoded_sheet}"

            rel_info = get_sheet_release_info(sheet_str)
            direct_pdf_url = rel_info["pdf_url"]
            direct_georef_url = rel_info["georef_url"]
            has_pdf = rel_info["has_pdf"]
            has_georef = rel_info["has_georef"]
            direct_available = rel_info["direct_available"]

            results.append({
                "id": str(feature.get("id") or sheet_no or len(results) + 1),
                "sheet_number": sheet_str,
                "sheet_safe": rel_info["normalized_key"] or sheet_str.replace("/", "_").replace(" ", "").upper(),
                "properties": props,
                "bbox": list(sheet_geom.bounds),
                "geometry": mapping(sheet_geom),
                "official_pdf_url": direct_portal_url,
                "official_catalogue_url": SOI_CATALOG_URL,
                "direct_download_pdf_url": direct_pdf_url,
                "direct_download_georef_url": direct_georef_url,
                "direct_available": direct_available,
                "has_direct_pdf": has_pdf,
                "has_direct_georef": has_georef,
                "pdf_size": rel_info["pdf_size"],
                "georef_size": rel_info["georef_size"],
                "acquisition_mode": "direct" if direct_available else "assisted",
                "availability": "direct_download" if direct_available else "portal_only",
                "formats": ["PDF", "TIFF", "SHP/GDB", "IMG/TIFF"],
            })
            if len(results) >= request.limit:
                break
        except Exception:
            logger.warning("Skipping malformed feature in topo-sheet index", exc_info=True)
    return {"total_found": len(results), "index_feature_count": len(features), "results": results, "crs": "EPSG:4326"}


@router.post("/harvest", response_model=JobResponse)
async def harvest_toposheets(request: ToposheetHarvestRequest, db: Session = Depends(get_db)):
    """Create a persistent GeoHarvest download job to fetch toposheets directly."""
    if not request.sheets:
        raise HTTPException(status_code=400, detail="No toposheets provided for harvesting.")

    scenes: List[SearchResultItem] = []
    skipped_sheets: List[str] = []
    for item in request.sheets:
        sheet_no = item.sheet_number.strip()
        rel_info = get_sheet_release_info(sheet_no)
        sheet_safe = rel_info["normalized_key"] or sheet_no.replace("/", "_").replace(" ", "").upper()
        
        assets: Dict[str, AssetInfo] = {}
        formats = [f.lower().strip() for f in item.formats] if item.formats else ["pdf"]
        
        if any(f in formats for f in ["pdf", "all", "osm_pdf"]) and rel_info["pdf_url"]:
            assets["osm_pdf"] = AssetInfo(
                name="osm_pdf",
                title=f"Survey of India Topo Sheet {sheet_no} (PDF)",
                url=rel_info["pdf_url"],
                mime_type="application/pdf",
                band="pdf"
            )
        if any(f in formats for f in ["tif", "tiff", "georef", "georef_tif", "all"]) and rel_info["georef_url"]:
            assets["georef_tif"] = AssetInfo(
                name="georef_tif",
                title=f"Survey of India Topo Sheet {sheet_no} Georeferenced (GeoTIFF)",
                url=rel_info["georef_url"],
                mime_type="image/tiff",
                band="georef"
            )

        if not assets:
            skipped_sheets.append(sheet_no)
            continue

        scenes.append(
            SearchResultItem(
                id=f"SOI_{sheet_safe}",
                collection="survey-of-india-50k",
                provider_id="survey-of-india-toposheets",
                title=f"Survey of India Topo Sheet {sheet_no}",
                datetime="2024-01-01T00:00:00Z",
                bbox=item.bbox or [0, 0, 0, 0],
                geometry=item.geometry or {"type": "Polygon", "coordinates": []},
                assets=assets
            )
        )

    if not scenes:
        skipped_names = ", ".join(skipped_sheets[:3])
        if len(skipped_sheets) > 3:
            skipped_names += f" and {len(skipped_sheets) - 3} other sheet(s)"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Selected sheet(s) [{skipped_names}] do not have open-access direct download releases "
                "available. They are restricted border or degree sheets that require assisted acquisition via the official Survey of India portal."
            )
        )

    job = job_engine.create_harvest_job(
        name=request.name or "TopoSheet Harvest",
        scenes=scenes,
        selected_bands=["all"],
        db=db,
        destination_dir=request.destination_dir,
        is_toposheet=True
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


@router.get("/official-links")
async def get_official_toposheet_links():
    return {
        "free_osm_pdf": SOI_FREE_MAP_URL,
        "digital_catalogue": SOI_CATALOG_URL,
        "faq": SOI_FAQ_URL,
        "products": PRODUCTS,
    }
