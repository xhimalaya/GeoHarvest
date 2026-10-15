import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from backend.core.sources.discovery.bhuvan_wcs import BhuvanWcsDiscoveryAdapter
from backend.core.sources.discovery.bhoonidhi import BhoonidhiDiscoveryAdapter
from backend.core.sources.discovery.isro_vedas import IsroVedasDiscoveryAdapter
from backend.core.credentials.manager import CredentialManager
from backend.core.download.engine import DownloadEngine, DownloadStatus
from backend.core.jobs.engine import JobEngine
from backend.app.dependencies.database import SessionLocal
from backend.app.models.models import Job, Dataset, Asset, Download, JobStatus
from backend.app.schemas.schemas import SearchResultItem, AssetInfo


@pytest.mark.asyncio
async def test_bhuvan_wcs_discovery_and_url_generation():
    """Verify Bhuvan WCS adapter builds valid OGC WCS 1.0.0 GetCoverage URLs for CartoDEM."""
    adapter = BhuvanWcsDiscoveryAdapter()
    results = await adapter.discover(
        aoi=None,
        start_date="2024-01-01",
        end_date="2024-01-02",
        filters={"collection": "bhuvan-cartodem-30m", "bbox": [77.0, 34.0, 78.0, 35.0]}
    )
    assert len(results) == 1
    item = results[0]
    assert "BHUVAN_CARTODEM" in item["id"]
    assert "cartodem" in item["assets"]

    href = item["assets"]["cartodem"]["href"]
    assert "SERVICE=WCS" in href
    assert "VERSION=1.0.0" in href
    assert "REQUEST=GetCoverage" in href
    assert "COVERAGE=bhuvan:cartodem_v3" in href
    assert "CRS=EPSG:4326" in href
    assert "FORMAT=GeoTIFF" in href
    assert "77.000000,34.000000,78.000000,35.000000" in href


@pytest.mark.asyncio
async def test_bhoonidhi_stac_discovery():
    """Verify Bhoonidhi STAC adapter formats Indian constellation items and assets."""
    adapter = BhoonidhiDiscoveryAdapter()
    results = await adapter.discover(
        aoi=None,
        start_date="2024-06-01",
        end_date="2024-06-30",
        filters={"collection": "isro-resourcesat-2a", "bbox": [76.5, 33.5, 77.5, 34.5]}
    )
    assert len(results) >= 1
    item = results[0]
    assert "RESOURCESAT" in item["id"] or "AWIFS" in item["id"]
    assert "awifs_b3" in item["assets"]
    assert item["assets"]["awifs_b3"]["type"] == "image/tiff"


@pytest.mark.asyncio
async def test_isro_vedas_unified_routing():
    """Verify unified ISRO adapter routes Bhuvan WCS vs Bhoonidhi STAC collections."""
    adapter = IsroVedasDiscoveryAdapter()

    # 1. Bhuvan CartoDEM route
    dem_results = await adapter.discover(
        aoi=None,
        start_date="2024-01-01",
        end_date="2024-01-02",
        filters={"collection": "bhuvan-cartodem-30m"}
    )
    assert len(dem_results) == 1
    assert "BHUVAN" in dem_results[0]["id"]
    assert "cartodem" in dem_results[0]["assets"]

    # 2. Bhoonidhi Resourcesat route
    sat_results = await adapter.discover(
        aoi=None,
        start_date="2024-06-01",
        end_date="2024-06-02",
        filters={"collection": "isro-resourcesat-2a"}
    )
    assert len(sat_results) >= 1
    assert "RESOURCESAT" in sat_results[0]["id"]


@pytest.mark.asyncio
async def test_credential_manager_bhoonidhi_token(monkeypatch):
    """Verify CredentialManager generates authorization headers from token or user login."""
    monkeypatch.setenv("GEOHARVEST_ISRO_API_TOKEN", "test_isro_secret_token_12345")
    cm = CredentialManager()
    headers = await cm.get_bhoonidhi_auth_headers()
    assert headers.get("Authorization") == "Bearer test_isro_secret_token_12345"


