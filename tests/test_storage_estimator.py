from backend.core.storage.estimator import StorageEstimator, format_bytes
from backend.app.schemas.schemas import SearchResultItem, AssetInfo


def test_format_bytes():
    assert format_bytes(500) == "500.00 B"
    assert format_bytes(1024 * 1024) == "1.00 MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"


def test_storage_estimator_calculation():
    scene = SearchResultItem(
        id="S2A_TEST_SCENE",
        collection="sentinel-2-l2a",
        provider_id="aws-earthsearch",
        bbox=[76.0, 34.0, 77.0, 35.0],
        geometry={"type": "Polygon", "coordinates": [[[76.0, 34.0], [77.0, 34.0], [77.0, 35.0], [76.0, 35.0], [76.0, 34.0]]]},
        assets={
            "visual": AssetInfo(name="visual", url="http://example.com/visual.tif", size_bytes=100 * 1024 * 1024),
            "red": AssetInfo(name="red", band="B04", url="http://example.com/red.tif", size_bytes=100 * 1024 * 1024),
            "green": AssetInfo(name="green", band="B03", url="http://example.com/green.tif", size_bytes=100 * 1024 * 1024),
            "blue": AssetInfo(name="blue", band="B02", url="http://example.com/blue.tif", size_bytes=100 * 1024 * 1024),
            "nir": AssetInfo(name="nir", band="B08", url="http://example.com/nir.tif", size_bytes=100 * 1024 * 1024),
        }
    )

    result = StorageEstimator.estimate([scene, scene], ["visual", "red", "nir"])
    # The job stages two unique spectral assets and skips the ancillary RGB composite.
    assert result.scene_count == 1
    assert result.asset_count == 2
    assert result.raw_bytes == 200 * 1024 * 1024
    assert result.formatted_raw == "200.00 MB"
    assert result.processing_bytes == int(result.raw_bytes * 0.15)
    assert result.output_bytes == int(result.raw_bytes * 0.25)
    assert result.safety_bytes >= 2 * 1024 * 1024 * 1024
    assert result.required_bytes > result.raw_bytes
    assert result.available_bytes > 0
