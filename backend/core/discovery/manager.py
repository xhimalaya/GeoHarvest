import logging
from typing import Dict, List, Optional, Any
from backend.providers.base.provider import DataProvider
from backend.providers.aws_earthsearch.provider import AWSEarthSearchProvider
from backend.providers.planetary_computer.provider import PlanetaryComputerProvider
from backend.core.sources.registry import source_registry
from backend.core.credentials.manager import credential_manager
from backend.app.schemas.schemas import ProviderInfo, SearchResultItem

logger = logging.getLogger("geoharvest.discovery.manager")


class DiscoveryManager:
    def __init__(self):
        self._providers: Dict[str, DataProvider] = {
            "aws-earthsearch": AWSEarthSearchProvider(),
            "planetary-computer": PlanetaryComputerProvider(),
        }

    def list_providers(self) -> List[ProviderInfo]:
        providers = []
        for s in source_registry.list_sources():
            if s.source_id == "local-filesystem":
                continue
            is_stac = (
                "stac" in s.name.lower()
                or "earthsearch" in s.source_id
                or "planetary" in s.source_id
                or "dataspace" in s.source_id
                or "cmr" in s.name.lower()
            )
            # Evaluate true authentication / credentials configuration
            cred = credential_manager.get_platform_status(s.source_id)
            if cred is not None:
                is_auth = bool(cred.is_configured)
            else:
                is_auth = not s.capabilities.supports_authentication

            providers.append(
                ProviderInfo(
                    provider_id=s.source_id,
                    name=s.name,
                    type="stac" if is_stac else "catalog_api",
                    enabled=True,
                    authenticated=is_auth,
                    collections=s.capabilities.collections,
                )
            )
        return providers

    def get_provider(self, provider_id: str) -> Optional[DataProvider]:
        return self._providers.get(provider_id)

    async def search(
        self,
        provider_id: str,
        collection: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        aoi: Optional[Dict[str, Any]] = None,
        bbox: Optional[List[float]] = None,
        max_cloud_cover: Optional[float] = 20.0,
        limit: int = 50,
    ) -> List[SearchResultItem]:
        # Adapt filters for radar or static elevation datasets
        effective_cloud_cover = max_cloud_cover
        if collection in ["sentinel-1-grd", "cop-dem-glo-30", "nasadem-hgt-v001", "rgi-glacier-outlines"]:
            effective_cloud_cover = None

        filters = {
            "collection": collection,
            "max_cloud_cover": effective_cloud_cover,
            "limit": limit,
            "bbox": bbox,
        }

        # Check registered source ecosystem first
        source = source_registry.get(provider_id)
        if source and provider_id not in ["aws-earthsearch", "planetary-computer"]:
            try:
                return await source.search(
                    aoi=aoi,
                    start_date=start_date or "",
                    end_date=end_date or "",
                    filters=filters,
                )
            except Exception as e:
                logger.error(f"Error querying ecosystem source '{provider_id}': {e}", exc_info=True)
                if provider_id in ["copernicus-dataspace", "isro-bhuvan-vedas", "ecmwf-cds", "opentopography-glacier"]:
                    return []

        # Fallback to direct providers (aws-earthsearch or planetary-computer)
        provider = self.get_provider(provider_id) or self._providers["aws-earthsearch"]
        return await provider.search(
            aoi=aoi,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        )


discovery_manager = DiscoveryManager()