@pytest.mark.asyncio
async def test_download_engine_accepts_custom_headers(tmp_path):
    """Verify DownloadEngine injects custom headers into outgoing HTTP stream request."""
    engine = DownloadEngine()
    dest = tmp_path / "test_download.tif"

    captured_headers = {}

    class MockStreamResponse:
        status_code = 200
        headers = {"Content-Length": "10"}
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def aiter_bytes(self, chunk_size=1024):
            yield b"1234567890"

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        def stream(self, method, url, headers=None):
            nonlocal captured_headers
            captured_headers = headers or {}
            return MockStreamResponse()

    with patch("httpx.AsyncClient", MockAsyncClient):
        success = await engine.download_file(
            url="https://bhoonidhi.nrsc.gov.in/api/v1/download?id=123",
            destination_path=dest,
            headers={"Authorization": "Bearer secret_bhoonidhi_jwt"}
        )

    assert success is True
    assert captured_headers.get("Authorization") == "Bearer secret_bhoonidhi_jwt"
    assert dest.exists()
    assert dest.read_bytes() == b"1234567890"


def test_job_engine_preserves_isro_provider_id(tmp_path):
    """Verify JobEngine preserves provider_id for isro-bhuvan-vedas and does not set it to None."""
    db = SessionLocal()
    try:
        engine = JobEngine()
        scene = SearchResultItem(
            id="BHUVAN_CARTODEM_TEST_01",
            collection="bhuvan-cartodem-30m",
            provider_id="isro-bhuvan-vedas",
            title="CartoDEM Scene",
            datetime="2024-01-01T00:00:00Z",
            bbox=[77.0, 34.0, 78.0, 35.0],
            geometry={"type": "Polygon", "coordinates": []},
            assets={
                "cartodem": AssetInfo(
                    name="cartodem",
                    title="CartoDEM GeoTIFF",
                    url="https://bhuvan-app1.nrsc.gov.in/bhuvan/wcs?REQUEST=GetCoverage&COVERAGE=bhuvan:cartodem_v3",
                    size_bytes=1024,
                    mime_type="image/tiff",
                    band="DEM"
                )
            }
        )

        job = engine.create_harvest_job(
            name="Test Bhuvan Harvest",
            scenes=[scene],
            selected_bands=["cartodem"],
            db=db
        )

        dataset_rec = db.query(Dataset).filter(Dataset.id == "BHUVAN_CARTODEM_TEST_01").first()
        assert dataset_rec is not None
        assert dataset_rec.provider_id == "isro-bhuvan-vedas"

        # Verify downloads were created for the cartodem band
        downloads = db.query(Download).filter(Download.job_id == job.id).all()
        assert len(downloads) == 1
        assert "bhuvan" in downloads[0].asset_id.lower() or "cartodem" in downloads[0].asset_id.lower()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_full_bhuvan_harvest_job_workflow(tmp_path):
    """Verify complete end-to-end harvest workflow for Bhuvan CartoDEM."""
    db = SessionLocal()
    try:
        engine = JobEngine()
        scene = SearchResultItem(
            id="BHUVAN_CARTODEM_E2E_01",
            collection="bhuvan-cartodem-30m",
            provider_id="isro-bhuvan-vedas",
            title="CartoDEM E2E Scene",
            datetime="2024-01-01T00:00:00Z",
            bbox=[77.0, 34.0, 78.0, 35.0],
            geometry={"type": "Polygon", "coordinates": []},
            assets={
                "cartodem": AssetInfo(
                    name="cartodem",
                    title="CartoDEM GeoTIFF",
                    url="https://bhuvan-app1.nrsc.gov.in/bhuvan/wcs?REQUEST=GetCoverage&COVERAGE=bhuvan:cartodem_v3",
                    size_bytes=2048,
                    mime_type="image/tiff",
                    band="DEM"
                )
            }
        )

        # Mock DownloadEngine.download_file to succeed and produce a valid dummy file
        async def mock_download_file(url, destination_path, **kwargs):
            dest = Path(destination_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"DUMMY_TIFF_BYTES_CONTENT")
            return True

        with patch.object(engine.download_engine, "download_file", side_effect=mock_download_file):
            job = engine.create_harvest_job(
                name="E2E Bhuvan Harvest",
                scenes=[scene],
                selected_bands=["cartodem"],
                db=db
            )

            # Await the created background task
            if job.id in engine._active_tasks:
                await engine._active_tasks[job.id]
            else:
                await engine._run_job(job.id)

        # Refresh database session to observe committed status
        db.expire_all()
        updated_job = db.query(Job).filter(Job.id == job.id).first()
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.progress == 100.0

        dl = db.query(Download).filter(Download.job_id == job.id).first()
        assert dl.status == DownloadStatus.COMPLETED
        assert Path(dl.destination).exists()
    finally:
        db.close()
