import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pathlib import Path
from backend.core.processing.algorithms import algorithm_registry
from backend.core.processing.raster_ops import RasterOps


@pytest.fixture
def multiband_synthetic_raster(tmp_path):
    """Creates a 60x60 3-band synthetic satellite raster in EPSG:4326 over Ladakh."""
    file_path = tmp_path / "multispectral_sample.tif"
    width, height = 60, 60
    transform = from_origin(77.5, 34.2, 0.001, 0.001)

    # 3 distinct clusters:
    # 1. Low reflectance (water/shadow)
    # 2. Moderate green reflectance
    # 3. High NIR/built-up reflectance
    band1 = np.zeros((height, width), dtype=np.float32)
    band2 = np.zeros((height, width), dtype=np.float32)
    band3 = np.zeros((height, width), dtype=np.float32)

    band1[:20, :] = 200.0
    band2[:20, :] = 300.0
    band3[:20, :] = 250.0

    band1[20:40, :] = 1200.0
    band2[20:40, :] = 2500.0
    band3[20:40, :] = 1800.0

    band1[40:, :] = 4000.0
    band2[40:, :] = 4500.0
    band3[40:, :] = 5000.0

    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 3,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": -9999.0
    }

    with rasterio.open(str(file_path), "w", **meta) as dst:
        dst.write(band1, 1)
        dst.write(band2, 2)
        dst.write(band3, 3)

    return str(file_path.resolve())


def test_algorithm_registry_loading():
    algos = algorithm_registry.list_all()
    assert len(algos) >= 7
    ids = [a.id for a in algos]
    assert "ml.kmeans" in ids
    assert "raster.polygonize" in ids
    assert "raster.change_detection" in ids
    assert "indices.ndvi" in ids
    assert "indices.ndsi" in ids
    assert "ml.random_forest" in ids

    kmeans = algorithm_registry.get("ml.kmeans")
    assert kmeans.name == "K-Means Unsupervised Clustering"
    assert len(kmeans.parameters) >= 3


def test_kmeans_clustering(multiband_synthetic_raster, tmp_path):
    out_path = str(tmp_path / "kmeans_output.tif")
    res = RasterOps.kmeans_clustering(
        input_path=multiband_synthetic_raster,
        output_path=out_path,
        n_clusters=3,
        max_iter=50,
        random_state=42,
        to_cog=False
    )

    assert Path(out_path).exists()
    assert res["n_clusters"] == 3
    assert len(res["clusters"]) == 3
    assert res["total_valid_pixels"] == 60 * 60

    # Verify output raster values are in [0, 1, 2]
    with rasterio.open(out_path) as src:
        data = src.read(1)
        unique_vals = set(np.unique(data))
        assert unique_vals.issubset({0, 1, 2})


def test_polygonize_raster(multiband_synthetic_raster, tmp_path):
    # Cluster first to get discrete classes
    kmeans_out = str(tmp_path / "kmeans_classified.tif")
    RasterOps.kmeans_clustering(
        input_path=multiband_synthetic_raster,
        output_path=kmeans_out,
        n_clusters=3,
        to_cog=False
    )

    geojson_out = str(tmp_path / "extracted_polygons.geojson")
    res = RasterOps.polygonize_raster(
        input_path=kmeans_out,
        output_geojson_path=geojson_out,
        min_area_m2=10.0,
        simplify_tolerance=0.0001
    )

    assert Path(geojson_out).exists()
    assert res["feature_count"] >= 3
    assert res["total_area_m2"] > 0
    assert res["geojson"] is not None
    assert res["geojson"]["type"] == "FeatureCollection"


def test_change_detection(multiband_synthetic_raster, tmp_path):
    # Create T2 with higher values
    t2_path = tmp_path / "t2_sample.tif"
    with rasterio.open(multiband_synthetic_raster) as src:
        meta = src.meta.copy()
        data = src.read(1) + 500.0  # Increased reflectance
        meta.update(count=1)
        with rasterio.open(str(t2_path), "w", **meta) as dst:
            dst.write(data, 1)

    out_diff = str(tmp_path / "change_diff.tif")
    res = RasterOps.change_detection(
        pre_path=multiband_synthetic_raster,
        post_path=str(t2_path),
        output_path=out_diff,
        method="difference",
        threshold=100.0,
        to_cog=False
    )

    assert Path(out_diff).exists()
    assert res["gain_pixels"] > 0
    assert res["gain_percentage"] > 90.0
    assert res["mean_change"] == pytest.approx(500.0, rel=1e-2)


def test_scientific_validation(multiband_synthetic_raster):
    res = RasterOps.scientific_validation(
        raster_path=multiband_synthetic_raster,
        algorithm_id="ml.kmeans"
    )
    assert res["valid"] is True
    assert res["layer1_data"]["passed"] is True
    assert len(res["layer1_data"]["checks"]) >= 4
    assert res["layer4_scientific"]["status"] == "requires_interpretation"
