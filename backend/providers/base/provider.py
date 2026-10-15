from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from backend.app.schemas.schemas import SearchResultItem, AssetInfo


class DataProvider(ABC):
    """Abstract base class for all GeoHarvest satellite and geospatial data providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'aws-earthsearch', 'planetary-computer')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        pass

    @abstractmethod
    async def search(
        self,
        aoi: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResultItem]:
        """Search the provider catalog for scenes matching the criteria."""
        pass

    @abstractmethod
    async def get_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """Fetch full metadata for a specific dataset/scene."""
        pass

    @abstractmethod
    async def get_assets(self, dataset_id: str) -> Dict[str, AssetInfo]:
        """Retrieve available asset links for a dataset/scene."""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate or refresh tokens if necessary."""
        pass
