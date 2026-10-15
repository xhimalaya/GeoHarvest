import pytest
from backend.core.sources.registry import source_registry
from backend.core.sources.base import Source, Capabilities
from backend.core.sources.connectors.local import LocalFileConnector


def test_list_sources():
    sources = source_registry.list_sources()
    assert len(sources) >= 3
    source_ids = [s.source_id for s in sources]
    assert "aws-earthsearch" in source_ids
    assert "planetary-computer" in source_ids
    assert "local-filesystem" in source_ids


@pytest.mark.asyncio
async def test_local_connector_health(tmp_path):
    conn = LocalFileConnector(tmp_path)
    res = await conn.test_connection()
    assert res.success is True
    assert res.latency_ms >= 0.0
    assert "accessible" in res.message


@pytest.mark.asyncio
async def test_aws_connector_health():
    source = source_registry.get("aws-earthsearch")
    assert source is not None
    res = await source.test_connection()
    assert res.success is True
    assert res.latency_ms > 0.0
    assert "200" in res.message or "HTTP" in res.message
