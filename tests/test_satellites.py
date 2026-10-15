import pytest
from backend.core.satellites.constellations import (
    constellation_registry,
    SatelliteConstellation,
    BandDefinition,
)
from backend.core.processing.recipes import recipe_registry
from backend.core.storage.estimator import StorageEstimator
from backend.core.discovery.manager import DiscoveryManager
from backend.providers.aws_earthsearch.provider import AWSEarthSearchProvider
from backend.app.schemas.schemas import SearchResultItem, AssetInfo


def test_constellation_registry():
    """Verify satellite constellations are correctly registered and configured."""
    constellations = constellation_registry.list_constellations()
    assert len(constellations) >= 4

    ids = [c.id for c in constellations]
    assert "sentinel-2" in ids
    assert "landsat-8-9" in ids
    assert "sentinel-1-sar" in ids
    assert "cop-dem-30" in ids

    # Test get_by_id
    s2 = constellation_registry.get_by_id("sentinel-2")
    assert s2 is not None
    assert s2.sensor_type == "OPTICAL"
    assert s2.resolution_meters == 10.0
    assert s2.supports_cloud_filter is True
    assert s2.supports_datetime_filter is True
    s2_band_ids = [b.id for b in s2.bands]
    assert "visual" in s2_band_ids
    assert "red" in s2_band_ids
    assert "green" in s2_band_ids
    assert "blue" in s2_band_ids
    assert "nir" in s2_band_ids

    landsat = constellation_registry.get_by_id("landsat-8-9")
    assert landsat is not None
    assert landsat.sensor_type == "OPTICAL"
    assert landsat.resolution_meters == 30.0
    assert landsat.supports_cloud_filter is True
    assert landsat.supports_datetime_filter is True
    l_band_ids = [b.id for b in landsat.bands]
    assert "red" in l_band_ids
    assert "nir08" in l_band_ids
    assert "lwir11" in l_band_ids
    assert "qa_pixel" in l_band_ids

    s1 = constellation_registry.get_by_id("sentinel-1-sar")
    assert s1 is not None
    assert s1.sensor_type == "SAR"
    assert s1.resolution_meters == 10.0
    assert s1.supports_cloud_filter is False  # Radar penetrates clouds
    assert s1.supports_datetime_filter is True
    s1_band_ids = [b.id for b in s1.bands]
    assert "vv" in s1_band_ids
    assert "vh" in s1_band_ids

    dem = constellation_registry.get_by_id("cop-dem-30")
    assert dem is not None
    assert dem.sensor_type == "DEM"
    assert dem.resolution_meters == 30.0
    assert dem.supports_cloud_filter is False  # Static elevation raster
    assert dem.supports_datetime_filter is False  # Static model
    dem_band_ids = [b.id for b in dem.bands]
    assert "data" in dem_band_ids

    # Test get_by_collection
    assert constellation_registry.get_by_collection("sentinel-2-l2a").id == "sentinel-2"
    assert constellation_registry.get_by_collection("landsat-c2-l2").id == "landsat-8-9"
    assert constellation_registry.get_by_collection("sentinel-1-grd").id == "sentinel-1-sar"
    assert constellation_registry.get_by_collection("cop-dem-glo-30").id == "cop-dem-30"
    assert constellation_registry.get_by_id("non-existent") is None


def test_api_satellites_endpoint(client):
    """Verify GET /api/satellites returns constellations with accurate schemas."""
    response = client.get("/api/satellites")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4

    constell_map = {item["id"]: item for item in data}
    assert "sentinel-2" in constell_map
    assert "landsat-8-9" in constell_map
    assert "sentinel-1-sar" in constell_map
    assert "cop-dem-30" in constell_map

    # Check Landsat details
    l_data = constell_map["landsat-8-9"]
    assert l_data["agency"] == "USGS / NASA"
    assert l_data["resolution_meters"] == 30.0
    assert l_data["supports_cloud_filter"] is True

    # Check Sentinel-1 details
    s1_data = constell_map["sentinel-1-sar"]
    assert s1_data["sensor_type"] == "SAR"
    assert s1_data["supports_cloud_filter"] is False

    # Check DEM details
    dem_data = constell_map["cop-dem-30"]
    assert dem_data["sensor_type"] == "DEM"
    assert dem_data["supports_datetime_filter"] is False


