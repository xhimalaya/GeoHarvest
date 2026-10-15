import math
from typing import Dict, Any, List, Optional
from backend.core.sources.base import DiscoveryAdapter


class BhuvanWcsDiscoveryAdapter(DiscoveryAdapter):
    """
    ISRO / NRSC Bhuvan OGC Web Coverage Service (WCS) & Web Map Service (WMS) Adapter.
    Generates standard OGC WCS 1.0.0 GetCoverage requests returning authentic GeoTIFF rasters
    for CartoDEM (30m elevation), LULC, and thematic datasets.
    """

    WCS_BASE_URL = "https://bhuvan-app1.nrsc.gov.in/bhuvan/wcs"
    WMS_BASE_URL = "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"

    COVERAGE_MAP = {
        "bhuvan-cartodem-30m": {
            "layer": "bhuvan:cartodem_v3",
            "title": "Bhuvan CartoDEM 30m Elevation Model",
            "band": "DEM",
            "asset_key": "cartodem",
            "resolution": 30.0,
            "format": "GeoTIFF",
        },
        "bhuvan-lulc-250k": {
            "layer": "bhuvan:lulc_250k",
            "title": "Bhuvan National Land Use / Land Cover 250k",
            "band": "LULC",
            "asset_key": "lulc",
            "resolution": 56.0,
            "format": "GeoTIFF",
        },
        "bhuvan-snow-himalaya": {
            "layer": "bhuvan:snow_cover_daily",
            "title": "Bhuvan Himalayan Daily Snow Cover",
            "band": "SNOW",
            "asset_key": "snow",
            "resolution": 1000.0,
            "format": "GeoTIFF",
        },
    }

    def __init__(
        self,
        wcs_url: str = WCS_BASE_URL,
        api_key: Optional[str] = None
    ):
        self.wcs_url = wcs_url.rstrip("/")
        self.api_key = api_key

    def build_wcs_url(
        self,
        coverage_id: str,
        bbox: List[float],
        width: int = 1024,
        height: int = 1024,
        crs: str = "EPSG:4326"
    ) -> str:
        """
        Builds an OGC WCS 1.0.0 GetCoverage request URL for downloading GeoTIFF.
        """
        minx, miny, maxx, maxy = bbox
        params = [
            f"SERVICE=WCS",
            f"VERSION=1.0.0",
            f"REQUEST=GetCoverage",
            f"COVERAGE={coverage_id}",
            f"CRS={crs}",
            f"BBOX={minx:.6f},{miny:.6f},{maxx:.6f},{maxy:.6f}",
            f"WIDTH={width}",
            f"HEIGHT={height}",
            f"FORMAT=GeoTIFF"
        ]
        if self.api_key:
            params.append(f"token={self.api_key}")
        return f"{self.wcs_url}?{'&'.join(params)}"

    async def discover(
        self,
        aoi: Optional[Dict[str, Any]],
        start_date: str,
        end_date: str,
        filters: Dict[str, Any]
    ) -> List[Any]:
        collection = filters.get("collection", "bhuvan-cartodem-30m")
        cov_info = self.COVERAGE_MAP.get(collection, self.COVERAGE_MAP["bhuvan-cartodem-30m"])

        # Determine spatial bounding box
        bbox = filters.get("bbox")
        if not bbox and aoi and aoi.get("coordinates"):
            # Derive bbox from GeoJSON polygon
            try:
                coords = aoi["coordinates"][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                bbox = [min(lons), min(lats), max(lons), max(lats)]
            except Exception:
                bbox = [76.0, 33.0, 78.0, 35.0]
        elif not bbox:
            bbox = [76.0, 33.0, 78.0, 35.0]  # Default Ladakh / NW Himalaya bounds

        # Compute sensible image dimensions based on aspect ratio
        dx = abs(bbox[2] - bbox[0])
        dy = abs(bbox[3] - bbox[1])
        base_size = 1024
        aspect = dx / max(dy, 1e-6)
        width = min(2048, max(256, int(base_size * math.sqrt(aspect))))
        height = min(2048, max(256, int(base_size / math.sqrt(aspect))))

        coverage_url = self.build_wcs_url(
            coverage_id=cov_info["layer"],
            bbox=bbox,
            width=width,
            height=height
        )

        date_stamp = (start_date or "2024-01-01").replace("-", "")
        item_id = f"BHUVAN_{cov_info['asset_key'].upper()}_{date_stamp}_{int(bbox[0])}E_{int(bbox[1])}N"

        items = [
            {
                "id": item_id,
                "collection": collection,
                "bbox": bbox,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [bbox[0], bbox[1]],
                        [bbox[2], bbox[1]],
                        [bbox[2], bbox[3]],
                        [bbox[0], bbox[3]],
                        [bbox[0], bbox[1]],
                    ]]
                },
                "properties": {
                    "datetime": f"{start_date or '2024-01-01'}T00:00:00Z",
                    "title": f"{cov_info['title']} ({width}x{height} px)",
                    "service": "OGC WCS 1.0.0",
                    "format": "GeoTIFF",
                    "coverage": cov_info["layer"],
                    "resolution": cov_info["resolution"],
                },
                "assets": {
                    cov_info["asset_key"]: {
                        "href": coverage_url,
                        "title": f"{cov_info['title']} GeoTIFF",
                        "type": "image/tiff",
                        "file:size": width * height * 2,  # 16-bit raster approximation
                    },
                    "visual": {
                        "href": coverage_url,
                        "title": "Visual Preview",
                        "type": "image/tiff",
                        "file:size": width * height * 2,
                    }
                }
            }
        ]
        return items

    async def get_metadata(self, item_id: str) -> Dict[str, Any]:
        return {
            "id": item_id,
            "provider": "isro-bhuvan-vedas",
            "service": "OGC WCS",
            "capabilities_url": f"{self.wcs_url}?SERVICE=WCS&REQUEST=GetCapabilities"
        }
