import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import httpx
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.dependencies.config import settings

router = APIRouter(prefix="/api/wms", tags=["wms"])


class WmsLayerSpec(BaseModel):
    name: str
    title: str
    abstract: Optional[str] = ""
    crs: List[str] = Field(default_factory=lambda: ["EPSG:4326", "EPSG:3857"])
    bbox: Optional[List[float]] = None  # [minx, miny, maxx, maxy]
    format: str = "image/png"
    transparent: bool = True


class WmsPresetService(BaseModel):
    id: str
    name: str
    provider: str
    category: str
    url: str
    version: str = "1.3.0"
    description: str
    default_layer: str
    layers: List[WmsLayerSpec]


CURATED_WMS_PRESETS: List[WmsPresetService] = [
    WmsPresetService(
        id="nasa-gibs-wms",
        name="NASA GIBS Global Earth Observation WMS",
        provider="NASA EOSDIS",
        category="Satellite Imagery & Thermal",
        url="https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi",
        version="1.3.0",
        description="Near-real-time global NASA satellite imagery including MODIS, VIIRS, Land Surface Temperature, Snow Cover, and Active Fires.",
        default_layer="MODIS_Terra_CorrectedReflectance_TrueColor",
        layers=[
            WmsLayerSpec(
                name="MODIS_Terra_CorrectedReflectance_TrueColor",
                title="MODIS Terra True Color (250m)",
                abstract="Daily global corrected reflectance true-color composite from NASA Terra.",
            ),
            WmsLayerSpec(
                name="VIIRS_SNPP_CorrectedReflectance_TrueColor",
                title="VIIRS Suomi-NPP True Color (375m)",
                abstract="High-resolution daily true-color composite from Suomi-NPP VIIRS.",
            ),
            WmsLayerSpec(
                name="MODIS_Terra_Land_Surface_Temp_Day",
                title="MODIS Land Surface Temperature (Day 1km)",
                abstract="Daytime land surface temperature thermal grid.",
            ),
            WmsLayerSpec(
                name="MODIS_Terra_NDSI_Snow_Cover",
                title="MODIS Snow Cover (NDSI 500m)",
                abstract="Normalized Difference Snow Index cryosphere snow cover extent.",
            ),
            WmsLayerSpec(
                name="VIIRS_SNPP_DayNightBand_ENCC",
                title="VIIRS Nighttime Lights (Day/Night Band)",
                abstract="Nighttime city lights and aurora radiance.",
            ),
            WmsLayerSpec(
                name="BlueMarble_ShadedRelief_Bathymetry",
                title="NASA Blue Marble Shaded Relief & Bathymetry",
                abstract="Cloud-free global true-color shaded relief and ocean bathymetry.",
            ),
        ],
    ),
    WmsPresetService(
        id="terrestris-osm-topo",
        name="Terrestris OpenStreetMap & SRTM Topographic WMS",
        provider="Terrestris OGC Services",
        category="Topography & Basemaps",
        url="https://ows.terrestris.de/osm/service",
        version="1.1.1",
        description="Global OGC WMS providing OpenStreetMap cartography, SRTM 30m colored elevation, and hillshade overlays.",
        default_layer="TOPO-WMS",
        layers=[
            WmsLayerSpec(
                name="TOPO-WMS",
                title="Topographic Map with Elevation Contours",
                abstract="Global topographic map combining OSM features with SRTM elevation.",
            ),
            WmsLayerSpec(
                name="SRTM30-Colored-Hillshade",
                title="SRTM 30m Colored Elevation + Hillshade",
                abstract="Color-ramped SRTM 30m digital elevation model with terrain shading.",
            ),
            WmsLayerSpec(
                name="SRTM30-Hillshade",
                title="SRTM 30m Pure Hillshade (Monochrome)",
                abstract="Grayscale terrain hillshade for relief visualization.",
            ),
            WmsLayerSpec(
                name="OSM-Overlay-WMS",
                title="Transparent Roads & Boundaries Overlay",
                abstract="Vector-rendered administrative boundaries, place names, and roads.",
            ),
        ],
    ),
    WmsPresetService(
        id="gebco-bathymetry-wms",
        name="GEBCO Global Ocean & Land Elevation WMS",
        provider="GEBCO / IHO / IOC",
        category="Elevation & Bathymetry",
        url="https://wms.gebco.net/mapserv",
        version="1.3.0",
        description="General Bathymetric Chart of the Oceans (GEBCO) global terrain and seafloor relief grid.",
        default_layer="GEBCO_LATEST",
        layers=[
            WmsLayerSpec(
                name="GEBCO_LATEST",
                title="GEBCO Global Bathymetry & Elevation Shading",
                abstract="Global gridded bathymetric and topographic shaded relief.",
            ),
            WmsLayerSpec(
                name="GEBCO_LATEST_2",
                title="GEBCO Flat Color Ramp",
                abstract="Elevation and ocean depth color map.",
            ),
        ],
    ),
    WmsPresetService(
        id="isro-bhuvan-wms",
        name="ISRO Bhuvan Thematic OGC WMS",
        provider="ISRO / NRSC India",
        category="Indian Thematic & LULC",
        url="https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms",
        version="1.1.1",
        description="ISRO NRSC Bhuvan thematic Web Map Service for Land Use Land Cover (LULC), Geomorphology, Wasteland, and Lineaments across India.",
        default_layer="lulc:LA_LULC50K_1516",
        layers=[
            WmsLayerSpec(
                name="lulc:LA_LULC50K_1516",
                title="Ladakh Land Use Land Cover (1:50,000)",
                abstract="NRSC 1:50K thematic LULC map for Ladakh region.",
            ),
            WmsLayerSpec(
                name="lulc:JK_LULC50K_1516",
                title="Jammu & Kashmir LULC (1:50,000)",
                abstract="NRSC 1:50K thematic LULC map for Jammu & Kashmir.",
            ),
            WmsLayerSpec(
                name="water:INDIA_WATERSHED",
                title="India Watershed & Basin Boundaries",
                abstract="Hydrological watershed delineation across India.",
            ),
        ],
    ),
    WmsPresetService(
        id="emodnet-bathymetry",
        name="EMODnet Digital Terrain & Bathymetry WMS",
        provider="European Marine Observation Network",
        category="Marine & Coastal",
        url="https://ows.emodnet-bathymetry.eu/wms",
        version="1.3.0",
        description="High-resolution marine bathymetry, contours, and coastal digital terrain models.",
        default_layer="emodnet:mean_atlas_land",
        layers=[
            WmsLayerSpec(
                name="emodnet:mean_atlas_land",
                title="Mean Depth & Land Topography",
                abstract="Combined bathymetry and land elevation color map.",
            ),
            WmsLayerSpec(
                name="emodnet:contours",
                title="Bathymetric Depth Contours",
                abstract="Submarine depth contour lines.",
            ),
        ],
    ),
    WmsPresetService(
        id="usgs-national-map-wms",
        name="USGS Shaded Relief & Hydrography WMS",
        provider="USGS National Map",
        category="Topography & Basemaps",
        url="https://basemap.nationalmap.gov/arcgis/services/USGSShadedReliefOnly/MapServer/WMSServer",
        version="1.3.0",
        description="USGS 3DEP shaded relief and terrain elevation rendering.",
        default_layer="0",
        layers=[
            WmsLayerSpec(
                name="0",
                title="USGS 3DEP Shaded Relief",
                abstract="High-resolution monochrome terrain hillshade.",
            ),
        ],
    ),
]


