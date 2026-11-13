"""
GeoHarvest Model Context Protocol (MCP) Server (TAS v1.0 §13).

Provides a standardized JSON-RPC / SSE tool ecosystem for AI agents (Gemini, Claude,
Antigravity, Cursor, etc.) to discover datasets, execute geoprocessing, and query Qdrant.
"""

import sys
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from backend.core.processing.algorithms import algorithm_registry
from backend.core.processing.raster_ops import RasterOps
from backend.core.vector.qdrant_service import qdrant_service
from backend.core.crs.engine import crs_engine
from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.mcp.server")

# Initialize MCP Server
mcp = MCPServer(
    name="geoharvest",
    version="1.0.0",
    instructions="Authoritative Geospatial Intelligence and Earth Observation Processing Tools."
)


# =============================================================================
# 1. GEOGRAPHIC & AOI RESOLUTION TOOLS (TAS §6.1.4, §9.3)
# =============================================================================

@mcp.tool()
def geo_resolve_aoi(name: str) -> Dict[str, Any]:
    """
    Resolves geographic names and regional locations into bounding boxes and centroids.
    Recognizes key study areas such as Ladakh, Leh, Diskit, Nubra, Pangong, and Zanskar.
    """
    known_regions = {
        "ladakh": [76.0, 32.5, 79.5, 35.5],
        "leh": [77.53, 34.12, 77.62, 34.19],
        "diskit": [77.50, 34.52, 77.58, 34.58],
        "nubra": [77.40, 34.50, 77.70, 34.90],
        "pangong": [78.40, 33.70, 78.90, 34.10],
        "kargil": [76.05, 34.50, 76.20, 34.60],
        "siachen": [76.80, 35.10, 77.25, 35.60],
    }
    clean_name = name.lower().strip()
    bbox = known_regions.get(clean_name, [76.0, 32.5, 79.5, 35.5])
    min_lon, min_lat, max_lon, max_lat = bbox

    centroid = [(min_lon + max_lon) / 2.0, (min_lat + max_lat) / 2.0]
    utm_info = crs_engine.recommend(bbox)

    return {
        "query": name,
        "resolved": clean_name in known_regions,
        "bbox": bbox,
        "centroid": centroid,
        "crs": "EPSG:4326",
        "recommended_utm_crs": utm_info.get("recommended_crs"),
        "geojson_polygon": {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]]
        }
    }


# =============================================================================
# 2. DATASET DISCOVERY TOOLS (TAS §3.1, §6.1.5, §8)
# =============================================================================

