import httpx
from typing import Dict, Any, List, Optional, Callable
from backend.core.sources.base import DiscoveryAdapter


class StacDiscoveryAdapter(DiscoveryAdapter):
    """STAC Discovery Adapter for querying STAC 1.0.0 API endpoints."""

    def __init__(
        self,
        stac_api_url: str,
        default_collection: str = "sentinel-2-l2a",
        url_signer: Optional[Callable[[str], str]] = None
    ):
        self.stac_api_url = stac_api_url.rstrip("/")
        self.default_collection = default_collection
        self.url_signer = url_signer

    async def discover(
        self,
        aoi: Optional[Dict[str, Any]],
        start_date: str,
        end_date: str,
        filters: Dict[str, Any]
    ) -> List[Any]:
        collection = filters.get("collection", self.default_collection)
        max_cloud_cover = filters.get("max_cloud_cover", 100.0)
        limit = filters.get("limit", 50)

        payload: Dict[str, Any] = {
            "collections": [collection],
            "limit": limit,
        }

        if collection != "cop-dem-glo-30":
            s_date = start_date if "T" in start_date else f"{start_date}T00:00:00Z"
            e_date = end_date if "T" in end_date else f"{end_date}T23:59:59Z"
            payload["datetime"] = f"{s_date}/{e_date}"

        if aoi:
            payload["intersects"] = aoi
        elif "bbox" in filters and filters["bbox"]:
            payload["bbox"] = filters["bbox"]

        if collection in ["sentinel-2-l2a", "sentinel-2-c1-l2a", "landsat-c2-l2"]:
            if max_cloud_cover is not None and max_cloud_cover < 100.0:
                payload["query"] = {
                    "eo:cloud_cover": {"lt": float(max_cloud_cover)}
                }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GeoHarvest/0.2.0"
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                resp = await client.post(f"{self.stac_api_url}/search", json=payload, headers=headers)
                if resp.status_code != 200 and "query" in payload:
                    del payload["query"]
                    resp = await client.post(f"{self.stac_api_url}/search", json=payload, headers=headers)
                
                if resp.status_code != 200 and collection == "sentinel-2-l2a":
                    # Fallback to sentinel-2-c1-l2a if needed
                    payload["collections"] = ["sentinel-2-c1-l2a"]
                    resp = await client.post(f"{self.stac_api_url}/search", json=payload, headers=headers)

                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        features = data.get("features", [])
        if self.url_signer:
            for feat in features:
                assets = feat.get("assets", {})
                for k, v in assets.items():
                    if isinstance(v, dict) and "href" in v:
                        v["href"] = self.url_signer(v["href"])

        return features

    async def get_metadata(self, item_id: str) -> Dict[str, Any]:
        url = f"{self.stac_api_url}/collections/{self.default_collection}/items/{item_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
        return {}
