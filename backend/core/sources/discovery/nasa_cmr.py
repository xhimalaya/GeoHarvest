import httpx
from typing import Dict, Any, List, Optional
from backend.core.sources.base import DiscoveryAdapter


class NasaCmrDiscoveryAdapter(DiscoveryAdapter):
    """
    NASA Earthdata Common Metadata Repository (CMR) STAC & Search Adapter.
    Provides public open discovery for NASA DAAC collections (LP DAAC, NSIDC, ASF, PO.DAAC, GES DISC)
    including MODIS, VIIRS, ICESat-2, GEDI, ASTER, and SWOT.
    """

    def __init__(
        self,
        base_url: str = "https://cmr.earthdata.nasa.gov/stac",
        default_collection: str = "HLSL30.v2.0"
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
        limit = filters.get("limit", 20)

        # CMR STAC Search payload
        payload: Dict[str, Any] = {
            "limit": limit
        }

        # Map friendly collection IDs to CMR collection symbols if known
        cmr_collection_map = {
            "modis-09a1-061": "MOD09A1.v061",
            "viirs-vnp09ga": "VNP09GA.v002",
            "icesat2-atl06-land-ice": "ATL06.006",
            "nasa-gedi-l2a-elevation": "GEDI02_A.002",
            "nasadem-hgt-v001": "NASADEM_HGT.v001",
            "ecostress-l2-lste": "ECO2LSTE.001",
            "nasa-swot-l2-water": "SWOT_L2_HR_RiverSP_2.0",
        }
        target_coll = cmr_collection_map.get(collection, collection)
        payload["collections"] = [target_coll]

        if start_date and end_date:
            s_date = start_date if "T" in start_date else f"{start_date}T00:00:00Z"
            e_date = end_date if "T" in end_date else f"{end_date}T23:59:59Z"
            payload["datetime"] = f"{s_date}/{e_date}"

        if aoi:
            payload["intersects"] = aoi
        elif "bbox" in filters and filters["bbox"]:
            payload["bbox"] = filters["bbox"]

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GeoHarvest/0.2.0 (NASA Earthdata CMR)"
        }

        features = []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(f"{self.base_url}/search", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    features = data.get("features", [])
        except Exception:
            features = []

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
