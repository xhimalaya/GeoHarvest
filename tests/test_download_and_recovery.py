import asyncio
import hashlib
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import pytest
from backend.core.download.engine import DownloadEngine
from backend.core.recovery.manager import CrashRecoveryManager
from backend.app.models.models import Job, Download, JobStatus, DownloadStatus
from backend.app.dependencies.database import SessionLocal


# Test HTTP Server supporting Range requests
TEST_FILE_CONTENT = b"GeoHarvest_Chunk_0123456789" * 1000  # 28,000 bytes
TEST_SHA256 = hashlib.sha256(TEST_FILE_CONTENT).hexdigest()


class RangeTestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = TEST_FILE_CONTENT
        total_len = len(content)

        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else total_len - 1

            self.send_response(206)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Range", f"bytes {start}-{end}/{total_len}")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(content[start:end + 1])
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(total_len))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(content)

    def log_message(self, format, *args):
        pass  # Suppress server logs in test output


@pytest.fixture(scope="module")
def local_range_server():
    server = HTTPServer(("127.0.0.1", 19876), RangeTestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:19876/test_scene.tif"
    server.shutdown()


@pytest.mark.asyncio
async def test_full_download(tmp_path, local_range_server):
    dest = tmp_path / "scene_full.tif"
    engine = DownloadEngine(chunk_size=4096)
    
    success = await engine.download_file(
        url=local_range_server,
        destination_path=dest,
        expected_size=len(TEST_FILE_CONTENT),
        expected_checksum=TEST_SHA256
    )

    assert success is True
    assert dest.exists()
    assert not Path(str(dest) + ".part").exists()
    assert dest.stat().st_size == len(TEST_FILE_CONTENT)
    assert dest.read_bytes() == TEST_FILE_CONTENT


@pytest.mark.asyncio
async def test_resume_download(tmp_path, local_range_server):
    dest = tmp_path / "scene_resumed.tif"
    part_file = Path(str(dest) + ".part")

    # Simulate existing partial download (first 10,000 bytes)
    partial_bytes = TEST_FILE_CONTENT[:10000]
    part_file.write_bytes(partial_bytes)
    assert part_file.stat().st_size == 10000

    engine = DownloadEngine(chunk_size=4096)
    success = await engine.download_file(
        url=local_range_server,
        destination_path=dest,
        expected_size=len(TEST_FILE_CONTENT),
        expected_checksum=TEST_SHA256
    )

    assert success is True
    assert dest.exists()
    assert not part_file.exists()
    assert dest.stat().st_size == len(TEST_FILE_CONTENT)
    assert dest.read_bytes() == TEST_FILE_CONTENT


def test_crash_recovery(tmp_path):
    dest = tmp_path / "crash_test.tif"
    part_file = Path(str(dest) + ".part")
    part_file.write_bytes(b"A" * 5000)

    import uuid
    uid = uuid.uuid4().hex[:6]
    db = SessionLocal()
    job_id = f"test_crash_job_{uid}"
    dl_id = f"test_crash_dl_{uid}"

    job = Job(id=job_id, type="harvest", status=JobStatus.RUNNING, progress=10.0)
    db.add(job)

    dl = Download(
        id=dl_id,
        job_id=job_id,
        destination=str(dest),
        total_bytes=10000,
        downloaded_bytes=2000,
        status=DownloadStatus.DOWNLOADING
    )
    db.add(dl)
    db.commit()

    # Execute Crash Recovery
    recovered = CrashRecoveryManager.recover_interrupted_jobs()
    assert recovered >= 1

    # Check that job and download records were updated properly
    db.expire_all()
    updated_job = db.query(Job).filter(Job.id == job_id).first()
    updated_dl = db.query(Download).filter(Download.id == dl_id).first()

    assert updated_job.status in [JobStatus.QUEUED, JobStatus.RUNNING]
    # Downloaded bytes was corrected to match the actual 5000 bytes found in the .part file
    assert updated_dl.downloaded_bytes == 5000

    # Cleanup
    db.delete(updated_dl)
    db.delete(updated_job)
    db.commit()
    db.close()


@pytest.mark.asyncio
async def test_s3_download_fallback(tmp_path, monkeypatch):
    """Verify s3:// URL gracefully falls back to public mirror if S3 credentials not present."""
    from backend.app.dependencies.config import settings
    monkeypatch.setattr(settings, "cdse_s3_access_key", None)
    monkeypatch.setattr(settings, "cdse_s3_secret_key", None)

    engine = DownloadEngine()
    dest = tmp_path / "fallback.tif"

    # Simulated s3 URL without AWS keys
    s3_url = "s3://eodata/Sentinel-2/MSI/L2A/2024/06/15/S2A_MSIL2A_20240615T053651_N0510_R005_T43SGT_20240615T103157.SAFE/GRANULE/L2A_T43SGT_A046906_20240615T054139/IMG_DATA/R10m/T43SGT_20240615T053651_B02_10m.jp2"

    # Mock download_file for the fallback HTTP URL so we don't rely on live internet
    async def mock_download_file(url, destination_path, **kwargs):
        assert "sentinel-cogs" in url
        destination_path.write_bytes(b"MOCK_FALLBACK_DATA")
        return True

    monkeypatch.setattr(engine, "download_file", mock_download_file)

    res = await engine._download_s3_file(
        url=s3_url,
        destination_path=dest
    )
    assert res is True



def test_build_s3_client_uses_cdse_compatible_config(monkeypatch):
    import boto3
    from backend.core.download.engine import build_s3_client

    captured = {}

    def fake_boto3_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(boto3, "client", fake_boto3_client)

    build_s3_client(
        endpoint=" https://eodata.dataspace.copernicus.eu/ ",
        access_key=" MY_ACCESS_KEY ",
        secret_key=" MY_SECRET_KEY\n",
    )

    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == "https://eodata.dataspace.copernicus.eu"
    assert captured["aws_access_key_id"] == "MY_ACCESS_KEY"
    assert captured["aws_secret_access_key"] == "MY_SECRET_KEY"
    assert captured["region_name"] == "default"
    cfg = captured["config"]
    assert cfg.signature_version == "s3v4"
    assert cfg.s3 == {"addressing_style": "path"}
    assert cfg.request_checksum_calculation == "when_required"
    assert cfg.response_checksum_validation == "when_required"


@pytest.mark.asyncio
async def test_s3_signature_error_fails_fast_and_falls_back_to_sentinel2_cog(tmp_path, monkeypatch):
    from pathlib import Path
    from botocore.exceptions import ClientError
    from backend.app.dependencies.config import settings
    from backend.core.download.engine import DownloadEngine

    monkeypatch.setattr(settings, "cdse_s3_access_key", "BAD_KEY")
    monkeypatch.setattr(settings, "cdse_s3_secret_key", "BAD_SECRET")
    monkeypatch.setattr(settings, "cdse_s3_endpoint", "https://eodata.dataspace.copernicus.eu")

    s3_attempts = 0

    class FakeS3Client:
        def _raise_sig_err(self):
            nonlocal s3_attempts
            s3_attempts += 1
            raise ClientError(
                {
                    "Error": {"Code": "SignatureDoesNotMatch", "Message": "Bad signature"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "GetObject",
            )

        def head_object(self, **kwargs):
            self._raise_sig_err()

        def get_object(self, **kwargs):
            self._raise_sig_err()

    monkeypatch.setattr("backend.core.download.engine.build_s3_client", lambda **kwargs: FakeS3Client())

    engine = DownloadEngine(max_attempts=5, base_backoff_sec=0.01)
    fallback_calls = []

    async def mock_download_file(url, destination_path, expected_size=None, expected_checksum=None, **kwargs):
        fallback_calls.append(
            {
                "url": url,
                "expected_size": expected_size,
                "expected_checksum": expected_checksum,
                "part_exists": Path(str(destination_path) + ".part").exists(),
            }
        )
        destination_path.write_bytes(b"COGDATA")
        return True

    monkeypatch.setattr(engine, "download_file", mock_download_file)

    dest = tmp_path / "B04.jp2"
    stale_part = Path(str(dest) + ".part")
    stale_part.write_bytes(b"stale-jp2-prefix")

    s3_url = (
        "s3://eodata/Sentinel-2/MSI/L2A/2024/06/15/"
        "S2A_MSIL2A_20240615T052651_N0510_R105_T43SFT_20240615T083651.SAFE/"
        "GRANULE/L2A_T43SFT_A046909_20240615T053559/IMG_DATA/R10m/T43SFT_20240615T052651_B04_10m.jp2"
    )
    ok = await engine._download_s3_file(
        s3_url,
        dest,
        expected_size=123456,
        expected_checksum="deadbeef",
    )

    assert ok is True
    assert s3_attempts == 1
    assert len(fallback_calls) == 1
    assert fallback_calls[0]["url"].startswith("https://sentinel-cogs.s3.us-west-2.amazonaws.com/")
    assert fallback_calls[0]["url"].endswith("/B04.tif")
    assert fallback_calls[0]["expected_size"] is None
    assert fallback_calls[0]["expected_checksum"] is None
    assert fallback_calls[0]["part_exists"] is False


@pytest.mark.asyncio
async def test_s3_auth_error_non_sentinel2_fails_without_retrying(tmp_path, monkeypatch):
    from botocore.exceptions import ClientError
    from backend.app.dependencies.config import settings
    from backend.app.models.models import DownloadStatus
    from backend.core.download.engine import DownloadEngine

    monkeypatch.setattr(settings, "cdse_s3_access_key", "BAD_KEY")
    monkeypatch.setattr(settings, "cdse_s3_secret_key", "BAD_SECRET")

    s3_attempts = 0
    captured_keys = []

    class FakeS3Client:
        def head_object(self, **kwargs):
            nonlocal s3_attempts
            s3_attempts += 1
            captured_keys.append(kwargs["Key"])
            raise ClientError(
                {
                    "Error": {"Code": "InvalidAccessKeyId", "Message": "Invalid key"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "HeadObject",
            )

    monkeypatch.setattr("backend.core.download.engine.build_s3_client", lambda **kwargs: FakeS3Client())

    events = []
    engine = DownloadEngine(max_attempts=5, base_backoff_sec=0.01)
    dest = tmp_path / "sar.tiff"

    ok = await engine._download_s3_file(
        "s3://eodata//Sentinel-1/SAR/SLC/2024/06/sample.tiff",
        dest,
        progress_callback=lambda b, t, s, st, msg: events.append((st, msg)),
    )

    assert ok is False
    assert s3_attempts == 1
    assert captured_keys == ["Sentinel-1/SAR/SLC/2024/06/sample.tiff"]
    assert events[-1][0] == DownloadStatus.FAILED
    assert "InvalidAccessKeyId" in events[-1][1]
    assert "Credentials settings" in events[-1][1]


@pytest.mark.asyncio
async def test_s2c_signature_error_falls_back_to_sentinel2_cog(tmp_path, monkeypatch):
    from botocore.exceptions import ClientError
    from backend.app.dependencies.config import settings
    from backend.core.download.engine import DownloadEngine, resolve_sentinel2_cog_fallback_url
    from backend.core.sources.datasets.raster import RasterDatasetAdapter

    s2c_url = (
        "s3://eodata/Sentinel-2/MSI/L2A/2026/01/13/"
        "S2C_MSIL2A_20260113T053201_N0511_R105_T44SKE_20260113T090418.SAFE/"
        "GRANULE/L2A_T44SKE_A007082_20260113T053204/IMG_DATA/R10m/T44SKE_20260113T053201_B02_10m.jp2"
    )
    resolved = resolve_sentinel2_cog_fallback_url(s2c_url)
    assert resolved == (
        "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
        "sentinel-s2-l2a-cogs/44/S/KE/2026/1/S2C_44SKE_20260113_0_L2A/B02.tif"
    )

    monkeypatch.setattr(settings, "cdse_s3_access_key", "BAD_KEY")
    monkeypatch.setattr(settings, "cdse_s3_secret_key", "BAD_SECRET")

    class FakeS3Client:
        def head_object(self, **kwargs):
            raise ClientError(
                {
                    "Error": {"Code": "SignatureDoesNotMatch", "Message": "Bad signature"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "HeadObject",
            )

        def get_object(self, **kwargs):
            return self.head_object(**kwargs)

    monkeypatch.setattr("backend.core.download.engine.build_s3_client", lambda **kwargs: FakeS3Client())

    engine = DownloadEngine(max_attempts=5, base_backoff_sec=0.01)
    fallback_urls = []

    async def mock_download_file(url, destination_path, **kwargs):
        fallback_urls.append(url)
        destination_path.write_bytes(b"S2CCOG")
        return True

    monkeypatch.setattr(engine, "download_file", mock_download_file)

    ok = await engine._download_s3_file(s2c_url, tmp_path / "B02.jp2")
    assert ok is True
    assert fallback_urls == [resolved]

    adapter = RasterDatasetAdapter()
    item = adapter.adapt(
        {
            "id": "S2C_MSIL2A_20260113T053201_N0511_R105_T44SKE_20260113T090418",
            "collection": "sentinel-2-l2a",
            "properties": {"datetime": "2026-01-13T05:32:01Z"},
            "assets": {"B02_10m": {"href": s2c_url, "type": "image/jp2"}},
        },
        provider_id="copernicus-dataspace",
    )
    assert item.thumbnail_url == (
        "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
        "sentinel-s2-l2a-cogs/44/S/KE/2026/1/S2C_44SKE_20260113_0_L2A/thumbnail.jpg"
    )



def test_resolve_and_aggregate_completed_byte_mismatch():
    from types import SimpleNamespace
    from backend.app.models.models import DownloadStatus
    from backend.core.jobs.engine import resolve_download_byte_progress, compute_job_progress_stats

    # Case 1: COMPLETED download with smaller downloaded_bytes from stale session cache
    dn1, tot1, pct1 = resolve_download_byte_progress(DownloadStatus.COMPLETED, 112_165_997, 186_819_679)
    assert (dn1, tot1, pct1) == (186_819_679, 186_819_679, 100.0)

    # Case 2: COMPLETED download whose actual size exceeded initial STAC estimate
    dn2, tot2, pct2 = resolve_download_byte_progress(DownloadStatus.COMPLETED, 3_733_518, 621_324)
    assert (dn2, tot2, pct2) == (3_733_518, 3_733_518, 100.0)

    # Case 3: In-progress download with overshoot is clamped to 100.0
    dn3, tot3, pct3 = resolve_download_byte_progress(DownloadStatus.DOWNLOADING, 150, 100)
    assert (dn3, tot3, pct3) == (100, 100, 100.0)

    rows = [
        SimpleNamespace(status=DownloadStatus.COMPLETED, downloaded_bytes=60, total_bytes=100),
        SimpleNamespace(status=DownloadStatus.DOWNLOADING, downloaded_bytes=50, total_bytes=100),
    ]
    comp, tot, tot_b, dn_b, overall_pct = compute_job_progress_stats(rows)
    assert comp == 1
    assert tot == 2
    assert tot_b == 200
    assert dn_b == 150
    assert overall_pct == 75.0


@pytest.mark.asyncio
async def test_completed_download_updates_total_bytes_and_api_returns_100_percent(client, db_session, tmp_path, monkeypatch):
    import datetime
    import uuid
    from backend.app.models.models import Job, Download, Asset, Dataset, JobStatus, DownloadStatus
    from backend.core.jobs.engine import JobEngine

    suffix = uuid.uuid4().hex[:8]
    job_id = f"job_test_{suffix}"
    scene_id = f"scene_test_{suffix}"
    asset_id = f"{scene_id}_green"
    dl_new_id = f"dl_new_{suffix}"
    dl_old_id = f"dl_old_{suffix}"
    dest_file = tmp_path / "B03.jp2"

    try:
        ds = Dataset(
            id=scene_id,
            provider_id="copernicus-dataspace",
            collection="sentinel-2-l2a",
            dataset_id=scene_id,
            title=scene_id,
            acquisition_date=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )
        asset = Asset(
            id=asset_id,
            dataset_id=scene_id,
            asset_name="green",
            url="https://example.com/B03.tif",
            size=100,
            band="B03",
            status="pending",
        )
        job = Job(
            id=job_id,
            type="harvest",
            status=JobStatus.QUEUED,
            progress=0.0,
            job_metadata={
                "name": "byte-sync-test",
                "scenes": [
                    {
                        "id": scene_id,
                        "collection": "sentinel-2-l2a",
                        "assets": {"green": {"url": "https://example.com/B03.tif"}},
                    }
                ],
            },
        )
        dl_new = Download(
            id=dl_new_id,
            job_id=job_id,
            asset_id=asset_id,
            destination=str(dest_file),
            total_bytes=100,  # Stale initial STAC size
            downloaded_bytes=0,
            status=DownloadStatus.PENDING,
        )
        dl_old = Download(
            id=dl_old_id,
            job_id=job_id,
            asset_id=asset_id,
            destination=str(tmp_path / "legacy.jp2"),
            total_bytes=100,
            downloaded_bytes=60,  # Pre-existing legacy mismatched COMPLETED row
            status=DownloadStatus.COMPLETED,
        )
        db_session.add_all([ds, asset, job, dl_new, dl_old])
        db_session.commit()

        engine = JobEngine(max_workers=1)

        async def fake_download_file(url, destination_path, progress_callback=None, **kwargs):
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(b"X" * 250)
            if progress_callback:
                progress_callback(250, 250, 0.0, DownloadStatus.COMPLETED, None)
            return True

        monkeypatch.setattr(engine.download_engine, "download_file", fake_download_file)
        monkeypatch.setattr("backend.core.jobs.engine.catalog_engine.add_scene_to_catalog", lambda **kwargs: None)

        await engine._run_job(job_id)

        db_session.expire_all()
        refreshed_new = db_session.query(Download).filter(Download.id == dl_new_id).first()
        assert refreshed_new.status == DownloadStatus.COMPLETED
        assert refreshed_new.total_bytes == 250
        assert refreshed_new.downloaded_bytes == 250

        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["progress"] == 100.0
        by_id = {d["id"]: d for d in payload["downloads"]}
        assert by_id[dl_new_id]["progress_percentage"] == 100.0
        assert by_id[dl_new_id]["downloaded_bytes"] == 250
        assert by_id[dl_new_id]["total_bytes"] == 250
        assert by_id[dl_old_id]["progress_percentage"] == 100.0
        assert by_id[dl_old_id]["downloaded_bytes"] == 100
        assert by_id[dl_old_id]["total_bytes"] == 100
    finally:
        db_session.expire_all()
        db_session.query(Download).filter(Download.job_id == job_id).delete()
        db_session.query(Job).filter(Job.id == job_id).delete()
        db_session.query(Asset).filter(Asset.id == asset_id).delete()
        db_session.query(Dataset).filter(Dataset.id == scene_id).delete()
        db_session.commit()