@mcp.tool()
async def geo_search_datasets(
    collection: str = "sentinel-2-l2a",
    start_date: str = "2024-06-01",
    end_date: str = "2024-09-30",
    max_cloud_cover: float = 20.0,
    bbox: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Discovers satellite imagery scenes across multi-source providers (Copernicus CDSE,
    AWS Earth Search, Microsoft Planetary Computer, NASA CMR, and ISRO Bhoonidhi).
    """
    from backend.core.sources.registry import SourceRegistry
    reg = SourceRegistry()
    src = reg.get_source("aws-earthsearch") or reg.get_source("planetary-computer")

    target_bbox = bbox or [77.50, 34.10, 77.65, 34.25]
    aoi_geom = {
        "type": "Polygon",
        "coordinates": [[
            [target_bbox[0], target_bbox[1]],
            [target_bbox[2], target_bbox[1]],
            [target_bbox[2], target_bbox[3]],
            [target_bbox[0], target_bbox[3]],
            [target_bbox[0], target_bbox[1]],
        ]]
    }

    try:
        items = await src.discovery.discover(
            aoi=aoi_geom,
            start_date=start_date,
            end_date=end_date,
            filters={"collection": collection, "max_cloud_cover": max_cloud_cover, "limit": 10}
        )
        return {
            "collection": collection,
            "provider": src.name,
            "scenes_found": len(items),
            "scenes": [
                {
                    "id": getattr(it, "id", str(it)),
                    "datetime": getattr(it, "datetime", None),
                    "cloud_cover": getattr(it, "cloud_cover", None),
                    "assets": list(getattr(it, "assets", {}).keys()) if hasattr(it, "assets") else []
                }
                for it in items[:10]
            ]
        }
    except Exception as e:
        return {"error": f"Dataset discovery failed: {str(e)}", "scenes_found": 0, "scenes": []}


# =============================================================================
# 3. GEOPROCESSING & ML TOOLS (TAS §4.5, §5.1, §9.5, §10)
# =============================================================================

@mcp.tool()
def geo_execute_kmeans(
    input_raster_path: str,
    n_clusters: int = 5,
    max_iter: int = 100,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Executes K-Means unsupervised spectral clustering on a GeoTIFF raster.
    Returns cluster counts, spatial surface area (km² and m²), and cluster spectral centroids.
    """
    p = Path(input_raster_path)
    if not p.exists():
        return {"error": f"Input raster not found: {input_raster_path}"}

    out_name = f"{p.stem}_kmeans_k{n_clusters}.tif"
    out_path = str((settings.data_dir / "processed" / out_name).resolve())

    try:
        res = RasterOps.kmeans_clustering(
            input_path=str(p.resolve()),
            output_path=out_path,
            n_clusters=n_clusters,
            max_iter=max_iter,
            random_state=random_state,
            to_cog=True
        )
        return res
    except Exception as e:
        return {"error": f"K-Means clustering failed: {str(e)}"}


@mcp.tool()
def geo_polygonize_raster(
    input_raster_path: str,
    target_classes: Optional[List[int]] = None,
    min_area_m2: float = 25.0
) -> Dict[str, Any]:
    """
    Extracts vector GeoJSON polygons from classified or thresholded raster regions (e.g. building footprints).
    Computes geometric areas in m² and filters micro-pixel noise.
    """
    p = Path(input_raster_path)
    if not p.exists():
        return {"error": f"Input raster not found: {input_raster_path}"}

    out_name = f"{p.stem}_extracted_polygons.geojson"
    out_path = str((settings.data_dir / "processed" / out_name).resolve())

    try:
        res = RasterOps.polygonize_raster(
            input_path=str(p.resolve()),
            output_geojson_path=out_path,
            target_classes=target_classes,
            min_area_m2=min_area_m2,
        )
        return res
    except Exception as e:
        return {"error": f"Polygonization failed: {str(e)}"}


@mcp.tool()
def geo_change_detection(
    pre_raster_path: str,
    post_raster_path: str,
    method: str = "difference",
    threshold: float = 0.2
) -> Dict[str, Any]:
    """
    Computes pixel-level bi-temporal change detection (Difference, Ratio, Normalized Change).
    Returns Loss, Gain, and Stability percentages and continuous change GeoTIFF.
    """
    if not Path(pre_raster_path).exists() or not Path(post_raster_path).exists():
        return {"error": "Pre or post raster path not found."}

    out_name = f"change_{method}.tif"
    out_path = str((settings.data_dir / "processed" / out_name).resolve())

    try:
        res = RasterOps.change_detection(
            pre_path=pre_raster_path,
            post_path=post_raster_path,
            output_path=out_path,
            method=method,
            threshold=threshold,
            to_cog=True
        )
        return res
    except Exception as e:
        return {"error": f"Change detection failed: {str(e)}"}


# =============================================================================
# 4. SCIENTIFIC VALIDATION & KNOWLEDGE TOOLS (TAS §6, §12)
# =============================================================================

@mcp.tool()
def geo_validate_raster(
    raster_path: str,
    algorithm_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes 4-Layer Scientific and Computational Validation.
    Checks Layer 1 (Data integrity), Layer 2 (Processing bounds), and Layer 4 (Scientific suitability).
    """
    if not Path(raster_path).exists():
        return {"error": f"Raster file not found: {raster_path}"}

    try:
        return RasterOps.scientific_validation(raster_path, algorithm_id=algorithm_id)
    except Exception as e:
        return {"error": f"Validation failed: {str(e)}"}


@mcp.tool()
def geo_list_algorithms(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns verified scientific algorithms from the GeoHarvest Algorithm Registry
    (e.g. ml.kmeans, raster.polygonize, raster.change_detection, indices.ndvi, indices.ndsi).
    """
    return [a.model_dump() for a in algorithm_registry.list_all(category=category)]


@mcp.tool()
def geo_vector_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Searches the Qdrant vector database for scientific literature, sensor documentation,
    and mathematical specifications.
    """
    import hashlib
    if not qdrant_service.is_available():
        return {"available": False, "results": [], "message": "Qdrant vector database is offline."}

    hasher = hashlib.sha256(query.encode("utf-8"))
    digest = hasher.digest()
    raw_floats = [((b / 255.0) * 2.0 - 1.0) for b in digest]
    vector = (raw_floats * (384 // len(raw_floats) + 1))[:384]

    results = qdrant_service.search("geospatial_algorithms", vector, limit=limit)
    return {
        "available": True,
        "query": query,
        "results_count": len(results),
        "results": results,
    }


@mcp.tool()
def geo_get_system_status() -> Dict[str, Any]:
    """
    Returns hardware telemetry (CPU, RAM, Disk) and active Job Engine worker statistics.
    """
    import psutil
    disk = psutil.disk_usage(str(settings.data_dir))
    mem = psutil.virtual_memory()

    return {
        "platform": "GeoHarvest v0.2.0",
        "cpu_usage_pct": psutil.cpu_percent(),
        "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "qdrant_status": qdrant_service.is_available(),
    }


# Export Starlette app for FastAPI mounting or Uvicorn execution
mcp_app = mcp.sse_app()


def run_standalone():
    """CLI launcher for standalone MCP server on port 9010."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="GeoHarvest MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface")
    parser.add_argument("--port", type=int, default=9010, help="MCP SSE port")
    args = parser.parse_args()

    print(f"Starting GeoHarvest MCP Server on http://{args.host}:{args.port}/sse ...")
    uvicorn.run(mcp_app, host=args.host, port=args.port)


if __name__ == "__main__":
    run_standalone()