def test_multi_satellite_recipes(client):
    """Verify processing recipes exist for multi-satellite workflows."""
    response = client.get("/api/processing/recipes")
    assert response.status_code == 200
    recipes = response.json()
    recipe_ids = [r["id"] for r in recipes]

    assert "s2-aoi-cog" in recipe_ids
    assert "landsat-aoi-cog" in recipe_ids
    assert "landsat-ndvi" in recipe_ids
    assert "s1-grd-cog" in recipe_ids
    assert "dem-aoi-cog" in recipe_ids

    # Check landsat-ndvi step parameters
    l_ndvi = recipe_registry.get("landsat-ndvi")
    ndvi_step = next(s for s in l_ndvi.steps if s.name == "ndvi")
    assert ndvi_step.parameters["band1"] == "nir08"
    assert ndvi_step.parameters["band2"] == "red"

    # Check dem-aoi-cog step parameters
    dem_recipe = recipe_registry.get("dem-aoi-cog")
    clip_step = next(s for s in dem_recipe.steps if s.name == "clip")
    assert clip_step.parameters["nodata"] == -9999.0


def test_multi_satellite_storage_estimator():
    """Verify storage estimation functions properly for Landsat, SAR, and DEM assets."""
    landsat_scene = SearchResultItem(
        id="LC08_L2SP_146037_20240628_02_T1",
        collection="landsat-c2-l2",
        provider_id="aws-earthsearch",
        bbox=[76.0, 34.0, 77.0, 35.0],
        geometry={"type": "Polygon", "coordinates": [[[76.0, 34.0], [77.0, 34.0], [77.0, 35.0], [76.0, 35.0], [76.0, 34.0]]]},
        assets={
            "red": AssetInfo(name="red", band="B04", url="http://example.com/sr_b4.tif", size_bytes=60 * 1024 * 1024),
            "nir08": AssetInfo(name="nir08", band="B05", url="http://example.com/sr_b5.tif", size_bytes=60 * 1024 * 1024),
            "qa_pixel": AssetInfo(name="qa_pixel", band="QA_PIXEL", url="http://example.com/qa.tif", size_bytes=25 * 1024 * 1024),
        }
    )
    est_landsat = StorageEstimator.estimate([landsat_scene], ["red", "nir08", "qa_pixel"])
    assert est_landsat.scene_count == 1
    assert est_landsat.asset_count == 3
    assert est_landsat.raw_bytes == (60 + 60 + 25) * 1024 * 1024

    s1_scene = SearchResultItem(
        id="S1A_IW_GRDH_1SDV_20240630T124110",
        collection="sentinel-1-grd",
        provider_id="aws-earthsearch",
        bbox=[76.0, 34.0, 77.0, 35.0],
        geometry={"type": "Polygon", "coordinates": [[[76.0, 34.0], [77.0, 34.0], [77.0, 35.0], [76.0, 35.0], [76.0, 34.0]]]},
        assets={
            "vv": AssetInfo(name="vv", band="VV", url="http://example.com/vv.tif", size_bytes=85 * 1024 * 1024),
            "vh": AssetInfo(name="vh", band="VH", url="http://example.com/vh.tif", size_bytes=85 * 1024 * 1024),
        }
    )
    est_s1 = StorageEstimator.estimate([s1_scene], ["vv", "vh"])
    assert est_s1.scene_count == 1
    assert est_s1.asset_count == 2
    assert est_s1.raw_bytes == (85 + 85) * 1024 * 1024

    dem_scene = SearchResultItem(
        id="Copernicus_DSM_COG_10_N35_00_E079_00_DEM",
        collection="cop-dem-glo-30",
        provider_id="aws-earthsearch",
        bbox=[76.0, 34.0, 77.0, 35.0],
        geometry={"type": "Polygon", "coordinates": [[[76.0, 34.0], [77.0, 34.0], [77.0, 35.0], [76.0, 35.0], [76.0, 34.0]]]},
        assets={
            "data": AssetInfo(name="data", band="DEM", url="http://example.com/dem.tif", size_bytes=25 * 1024 * 1024),
        }
    )
    est_dem = StorageEstimator.estimate([dem_scene], ["data"])
    assert est_dem.scene_count == 1
    assert est_dem.asset_count == 1
    assert est_dem.raw_bytes == 25 * 1024 * 1024


