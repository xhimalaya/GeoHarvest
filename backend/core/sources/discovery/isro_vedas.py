from typing import Dict, Any, List, Optional
from backend.core.sources.base import DiscoveryAdapter
from backend.core.sources.discovery.bhuvan_wcs import BhuvanWcsDiscoveryAdapter
from backend.core.sources.discovery.bhoonidhi import BhoonidhiDiscoveryAdapter


class IsroVedasDiscoveryAdapter(DiscoveryAdapter):
    """
    Unified ISRO Remote Sensing Ecosystem Discovery Adapter.
    Dispatches between:
      1. Bhuvan OGC WCS (CartoDEM 30m, LULC 250k, Snow Cover rasters)
      2. Bhoonidhi STAC API (Resourcesat-2A, Cartosat-2, EOS-04 SAR)
    """

    def __init__(
        self,
        base_url: str = "https://bhoonidhi.nrsc.gov.in/api/v1",
        api_token: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.bhuvan_wcs = BhuvanWcsDiscoveryAdapter(api_key=api_token)
        self.bhoonidhi = BhoonidhiDiscoveryAdapter(base_url=self.base_url)

    async def discover(
        self,
        aoi: Optional[Dict[str, Any]],
        start_date: str,
        end_date: str,
        filters: Dict[str, Any]
    ) -> List[Any]:
        collection = filters.get("collection", "isro-resourcesat-2a")

        # Route Bhuvan thematic and elevation coverages to OGC WCS
        if collection.startswith("bhuvan-") or "cartodem" in collection or "snow" in collection:
            return await self.bhuvan_wcs.discover(
                aoi=aoi,
                start_date=start_date,
                end_date=end_date,
                filters=filters
            )

        # Route satellite constellation collections to Bhoonidhi STAC Client
        return await self.bhoonidhi.discover(
            aoi=aoi,
            start_date=start_date,
            end_date=end_date,
            filters=filters
        )

    async def get_metadata(self, item_id: str) -> Dict[str, Any]:
        if "BHUVAN" in item_id:
            return await self.bhuvan_wcs.get_metadata(item_id)
        return await self.bhoonidhi.get_metadata(item_id)
