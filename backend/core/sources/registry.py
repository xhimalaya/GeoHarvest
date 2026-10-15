from typing import Dict, List, Optional
from pathlib import Path
from backend.core.sources.base import Source, Capabilities, ConnectionTestResult
from backend.core.sources.connectors.http import HttpConnector
from backend.core.sources.connectors.local import LocalFileConnector
from backend.core.sources.discovery.stac import StacDiscoveryAdapter
from backend.core.sources.discovery.nasa_cmr import NasaCmrDiscoveryAdapter
from backend.core.sources.discovery.copernicus_cdse import CopernicusCdseDiscoveryAdapter
from backend.core.sources.discovery.isro_vedas import IsroVedasDiscoveryAdapter
from backend.core.sources.discovery.ecmwf_cds import EcmwfCdsDiscoveryAdapter
from backend.core.sources.discovery.opentopo_glacier import OpenTopoGlacierDiscoveryAdapter
from backend.core.sources.datasets.raster import RasterDatasetAdapter
from backend.core.sources.transfer.http import HttpTransferAdapter
from backend.app.dependencies.config import settings


class SourceRegistry:
    """Manages configured Sources and handles runtime dispatching across all data ecosystems."""

    def __init__(self):
        self._sources: Dict[str, Source] = {}
        self._register_default_sources()

    def _register_default_sources(self):
        raster_adapter = RasterDatasetAdapter()
        transfer_adapter = HttpTransferAdapter()

        # 1. AWS Earth Search STAC (Element 84)
        self.register(
            Source(
                source_id="aws-earthsearch",
                name="AWS Earth Search (Element 84)",
                connector=HttpConnector("https://earth-search.aws.element84.com/v1"),
                discovery=StacDiscoveryAdapter("https://earth-search.aws.element84.com/v1", default_collection="sentinel-2-l2a"),
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=True,
                    supports_temporal_filter=True,
                    supports_range_request=True,
                    supports_authentication=False,
                    protocols=["http", "https"],
                    collections=["sentinel-2-l2a", "sentinel-2-c1-l2a", "landsat-c2-l2", "sentinel-1-grd", "cop-dem-glo-30"]
                )
            )
        )

        # 2. Microsoft Planetary Computer STAC
        self.register(
            Source(
                source_id="planetary-computer",
                name="Microsoft Planetary Computer",
                connector=HttpConnector("https://planetarycomputer.microsoft.com/api/stac/v1"),
                discovery=StacDiscoveryAdapter("https://planetarycomputer.microsoft.com/api/stac/v1", default_collection="sentinel-2-l2a"),
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=True,
                    supports_temporal_filter=True,
                    supports_range_request=True,
                    supports_authentication=True,
                    protocols=["http", "https"],
                    collections=["sentinel-2-l2a", "landsat-c2-l2", "modis-09a1-061", "cop-dem-glo-30"]
                )
            )
        )

        # 3. NASA Earthdata CMR STAC & DAACs (LP DAAC, NSIDC, ASF, PO.DAAC)
        self.register(
            Source(
                source_id="nasa-earthdata",
                name="NASA Earthdata CMR & DAACs",
                connector=HttpConnector("https://cmr.earthdata.nasa.gov/stac"),
                discovery=NasaCmrDiscoveryAdapter("https://cmr.earthdata.nasa.gov/stac"),
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=True,
                    supports_temporal_filter=True,
                    supports_range_request=True,
                    supports_authentication=False,  # CMR STAC search is open public
                    protocols=["http", "https"],
                    collections=["modis-09a1-061", "viirs-vnp09ga", "icesat2-atl06-land-ice", "nasa-gedi-l2a-elevation", "nasadem-hgt-v001", "ecostress-l2-lste", "nasa-swot-l2-water"]
                )
            )
        )

        # 4. Copernicus Data Space Ecosystem (CDSE)
        self.register(
            Source(
                source_id="copernicus-dataspace",
                name="Copernicus Data Space Ecosystem (CDSE)",
                connector=HttpConnector("https://stac.dataspace.copernicus.eu/v1"),
                discovery=CopernicusCdseDiscoveryAdapter("https://stac.dataspace.copernicus.eu/v1"),
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=True,
                    supports_temporal_filter=True,
                    supports_range_request=True,
                    supports_authentication=False,  # CDSE STAC search is open
                    protocols=["http", "https"],
                    collections=["sentinel-1-grd", "sentinel-2-l2a", "sentinel-3-sral", "sentinel-5p-l2-tropomi", "cop-dem-glo-30"]
                )
            )
        )

        # 5. ISRO / Bhuvan / Bhoonidhi / VEDAS Catalog
        self.register(
            Source(
                source_id="isro-bhuvan-vedas",
                name="ISRO / Bhuvan / Bhoonidhi / VEDAS Catalog",
                connector=HttpConnector("https://bhuvan.nrsc.gov.in"),
                discovery=IsroVedasDiscoveryAdapter("https://bhoonidhi.nrsc.gov.in/api/v1"),
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=True,
                    supports_temporal_filter=True,
                    supports_range_request=True,
                    supports_authentication=True,
                    protocols=["http", "https", "wcs"],
                    collections=[
                        "bhuvan-cartodem-30m",
                        "bhuvan-lulc-250k",
                        "bhuvan-snow-himalaya",
                        "isro-resourcesat-2a",
                        "isro-cartosat-pan",
                        "isro-eos04-sar",
                        "isro-oceansat-ocm",
                        "isro-insat-3d-met"
                    ]
                )
            )
        )

        # 6. ECMWF Climate Data Store (CDS) Reanalysis
        self.register(
            Source(
                source_id="ecmwf-cds",
                name="ECMWF Climate Data Store (CDS)",
                connector=HttpConnector("https://cds.climate.copernicus.eu"),
                discovery=EcmwfCdsDiscoveryAdapter("https://cds.climate.copernicus.eu/api/v2"),
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=True,
                    supports_temporal_filter=True,
                    supports_range_request=True,
                    supports_authentication=True,
                    protocols=["http", "https"],
                    collections=["ecmwf-era5-reanalysis"]
                )
            )
        )

        # 7. OpenTopography & Glacier Reference Services
        self.register(
            Source(
                source_id="opentopography-glacier",
                name="OpenTopography & Glacier Services",
                connector=HttpConnector("https://portal.opentopography.org"),
                discovery=OpenTopoGlacierDiscoveryAdapter("https://portal.opentopography.org/API"),
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=True,
                    supports_temporal_filter=False,
                    supports_range_request=True,
                    supports_authentication=False,
                    protocols=["http", "https"],
                    collections=["rgi-glacier-outlines", "glims-glacier-database", "nasadem-hgt-v001", "alos-aw3d30", "cop-dem-glo-30"]
                )
            )
        )

        # 8. Local Filesystem Archive
        local_dir = settings.downloads_dir
        local_connector = LocalFileConnector(local_dir)
        self.register(
            Source(
                source_id="local-filesystem",
                name="Local Storage Repository",
                connector=local_connector,
                discovery=StacDiscoveryAdapter("https://earth-search.aws.element84.com/v1"),  # Fallback discovery
                dataset=raster_adapter,
                transfer=transfer_adapter,
                capabilities=Capabilities(
                    supports_spatial_filter=False,
                    supports_temporal_filter=False,
                    supports_range_request=True,
                    supports_authentication=False,
                    protocols=["file"],
                    collections=["local-archive"]
                )
            )
        )

    def register(self, source: Source):
        self._sources[source.source_id] = source

    def get(self, source_id: str) -> Optional[Source]:
        return self._sources.get(source_id)

    def list_sources(self) -> List[Source]:
        return list(self._sources.values())

    async def test_source_connection(self, source_id: str) -> ConnectionTestResult:
        source = self.get(source_id)
        if not source:
            return ConnectionTestResult(
                success=False,
                latency_ms=0.0,
                message=f"Source '{source_id}' not found in registry"
            )
        return await source.test_connection()


source_registry = SourceRegistry()
