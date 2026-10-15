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

