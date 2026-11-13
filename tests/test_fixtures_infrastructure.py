import pytest
import numpy as np
import rasterio
from pathlib import Path
from backend.core.processing.raster_ops import RasterOps
from backend.core.aoi.engine import AOIEngine


@pytest.mark.unit
@pytest.mark.geospatial
def test_synthetic_raster_fixtures_integrity(fixtures_dir):
    """Verifies that all required synthetic raster fixtures exist and have expected geometry."""
    wgs84_tif = fixtures_dir / "rasters" / "sample_singleband_wgs84.tif"
    utm_tif = fixtures_dir / "rasters" / "sample_raster_utm43n.tif"
    dem_tif = fixtures_dir / "dem" / "sample_dem_elevation.tif"
    nodata_tif = fixtures_dir / "rasters" / "sample_raster_with_nodata.tif"
    multi_tif = fixtures_dir / "satellite" / "sample_multispectral_3band.tif"

    for p in [wgs84_tif, utm_tif, dem_tif, nodata_tif, multi_tif]:
        assert p.exists(), f"Fixture missing: {p}"
        meta = RasterOps.validate_raster(str(p))
        assert meta["valid"] is True
        assert meta["width"] == 50
        assert meta["height"] == 50

    # Specific CRS checks
    assert RasterOps.validate_raster(str(wgs84_tif))["crs"] == "EPSG:4326"
    assert RasterOps.validate_raster(str(utm_tif))["crs"] == "EPSG:32643"
    assert RasterOps.validate_raster(str(nodata_tif))["nodata"] == -9999.0


@pytest.mark.unit
@pytest.mark.geospatial
def test_synthetic_vector_fixtures_integrity(fixtures_dir):
    """Verifies that synthetic vector GeoJSON fixtures are valid polygons."""
    poly_path = fixtures_dir / "vectors" / "sample_aoi_polygon.geojson"
    multi_path = fixtures_dir / "vectors" / "sample_aoi_multipolygon.geojson"

    import json
    with open(poly_path) as f:
        poly_data = json.load(f)
    res_poly = AOIEngine.validate_and_analyze(geojson_data=poly_data)
    assert res_poly["valid"] is True
    assert res_poly["geometry_type"] == "Polygon"
    assert res_poly["area_km2"] > 0

    with open(multi_path) as f:
        multi_data = json.load(f)
    res_multi = AOIEngine.validate_and_analyze(geojson_data=multi_data)
    assert res_multi["valid"] is True
    assert res_multi["geometry_type"] == "MultiPolygon"
    assert res_multi["area_km2"] > 0


@pytest.mark.geospatial
@pytest.mark.physical
def test_physical_ndvi_on_synthetic_satellite_fixture(fixtures_dir, isolated_test_dir):
    """Verifies physical index derivation using the 3-band multispectral synthetic satellite fixture."""
    multi_tif = fixtures_dir / "satellite" / "sample_multispectral_3band.tif"
    out_ndvi = str(isolated_test_dir / "derived_ndvi.tif")

    res = RasterOps.calc_spectral_index_advanced(
        index_type="ndvi",
        output_path=out_ndvi,
        band1_path=str(multi_tif),  # NIR (band 3)
        band2_path=str(multi_tif),  # Red (band 2)
        band1_idx=3,
        band2_idx=2,
        to_cog=False
    )

    assert Path(out_ndvi).exists()
    assert res["mean"] == pytest.approx(0.60, abs=1e-2)

    with rasterio.open(out_ndvi) as src:
        data = src.read(1)
        assert data.shape == (50, 50)
        assert np.allclose(data, 0.60, atol=1e-2)