class WmsCapabilitiesRequest(BaseModel):
    url: str
    version: Optional[str] = "1.3.0"


class WmsExportRequest(BaseModel):
    url: str
    layer: Optional[str] = None
    layers: Optional[str] = None
    version: str = "1.1.1"
    bbox: List[float]  # [minLon, minLat, maxLon, maxLat] in EPSG:4326
    aoi_geometry: Optional[Dict[str, Any]] = None
    width: int = 1024
    height: int = 1024
    format: str = "image/png"
    crs: str = "EPSG:4326"
    output_filename: Optional[str] = None


def _build_capabilities_url(base_url: str, version: str = "1.3.0") -> str:
    parsed = urlparse(base_url.strip())
    existing_params = dict(parse_qsl(parsed.query))
    existing_params["service"] = "WMS"
    existing_params["request"] = "GetCapabilities"
    if version:
        existing_params["version"] = version
    new_query = urlencode(existing_params)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


@router.get("/presets")
async def get_wms_presets():
    """Returns curated global OGC WMS endpoints and their ready-to-use layers."""
    out = []
    for p in CURATED_WMS_PRESETS:
        d = p.model_dump()
        d["default_layers"] = d["layers"]
        out.append(d)
    return out


@router.post("/capabilities")
async def fetch_wms_capabilities(req: WmsCapabilitiesRequest):
    """
    Connects to any OGC WMS endpoint URL, fetches GetCapabilities XML,
    and parses all discoverable map layers.
    """
    if not req.url or not req.url.strip().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Please provide a valid http:// or https:// WMS endpoint URL.")

    cap_url = _build_capabilities_url(req.url, req.version or "1.3.0")
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(cap_url)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to WMS endpoint: {str(e)}")

    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Endpoint did not return valid WMS XML capabilities: {str(e)}")

    service_title = "Custom WMS Service"
    service_abstract = ""
    layers: List[Dict[str, Any]] = []

    # Extract Service metadata
    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        if tag == "Service":
            for child in elem:
                ctag = _strip_ns(child.tag)
                if ctag == "Title" and child.text:
                    service_title = child.text.strip()
                elif ctag == "Abstract" and child.text:
                    service_abstract = child.text.strip()

    # Extract Named Layers
    for elem in root.iter():
        if _strip_ns(elem.tag) == "Layer":
            name_val = None
            title_val = None
            abstract_val = ""
            bbox_val = None
            crs_list = []

            for child in elem:
                ctag = _strip_ns(child.tag)
                if ctag == "Name" and child.text:
                    name_val = child.text.strip()
                elif ctag == "Title" and child.text:
                    title_val = child.text.strip()
                elif ctag == "Abstract" and child.text:
                    abstract_val = child.text.strip()
                elif ctag in ("CRS", "SRS") and child.text:
                    crs_list.append(child.text.strip())
                elif ctag == "EX_GeographicBoundingBox":
                    try:
                        w = float(next(c.text for c in child if _strip_ns(c.tag) == "westBoundLongitude"))
                        e = float(next(c.text for c in child if _strip_ns(c.tag) == "eastBoundLongitude"))
                        s = float(next(c.text for c in child if _strip_ns(c.tag) == "southBoundLatitude"))
                        n = float(next(c.text for c in child if _strip_ns(c.tag) == "northBoundLatitude"))
                        bbox_val = [w, s, e, n]
                    except Exception:
                        pass
                elif ctag == "LatLonBoundingBox":
                    try:
                        bbox_val = [
                            float(child.attrib.get("minx", -180)),
                            float(child.attrib.get("miny", -90)),
                            float(child.attrib.get("maxx", 180)),
                            float(child.attrib.get("maxy", 90)),
                        ]
                    except Exception:
                        pass

            if name_val:
                layers.append({
                    "name": name_val,
                    "title": title_val or name_val,
                    "abstract": abstract_val[:300] if abstract_val else "",
                    "crs": crs_list[:10] if crs_list else ["EPSG:4326", "EPSG:3857"],
                    "bbox": bbox_val,
                })

    clean_url = req.url.split("?")[0]
    return {
        "url": clean_url,
        "service_url": clean_url,
        "version": req.version or "1.3.0",
        "service_title": service_title,
        "service_abstract": service_abstract,
        "layer_count": len(layers),
        "layers": layers[:150],  # cap at 150 for UI responsiveness
    }


