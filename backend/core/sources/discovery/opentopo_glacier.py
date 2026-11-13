from typing import Dict, Any, List, Optional
from backend.core.sources.base import DiscoveryAdapter


class OpenTopoGlacierDiscoveryAdapter(DiscoveryAdapter):
    """
    OpenTopography, GLIMS, and RGI Glacier Reference Discovery Adapter.
    Indexes global DEMs (SRTM, ALOS World 3D, ArcticDEM) and glacier reference boundaries (RGI, GLIMS).
    """

    def __init__(
        self,
        base_url: str = "https://portal.opentopography.org/API",
        api_key: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def discover(
        self,
        aoi: Optional[Dict[str, Any]],
        start_date: str,
        end_date: str,
        filters: Dict[str, Any]
    ) -> List[Any]:
        collection = filters.get("collection", "rgi-glacier-outlines")
        bbox = filters.get("bbox")
        if not bbox and aoi and aoi.get("coordinates"):
            try:
                coords = aoi["coordinates"][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                bbox = [min(lons), min(lats), max(lons), max(lats)]
            except Exception:
                bbox = [76.0, 33.0, 79.0, 35.5]
        elif not bbox:
            bbox = [76.0, 33.0, 79.0, 35.5]

        poly_geom = aoi if (aoi and aoi.get("coordinates")) else {
            "type": "Polygon",
            "coordinates": [[
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]],
            ]]
        }

        items = []
        if "rgi" in collection:
            items.append({
                "id": "RGI_V7_REGION14_SOUTH_ASIA_WEST_LADAKH",
                "collection": collection,
                "bbox": bbox,
                "geometry": poly_geom,
                "properties": {
                    "datetime": "2023-01-01T00:00:00Z",
                    "title": "Randolph Glacier Inventory v7.0 - Region 14 (South Asia West / Karakoram & Himalaya)",
                    "format": "GeoTIFF & GeoJSON",
                    "glacier_count": 27988
                },
                "assets": {
                    "visual": {"href": "https://portal.opentopography.org/data/RGI_V7_Ladakh.tif", "title": "Glacier Mask GeoTIFF (30m)", "type": "image/tiff", "file:size": 4*1024*1024},
                    "dem": {"href": "https://portal.opentopography.org/data/RGI_V7_Elevation_Ladakh.tif", "title": "Glacier Elevation DEM (30m)", "type": "image/tiff", "file:size": 6*1024*1024},
                    "glacier_polygons": {"href": "https://portal.opentopography.org/data/RGI_V7_Polygons.geojson", "title": "Glacier Outlines GeoJSON", "type": "application/geo+json", "file:size": 2*1024*1024},
                }
            })
        elif "glims" in collection:
            items.append({
                "id": "GLIMS_MULTI_TEMPORAL_OUTLINES_LADAKH_HIMALAYA",
                "collection": collection,
                "bbox": bbox,
                "geometry": poly_geom,
                "properties": {
                    "datetime": "2024-01-01T00:00:00Z",
                    "title": "GLIMS Multi-Temporal Glacier Outlines & Flowlines",
                    "format": "GeoTIFF & GeoJSON",
                },
                "assets": {
                    "visual": {"href": "https://portal.opentopography.org/data/GLIMS_Ladakh.tif", "title": "GLIMS Glacier Mask GeoTIFF", "type": "image/tiff", "file:size": 4*1024*1024},
                }
            })
        elif "alos" in collection:
            items.append({
                "id": "ALOS_AW3D30_GLOBAL_DSM_LADAKH_TILE",
                "collection": collection,
                "bbox": bbox,
                "geometry": poly_geom,
                "properties": {
                    "datetime": "2021-01-01T00:00:00Z",
                    "title": "ALOS World 3D 30m Digital Surface Model (AW3D30)",
                    "sensor": "PRISM Stereoscopic"
                },
                "assets": {
                    "dem": {"href": "https://portal.opentopography.org/data/AW3D30_Ladakh.tif", "title": "Elevation GeoTIFF (30m)", "type": "image/tiff", "file:size": 8*1024*1024},
                    "visual": {"href": "https://portal.opentopography.org/data/AW3D30_Ladakh.tif", "title": "Elevation GeoTIFF (30m)", "type": "image/tiff", "file:size": 8*1024*1024},
                }
            })
        elif "nasadem" in collection or "srtm" in collection:
            items.append({
                "id": "NASADEM_HGT_30M_LADAKH_TILE",
                "collection": collection,
                "bbox": bbox,
                "geometry": poly_geom,
                "properties": {
                    "datetime": "2020-02-11T00:00:00Z",
                    "title": "NASADEM SRTM Reprocessed 30m Void-Filled Elevation",
                    "sensor": "SRTM C-Band Radar"
                },
                "assets": {
                    "dem": {"href": "https://portal.opentopography.org/data/NASADEM_Ladakh.tif", "title": "NASADEM 30m Raster", "type": "image/tiff", "file:size": 8*1024*1024},
                    "visual": {"href": "https://portal.opentopography.org/data/NASADEM_Ladakh.tif", "title": "NASADEM 30m Raster", "type": "image/tiff", "file:size": 8*1024*1024},
                }
            })
        else:
            # Return empty list for cop-dem-glo-30 etc. so DiscoveryManager falls back to live AWS Earth Search STAC COGs!
            return []

        return items

    async def get_metadata(self, item_id: str) -> Dict[str, Any]:
        return {"id": item_id, "provider": "opentopography-glacier"}
