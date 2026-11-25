from typing import Optional
from urllib.parse import quote, urlencode

from fastapi import APIRouter, HTTPException, Query

from backend.app.dependencies.config import settings
from backend.core.geoserver import geoserver_manager

router = APIRouter(prefix="/api/geoserver", tags=["geoserver"])


@router.get("/status")
async def get_geoserver_status():
    try:
        return await geoserver_manager.status()
    except Exception as exc:
        return {
            "enabled": settings.geoserver_enabled,
            "available": False,
            "wms_url": geoserver_manager.wms_url,
            "version": "1.3.0",
            "error": str(exc),
        }


@router.get("/layers")
async def get_geoserver_layers():
    if not settings.geoserver_enabled:
        raise HTTPException(status_code=503, detail="GeoServer is disabled")
    try:
        return await geoserver_manager.layers()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GeoServer is unavailable: {exc}") from exc


@router.get("/wms-url")
async def build_wms_url(
    layer: str = Query(..., min_length=1, description="Published layer name, for example geoharvest:gh_scene_abc12345"),
    bbox: str = Query(..., description="WMS 1.3.0 BBOX in the axis order for the selected CRS"),
    width: int = Query(256, ge=1, le=4096),
    height: int = Query(256, ge=1, le=4096),
    crs: str = Query("EPSG:4326"),
    format: str = Query("image/png"),
    transparent: bool = Query(True),
    styles: Optional[str] = Query(None, description="GeoServer style name or a [value:RGBA:...] color ramp"),
    name: Optional[str] = Query(None, description="Optional layer title metadata, retained in the URL"),
    args: Optional[str] = Query(None, description="Optional vendor metadata, retained in the URL"),
):
    bbox_values = bbox.split(",")
    if len(bbox_values) != 4:
        raise HTTPException(status_code=400, detail="BBOX must contain exactly four comma-separated numbers")
    try:
        [float(value) for value in bbox_values]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="BBOX values must be numeric") from exc

    style_name = styles or ""
    if styles and styles.strip().startswith("["):
        if not settings.geoserver_enabled:
            raise HTTPException(status_code=503, detail="GeoServer is disabled")
        try:
            style_name = await geoserver_manager.ensure_color_ramp(styles)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"GeoServer could not create the requested style: {exc}") from exc

    params = [
        ("SERVICE", "WMS"),
        ("VERSION", "1.3.0"),
        ("REQUEST", "GetMap"),
        ("FORMAT", format),
        ("TRANSPARENT", str(transparent).lower()),
    ]
    if name:
        params.append(("name", name))
    params.append(("layers", layer))
    if args:
        params.append(("ARGS", args))
    params.extend([
        ("STYLES", style_name),
        ("PROJECTION", crs),
        ("WIDTH", str(width)),
        ("HEIGHT", str(height)),
        ("CRS", crs),
        ("BBOX", bbox),
    ])
    url = f"{geoserver_manager.wms_url}?{urlencode(params, quote_via=quote)}"
    return {
        "version": "1.3.0",
        "layer": layer,
        "wms_url": geoserver_manager.wms_url,
        "get_map_url": url,
    }