@router.post("/export")
async def export_wms_to_geotiff(req: WmsExportRequest):
    """
    Harvests a map region from any WMS endpoint and saves it as a georeferenced
    GeoTIFF in the local downloads directory so it can be used in Clip, Mosaic, or Band Stacking.
    """
    target_layer = req.layer or req.layers
    if not target_layer:
        raise HTTPException(status_code=400, detail="Either 'layer' or 'layers' must be provided.")
    if len(req.bbox) != 4:
        raise HTTPException(status_code=400, detail="bbox must be [minLon, minLat, maxLon, maxLat]")

    minx, miny, maxx, maxy = req.bbox
    if minx >= maxx or miny >= maxy:
        raise HTTPException(status_code=400, detail="Invalid bounding box coordinates.")

    width = max(128, min(req.width, 4096))
    height = max(128, min(req.height, 4096))

    parsed = urlparse(req.url.strip())
    params = dict(parse_qsl(parsed.query))
    params.update({
        "service": "WMS",
        "request": "GetMap",
        "version": req.version or "1.1.1",
        "layers": target_layer,
        "styles": "",
        "format": req.format or "image/png",
        "transparent": "TRUE",
        "width": str(width),
        "height": str(height),
    })

    # WMS 1.3.0 with EPSG:4326 uses lat,lon order; WMS 1.1.1 uses lon,lat order
    if params["version"] == "1.3.0":
        params["crs"] = "CRS:84"
        params["bbox"] = f"{minx},{miny},{maxx},{maxy}"
    else:
        params["srs"] = "EPSG:4326"
        params["bbox"] = f"{minx},{miny},{maxx},{maxy}"

    getmap_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(params), parsed.fragment))

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(getmap_url)
            resp.raise_for_status()
            content_bytes = resp.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"WMS GetMap download failed: {str(e)}")

    downloads_dir = settings.downloads_dir
    downloads_dir.mkdir(parents=True, exist_ok=True)

    safe_layer = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in target_layer)[:40]
    out_name = req.output_filename or f"wms_{safe_layer}_{uuid.uuid4().hex[:6]}.tif"
    if not out_name.lower().endswith((".tif", ".tiff")):
        out_name += ".tif"
    out_path = (downloads_dir / out_name).resolve()

    # Decode response image via rasterio MemoryFile and georeference to EPSG:4326 bounds
    try:
        from rasterio.io import MemoryFile
        with MemoryFile(content_bytes) as memfile:
            with memfile.open() as src:
                data = src.read()
                count, img_h, img_w = data.shape
                dtype = data.dtype

        transform = from_bounds(minx, miny, maxx, maxy, img_w, img_h)
        profile = {
            "driver": "GTiff",
            "height": img_h,
            "width": img_w,
            "count": count,
            "dtype": dtype,
            "crs": "EPSG:4326",
            "transform": transform,
            "tiled": True,
            "compress": "deflate",
        }
        with rasterio.open(str(out_path), "w", **profile) as dst:
            dst.write(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert WMS response to GeoTIFF: {str(e)}")

    return {
        "status": "completed",
        "layer": target_layer,
        "output_path": str(out_path),
        "filename": out_path.name,
        "size_bytes": out_path.stat().st_size,
        "bbox": req.bbox,
        "crs": "EPSG:4326",
        "width": img_w,
        "height": img_h,
        "dimensions": [img_w, img_h],
        "bands": count,
        "download_url": f"/api/storage/download?path={out_path.name}&root=downloads",
    }
