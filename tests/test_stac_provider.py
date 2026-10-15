import pytest
from backend.core.discovery.manager import DiscoveryManager
from backend.app.schemas.schemas import SearchResultItem


@pytest.mark.asyncio
async def test_stac_search_integration():
    mgr = DiscoveryManager()
    # Search AWS Earth Search STAC for a small bounding box in Ladakh
    # Leh / Ladakh area roughly [77.5, 34.1, 77.6, 34.2]
    results = await mgr.search(
        provider_id="aws-earthsearch",
        collection="sentinel-2-l2a",
        start_date="2024-06-01",
        end_date="2024-06-15",
        bbox=[77.5, 34.1, 77.6, 34.2],
        max_cloud_cover=50.0,
        limit=2
    )

    # May find 1 or 2 scenes
    assert isinstance(results, list)
    if results:
        scene = results[0]
        assert isinstance(scene, SearchResultItem)
        assert scene.collection in ["sentinel-2-l2a", "sentinel-2-c1-l2a"]
        assert "visual" in scene.assets or "red" in scene.assets
        assert len(scene.bbox) == 4
