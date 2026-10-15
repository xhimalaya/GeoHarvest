import httpx
import logging
from typing import Dict, Any, List, Optional
from backend.core.sources.base import DiscoveryAdapter

logger = logging.getLogger("geoharvest.sources.copernicus")


class CopernicusCdseDiscoveryAdapter(DiscoveryAdapter):
    """
    Copernicus Data Space Ecosystem (CDSE) STAC API Adapter.
    Active Endpoint: https://stac.dataspace.copernicus.eu/v1
    Authoritative ESA provider for complete, gapless global archives of:
      - Sentinel-2 (Level-2A BOA and Level-1C TOA)
      - Sentinel-1 (C-band SAR GRD, SLC)
      - Sentinel-3, Sentinel-5P, and Copernicus DEM (GLO-30)
    """

    def __init__(
        self,
        base_url: str = "https://stac.dataspace.copernicus.eu/v1",
        default_collection: str = "sentinel-2-l2a"
    ):
        self.base_url = base_url.rstrip("/")
        self.default_collection = default_collection

    async def discover(
        self,
        aoi: Optional[Dict[str, Any]],
        start_date: str,
        end_date: str,
        filters: Dict[str, Any]
    ) -> List[Any]:
        collection = filters.get("collection", self.default_collection)
        limit = filters.get("limit", 50)
        max_cloud = filters.get("max_cloud_cover")

        # Map internal collection IDs to CDSE collection symbols
        cdse_map = {
            "sentinel-2-l2a": "sentinel-2-l2a",
            "sentinel-2-c1-l2a": "sentinel-2-l2a",
            "sentinel-2-l1c": "sentinel-2-l1c",
            "sentinel-1-grd": "sentinel-1-grd",
            "sentinel-3-sral": "sentinel-3-sr-2-lan-ntc",
            "sentinel-5p-l2-tropomi": "sentinel-5p-l2-aer-ai",
            "cop-dem-glo-30": "cop-dem-glo-30-dged",
        }
        target_coll = cdse_map.get(collection, collection.lower())

        payload: Dict[str, Any] = {
            "collections": [target_coll],
            "limit": limit
        }

        # Date range filter
        if collection not in ["cop-dem-glo-30", "cop-dem-glo-30-dged"] and start_date and end_date:
            s_date = start_date if "T" in start_date else f"{start_date}T00:00:00Z"
            e_date = end_date if "T" in end_date else f"{end_date}T23:59:59Z"
            payload["datetime"] = f"{s_date}/{e_date}"

        # Spatial AOI intersection or bounding box
        if aoi:
            payload["intersects"] = aoi
        elif "bbox" in filters and filters["bbox"]:
            payload["bbox"] = filters["bbox"]

        # Cloud cover query filter for optical collections
        if max_cloud is not None and max_cloud < 100 and "sentinel-2" in target_coll:
            payload["query"] = {
                "eo:cloud_cover": {"lte": float(max_cloud)}
            }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GeoHarvest/0.2.0 (Copernicus CDSE STAC Client)"
        }

        features = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self.base_url}/search", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    features = data.get("features", [])
                    logger.info(f"CDSE STAC returned {len(features)} scenes for {target_coll}")
                else:
                    logger.warning(f"CDSE search returned HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"CDSE discovery request failed: {e}")
            features = []

        # Secondary client-side cloud cover check
        if max_cloud is not None and max_cloud < 100:
            filtered = []
            for f in features:
                props = f.get("properties", {})
                c_cov = props.get("eo:cloud_cover")
                if c_cov is None or c_cov <= max_cloud:
                    filtered.append(f)
            features = filtered

        return features

    async def get_metadata(self, item_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/items/{item_id}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {}
