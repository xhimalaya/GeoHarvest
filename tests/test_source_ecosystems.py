import pytest
from backend.core.sources.registry import source_registry
from backend.core.discovery.manager import discovery_manager
from backend.app.schemas.schemas import SearchResultItem


def test_source_ecosystem_registration():
    """Verify all 8 source ecosystems are registered in SourceRegistry."""
    sources = source_registry.list_sources()
    assert len(sources) >= 8

    source_ids = [s.source_id for s in sources]
    assert "aws-earthsearch" in source_ids
    assert "planetary-computer" in source_ids
    assert "nasa-earthdata" in source_ids
    assert "copernicus-dataspace" in source_ids
    assert "isro-bhuvan-vedas" in source_ids
    assert "ecmwf-cds" in source_ids
    assert "opentopography-glacier" in source_ids
    assert "local-filesystem" in source_ids


def test_discovery_manager_ecosystem_providers():
    """Verify DiscoveryManager exposes all STAC & catalog API source ecosystems."""
    providers = discovery_manager.list_providers()
    assert len(providers) >= 6

    p_ids = [p.provider_id for p in providers]
    assert "aws-earthsearch" in p_ids
    assert "planetary-computer" in p_ids
    assert "nasa-earthdata" in p_ids
    assert "copernicus-dataspace" in p_ids
    assert "isro-bhuvan-vedas" in p_ids
    assert "ecmwf-cds" in p_ids
    assert "opentopography-glacier" in p_ids


@pytest.mark.asyncio
async def test_ecosystem_search_routing():
    """Verify DiscoveryManager routes searches across non-default source ecosystems."""
    # 1. Search ISRO ecosystem
    isro_results = await discovery_manager.search(
        provider_id="isro-bhuvan-vedas",
        collection="isro-resourcesat-2a",
        start_date="2024-06-01",
        end_date="2024-06-30",
        bbox=[77.0, 34.0, 78.0, 35.0]
    )
    assert isinstance(isro_results, list)
    assert len(isro_results) >= 1
    assert isinstance(isro_results[0], SearchResultItem)
    assert "resourcesat" in isro_results[0].collection

    # 2. Search ECMWF CDS ecosystem
    cds_results = await discovery_manager.search(
        provider_id="ecmwf-cds",
        collection="ecmwf-era5-reanalysis",
        start_date="2024-06-01",
        end_date="2024-06-15",
        bbox=[77.0, 34.0, 78.0, 35.0]
    )
    assert isinstance(cds_results, list)
    assert len(cds_results) >= 1
    assert "era5" in cds_results[0].collection

    # 3. Search OpenTopography & Glacier ecosystem
    glacier_results = await discovery_manager.search(
        provider_id="opentopography-glacier",
        collection="rgi-glacier-outlines",
        bbox=[77.0, 34.0, 78.0, 35.0]
    )
    assert isinstance(glacier_results, list)
    assert len(glacier_results) >= 1
    assert "rgi" in glacier_results[0].collection


def test_copernicus_sentinel_priority():
    """Verify Sentinel missions prioritize Copernicus Data Space as primary ecosystem."""
    from backend.core.satellites.catalog import master_catalog
    s2 = master_catalog.get_mission("sentinel-2")
    assert s2 is not None
    assert s2.supported_ecosystems[0] == "copernicus-dataspace"

    s1 = master_catalog.get_mission("sentinel-1-sar")
    assert s1 is not None
    assert s1.supported_ecosystems[0] == "copernicus-dataspace"

    dem = master_catalog.get_mission("cop-dem-30")
    assert dem is not None
    assert dem.supported_ecosystems[0] == "copernicus-dataspace"


def test_copernicus_cdse_raster_adaptation():
    """Verify CDSE STAC item assets (B02_10m, TCI_10m, etc.) adapt to canonical band aliases."""
    from backend.core.sources.datasets.raster import RasterDatasetAdapter
    adapter = RasterDatasetAdapter()

    cdse_item = {
        "id": "S2A_MSIL2A_20240615T053651_N0510_R005_T43SGU_20240615T103157",
        "collection": "sentinel-2-l2a",
        "bbox": [77.0, 34.0, 78.0, 35.0],
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {
            "datetime": "2024-06-15T05:36:51Z",
            "title": "Sentinel-2 L2A Scene",
            "eo:cloud_cover": 4.2
        },
        "assets": {
            "B02_10m": {"href": "https://dataspace.copernicus.eu/b02.jp2", "type": "image/jp2"},
            "B03_10m": {"href": "https://dataspace.copernicus.eu/b03.jp2", "type": "image/jp2"},
            "B04_10m": {"href": "https://dataspace.copernicus.eu/b04.jp2", "type": "image/jp2"},
            "B08_10m": {"href": "https://dataspace.copernicus.eu/b08.jp2", "type": "image/jp2"},
            "TCI_10m": {"href": "https://dataspace.copernicus.eu/tci.jp2", "type": "image/jp2"},
            "thumbnail": {"href": "https://dataspace.copernicus.eu/thumb.jpg", "type": "image/jpeg"}
        }
    }

    result = adapter.adapt(cdse_item, provider_id="copernicus-dataspace")
    assert result.id == "S2A_MSIL2A_20240615T053651_N0510_R005_T43SGU_20240615T103157"
    assert result.cloud_cover == 4.2
    assert result.thumbnail_url == "https://dataspace.copernicus.eu/thumb.jpg"
    assert "blue" in result.assets
    assert "green" in result.assets
    assert "red" in result.assets
    assert "nir" in result.assets
    assert "visual" in result.assets
    assert "thumbnail" in result.assets

