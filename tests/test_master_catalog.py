import pytest
from backend.core.satellites.catalog import master_catalog, DOMAINS, MASTER_MISSIONS
from backend.core.sources.discovery.isro_vedas import IsroVedasDiscoveryAdapter
from backend.core.sources.discovery.ecmwf_cds import EcmwfCdsDiscoveryAdapter
from backend.core.sources.discovery.opentopo_glacier import OpenTopoGlacierDiscoveryAdapter
from backend.core.sources.discovery.nasa_cmr import NasaCmrDiscoveryAdapter


def test_master_catalog_domains():
    """Verify all 11 scientific domains are catalogued with metadata."""
    domains = master_catalog.list_domains()
    domain_ids = [d.id for d in domains]
    assert "ALL" in domain_ids
    assert "OPTICAL" in domain_ids
    assert "SAR" in domain_ids
    assert "DEM" in domain_ids
    assert "CLIMATE" in domain_ids
    assert "ALTIMETRY" in domain_ids
    assert "THERMAL" in domain_ids
    assert "HYPERSPECTRAL" in domain_ids
    assert "LIDAR" in domain_ids
    assert "OCEAN" in domain_ids
    assert "ATMOSPHERE" in domain_ids
    assert "GLACIER" in domain_ids
    assert len(domains) == 12  # ALL + 11 specific domains


def test_master_catalog_missions_count():
    """Verify master catalog contains key constellations across global ecosystems."""
    missions = master_catalog.list_missions()
    assert len(missions) >= 20

    m_ids = [m.id for m in missions]
    # Check essential missions
    assert "sentinel-2" in m_ids
    assert "landsat-8-9" in m_ids
    assert "landsat-4-5-7" in m_ids
    assert "modis-terra-aqua" in m_ids
    assert "viirs-noaa-snpp" in m_ids
    assert "isro-resourcesat" in m_ids
    assert "isro-cartosat" in m_ids
    assert "sentinel-1-sar" in m_ids
    assert "isro-risat-eos04" in m_ids
    assert "jaxa-alos-palsar" in m_ids
    assert "cop-dem-30" in m_ids
    assert "nasadem-srtm-30" in m_ids
    assert "alos-world-3d" in m_ids
    assert "era5-reanalysis" in m_ids
    assert "icesat2-atlas" in m_ids
    assert "cryosat-2-siral" in m_ids
    assert "nasa-swot" in m_ids
    assert "nasa-gedi-lidar" in m_ids
    assert "rgi-glacier-inventory" in m_ids
    assert "glims-glacier-database" in m_ids


def test_master_catalog_filtering():
    """Test filtering by domain, agency, Ladakh priority, and text search."""
    # Domain filter SAR
    sar_missions = master_catalog.filter_missions(domain="SAR")
    assert len(sar_missions) >= 3
    for m in sar_missions:
        assert m.domain == "SAR"

    # Domain filter CLIMATE
    climate_missions = master_catalog.filter_missions(domain="CLIMATE")
    assert len(climate_missions) >= 1
    assert any(m.id == "era5-reanalysis" for m in climate_missions)

    # Domain filter GLACIER
    glacier_missions = master_catalog.filter_missions(domain="GLACIER")
    assert len(glacier_missions) >= 2
    assert any(m.id == "rgi-glacier-inventory" for m in glacier_missions)

    # Agency filter ISRO
    isro_missions = master_catalog.filter_missions(agency="ISRO")
    assert len(isro_missions) >= 4
    isro_ids = [m.id for m in isro_missions]
    assert "isro-resourcesat" in isro_ids
    assert "isro-cartosat" in isro_ids
    assert "isro-risat-eos04" in isro_ids

    # Ladakh priority filter
    ladakh_missions = master_catalog.filter_missions(ladakh_only=True)
    assert len(ladakh_missions) >= 15
    for m in ladakh_missions:
        assert m.is_ladakh_priority is True

    # Search query
    snow_missions = master_catalog.filter_missions(query="snow")
    assert len(snow_missions) >= 1


def test_api_domains_endpoint(client):
    """Verify GET /api/satellites/domains endpoint."""
    response = client.get("/api/satellites/domains")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 11
    ids = [d["id"] for d in data]
    assert "OPTICAL" in ids
    assert "SAR" in ids
    assert "CLIMATE" in ids


def test_api_ecosystems_endpoint(client):
    """Verify GET /api/satellites/ecosystems endpoint."""
    response = client.get("/api/satellites/ecosystems")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    eco_ids = [e["id"] for e in data]
    assert "aws-earthsearch" in eco_ids
    assert "nasa-earthdata" in eco_ids
    assert "isro-bhuvan-vedas" in eco_ids


def test_api_satellite_detail_endpoint(client):
    """Verify GET /api/satellites/{mission_id} endpoint."""
    # Sentinel-2
    res_s2 = client.get("/api/satellites/sentinel-2")
    assert res_s2.status_code == 200
    s2 = res_s2.json()
    assert s2["id"] == "sentinel-2"
    assert s2["domain"] == "OPTICAL"
    assert len(s2["bands"]) >= 5

    # ISRO Resourcesat
    res_irs = client.get("/api/satellites/isro-resourcesat")
    assert res_irs.status_code == 200
    irs = res_irs.json()
    assert irs["family"] == "Resourcesat"
    assert "ISRO" in irs["agency"]
    band_ids = [b["id"] for b in irs["bands"]]
    assert "awifs_b3" in band_ids

    # Non-existent
    res_404 = client.get("/api/satellites/unknown-satellite-xyz")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_ecosystem_discovery_adapters():
    """Unit test discovery adapters for ISRO, ECMWF, OpenTopography, and NASA CMR."""
    # 1. ISRO Adapter
    isro_adapter = IsroVedasDiscoveryAdapter()
    isro_results = await isro_adapter.discover(
        aoi=None,
        start_date="2024-06-01",
        end_date="2024-06-30",
        filters={"collection": "isro-resourcesat-2a"}
    )
    assert len(isro_results) >= 1
    assert "awifs_b3" in isro_results[0]["assets"]

    # 2. ECMWF CDS Adapter
    ecmwf_adapter = EcmwfCdsDiscoveryAdapter()
    ecmwf_results = await ecmwf_adapter.discover(
        aoi=None,
        start_date="2024-06-01",
        end_date="2024-06-30",
        filters={"collection": "ecmwf-era5-reanalysis"}
    )
    assert len(ecmwf_results) >= 1
    assert "2m_temperature" in ecmwf_results[0]["assets"]

    # 3. OpenTopography & Glacier Adapter
    glacier_adapter = OpenTopoGlacierDiscoveryAdapter()
    glacier_results = await glacier_adapter.discover(
        aoi=None,
        start_date="2024-01-01",
        end_date="2024-01-02",
        filters={"collection": "rgi-glacier-outlines"}
    )
    assert len(glacier_results) >= 1
    assert "glacier_polygons" in glacier_results[0]["assets"]
