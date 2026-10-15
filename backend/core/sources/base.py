from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field
from backend.app.schemas.schemas import SearchResultItem, AssetInfo
from backend.app.models.models import DownloadStatus


class ConnectionTestResult(BaseModel):
    success: bool
    latency_ms: float = 0.0
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class Capabilities(BaseModel):
    supports_spatial_filter: bool = True
    supports_temporal_filter: bool = True
    supports_range_request: bool = True
    supports_authentication: bool = False
    protocols: List[str] = Field(default_factory=lambda: ["http", "https"])
    collections: List[str] = Field(default_factory=list)


class Connector(ABC):
    """Handles network transport, authentication, and liveness testing."""

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        pass

    async def close(self):
        pass


class DiscoveryAdapter(ABC):
    """Handles querying and discovery of items / scenes across catalogs."""

    @abstractmethod
    async def discover(
        self,
        aoi: Optional[Dict[str, Any]],
        start_date: str,
        end_date: str,
        filters: Dict[str, Any]
    ) -> List[Any]:
        pass

    @abstractmethod
    async def get_metadata(self, item_id: str) -> Dict[str, Any]:
        pass


class DatasetAdapter(ABC):
    """Maps raw source discovery items into standardized GeoHarvest SearchResultItem and Asset models."""

    @abstractmethod
    def adapt(self, raw_item: Any, provider_id: str) -> SearchResultItem:
        pass


class TransferAdapter(ABC):
    """Handles downloading or copying assets with resume and checksum support."""

    @abstractmethod
    async def transfer(
        self,
        url_or_path: str,
        destination_path: Any,
        expected_size: Optional[int] = None,
        expected_checksum: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, float, DownloadStatus, Optional[str]], None]] = None,
        cancellation_event: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        pass


class Source:
    """Pluggable GeoHarvest Data Source combining Connector, Discovery, Dataset Adapter, and Transfer."""

    def __init__(
        self,
        source_id: str,
        name: str,
        connector: Connector,
        discovery: DiscoveryAdapter,
        dataset: DatasetAdapter,
        transfer: TransferAdapter,
        capabilities: Capabilities
    ):
        self.source_id = source_id
        self.name = name
        self.connector = connector
        self.discovery = discovery
        self.dataset = dataset
        self.transfer = transfer
        self.capabilities = capabilities

    async def test_connection(self) -> ConnectionTestResult:
        return await self.connector.test_connection()

    async def search(
        self,
        aoi: Optional[Dict[str, Any]],
        start_date: str,
        end_date: str,
        filters: Dict[str, Any]
    ) -> List[SearchResultItem]:
        raw_items = await self.discovery.discover(
            aoi=aoi,
            start_date=start_date,
            end_date=end_date,
            filters=filters
        )
        return [self.dataset.adapt(item, self.source_id) for item in raw_items]
