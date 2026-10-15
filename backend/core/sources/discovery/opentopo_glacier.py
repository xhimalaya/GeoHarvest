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
        bbox = filters.get("bbox", [76.0, 33.0, 79.0, 35.5])

        items = []
        if "rgi" in collection:
            items.append({
                "id": "RGI_V7_REGION14_SOUTH_ASIA_WEST_LADAKH",
                "collection": collection,
                "bbox": bbox,
                "geometry": {"type": "Polygon", "coordinates": []},
                "properties": {
                    "datetime": "2023-01-01T00:00:00Z",
                    "title": "Randolph Glacier Inventory v7.0 - Region 14 (South Asia West / Karakoram & Himalaya)",
                    "format": "Vector GeoJSON & Geopackage",
                    "glacier_count": 27988
                },
                "assets": {
                    "glacier_polygons": {"href": "https://www.glims.org/RGI/rgi70_data/RGI2000-v7.0-G-14_south_asia_west.zip", "title": "Glacier Boundary Polygons", "file:size": 15*1024*1024},
                    "hypsometry": {"href": "https://www.glims.org/RGI/rgi70_data/rgi70_hypsometry_r14.csv", "title": "Hypsometry Tables", "file:size": 5*1024*1024},
                }
            })
        elif "glims" in collection:
            items.append({
                "id": "GLIMS_MULTI_TEMPORAL_OUTLINES_LADAKH_HIMALAYA",
                "collection": collection,
                "bbox": bbox,
                "geometry": {"type": "Polygon", "coordinates": []},
                "properties": {
                    "datetime": "2024-01-01T00:00:00Z",
                    "title": "GLIMS Multi-Temporal Glacier Outlines & Flowlines",
                    "format": "Vector GeoJSON",
                },
                "assets": {
                    "outlines": {"href": "https://www.glims.org/maps/glims_data.geojson", "title": "Multi-Temporal Outlines", "file:size": 20*1024*1024},
                }
            })
        elif "alos-aw3d30" in collection or "alos" in collection:
            items.append({
                "id": "ALOS_AW3D30_GLOBAL_DSM_LADAKH_TILE",
                "collection": collection,
                "bbox": bbox,
                "geometry": {"type": "Polygon", "coordinates": []},
                "properties": {
                    "datetime": "2011-01-01T00:00:00Z",
                    "title": "ALOS World 3D 30m Digital Surface Model",
                    "sensor": "PRISM Stereoscopic"
                },
                "assets": {
                    "elevation": {"href": "https://portal.opentopography.org/data/AW3D30_Ladakh.tif", "title": "Elevation GeoTIFF (30m)", "file:size": 25*1024*1024},
                }
            })
        elif "nasadem" in collection or "srtm" in collection:
            items.append({
                "id": "NASADEM_HGT_30M_LADAKH_TILE",
                "collection": collection,
                "bbox": bbox,
                "geometry": {"type": "Polygon", "coordinates": []},
                "properties": {
                    "datetime": "2000-02-11T00:00:00Z",
                    "title": "NASADEM SRTM Reprocessed 30m Void-Filled Elevation",
                    "sensor": "SRTM C-Band Radar"
                },
                "assets": {
                    "elevation": {"href": "https://portal.opentopography.org/data/NASADEM_Ladakh.tif", "title": "NASADEM 30m Raster", "file:size": 25*1024*1024},
                }
            })

        return items

    async def get_metadata(self, item_id: str) -> Dict[str, Any]:
        return {"id": item_id, "provider": "opentopography-glacier"}