def test_aws_earthsearch_item_parsing():
    """Unit test AWSEarthSearchProvider item parser for Landsat, Sentinel-1, and DEM STAC items."""
    provider = AWSEarthSearchProvider()

    # 1. Landsat mock item
    landsat_mock = {
        "id": "LC08_L2SP_146037_20240628_02_T1",
        "collection": "landsat-c2-l2",
        "bbox": [76.5, 34.1, 77.5, 35.1],
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {
            "datetime": "2024-06-28T05:30:00Z",
            "eo:cloud_cover": 12.5,
            "title": "Landsat 8 L2 Scene"
        },
        "assets": {
            "red": {"href": "https://example.com/SR_B4.TIF", "title": "SR_B4 Red"},
            "nir08": {"href": "https://example.com/SR_B5.TIF", "title": "SR_B5 NIR"},
            "lwir11": {"href": "https://example.com/ST_B10.TIF", "title": "ST_B10 Thermal"},
            "qa_pixel": {"href": "https://example.com/QA_PIXEL.TIF", "title": "QA Pixel"},
            "reduced_resolution_browse": {"href": "https://example.com/browse.jpg", "title": "Browse"}
        }
    }
    parsed_l = provider._parse_items([landsat_mock], "landsat-c2-l2", max_cloud_cover=50.0)
    assert len(parsed_l) == 1
    item_l = parsed_l[0]
    assert item_l.id == "LC08_L2SP_146037_20240628_02_T1"
    assert item_l.cloud_cover == 12.5
    assert item_l.resolution_meters == 30.0
    assert "red" in item_l.assets
    assert item_l.assets["red"].band == "B04"
    assert item_l.assets["nir08"].band == "B05"
    assert item_l.assets["lwir11"].band == "B10"
    assert item_l.assets["qa_pixel"].band == "QA_PIXEL"
    assert item_l.thumbnail_url == "https://example.com/browse.jpg"

    # 2. Sentinel-1 SAR mock item
    s1_mock = {
        "id": "S1A_IW_GRDH_1SDV_20240630T124110",
        "collection": "sentinel-1-grd",
        "bbox": [76.5, 34.1, 77.5, 35.1],
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {
            "datetime": "2024-06-30T12:41:10Z",
            "title": "Sentinel-1 SAR GRD Scene"
        },
        "assets": {
            "vv": {"href": "https://example.com/vv.tif", "title": "VV Polarization"},
            "vh": {"href": "https://example.com/vh.tif", "title": "VH Polarization"},
            "thumbnail": {"href": "https://example.com/s1_thumb.jpg", "title": "Preview"}
        }
    }
    parsed_s1 = provider._parse_items([s1_mock], "sentinel-1-grd", max_cloud_cover=100.0)
    assert len(parsed_s1) == 1
    item_s1 = parsed_s1[0]
    assert item_s1.cloud_cover is None  # Radar has no cloud cover
    assert item_s1.resolution_meters == 10.0
    assert "vv" in item_s1.assets
    assert item_s1.assets["vv"].band == "VV"
    assert "vh" in item_s1.assets
    assert item_s1.assets["vh"].band == "VH"
    assert item_s1.thumbnail_url == "https://example.com/s1_thumb.jpg"

    # 3. Copernicus DEM mock item
    dem_mock = {
        "id": "Copernicus_DSM_COG_10_N35_00_E079_00_DEM",
        "collection": "cop-dem-glo-30",
        "bbox": [76.5, 34.1, 77.5, 35.1],
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {
            "title": "Copernicus DEM 30m Tile"
        },
        "assets": {
            "data": {"href": "https://example.com/dem.tif", "title": "DEM Elevation Raster"}
        }
    }
    parsed_dem = provider._parse_items([dem_mock], "cop-dem-glo-30", max_cloud_cover=100.0)
    assert len(parsed_dem) == 1
    item_dem = parsed_dem[0]
    assert item_dem.cloud_cover is None
    assert item_dem.resolution_meters == 30.0
    assert "data" in item_dem.assets
    assert item_dem.assets["data"].band == "DEM"


@pytest.mark.asyncio
async def test_discovery_manager_multi_satellite_search():
    """Integration test verifying DiscoveryManager search supports Landsat, Sentinel-1, and DEM."""
    mgr = DiscoveryManager()
    bbox = [77.5, 34.1, 77.6, 34.2]

    # Landsat 8/9 search
    landsat_results = await mgr.search(
        provider_id="aws-earthsearch",
        collection="landsat-c2-l2",
        start_date="2024-06-01",
        end_date="2024-07-01",
        bbox=bbox,
        max_cloud_cover=50.0,
        limit=2
    )
    assert isinstance(landsat_results, list)
    if landsat_results:
        item = landsat_results[0]
        assert item.collection == "landsat-c2-l2"
        assert item.resolution_meters == 30.0

    # Sentinel-1 SAR search (all-weather radar)
    s1_results = await mgr.search(
        provider_id="aws-earthsearch",
        collection="sentinel-1-grd",
        start_date="2024-06-01",
        end_date="2024-07-01",
        bbox=bbox,
        limit=2
    )
    assert isinstance(s1_results, list)
    if s1_results:
        item = s1_results[0]
        assert item.collection == "sentinel-1-grd"
        assert "vv" in item.assets or "vh" in item.assets

    # Copernicus DEM GLO-30 search (static elevation model)
    dem_results = await mgr.search(
        provider_id="aws-earthsearch",
        collection="cop-dem-glo-30",
        bbox=bbox,
        limit=2
    )
    assert isinstance(dem_results, list)
    if dem_results:
        item = dem_results[0]
        assert item.collection == "cop-dem-glo-30"
        assert "data" in item.assets
