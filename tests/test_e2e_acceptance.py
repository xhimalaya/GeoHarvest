import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.models import JobStatus, DownloadStatus


def test_full_acceptance_workflow():
    client = TestClient(app)

    # 1. Health check
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"

    # 2. Load Ladakh AOI sample
    ladakh_res = client.get("/api/aoi/samples/ladakh")
    assert ladakh_res.status_code == 200
    ladakh_data = ladakh_res.json()
    assert ladakh_data["analysis"]["valid"] is True
    aoi_geom = ladakh_data["analysis"]["normalized_geometry"]

    # 3. Discover Sentinel-2 scenes
    search_payload = {
        "provider_id": "aws-earthsearch",
        "collection": "sentinel-2-l2a",
        "start_date": "2024-06-01",
        "end_date": "2024-06-15",
        "aoi": aoi_geom,
        "max_cloud_cover": 30.0,
        "limit": 2
    }
    search_res = client.post("/api/search", json=search_payload)
    assert search_res.status_code == 200
    scenes = search_res.json()["items"]
    assert len(scenes) > 0

    # 4. Storage Estimator
    estimate_payload = {
        "selected_scenes": scenes,
        "selected_bands": ["visual", "red", "nir"]
    }
    est_res = client.post("/api/storage/estimate", json=estimate_payload)
    assert est_res.status_code == 200
    estimate = est_res.json()
    assert estimate["scene_count"] == len(scenes)
    assert estimate["raw_bytes"] > 0
    assert estimate["required_bytes"] > estimate["raw_bytes"]

    # 5. Create Persistent Harvest Job
    job_payload = {
        "name": "E2E Acceptance Test Job",
        "scenes": [scenes[0]],
        "bands": ["thumbnail"],  # Thumbnail is small (~50KB) for instant verification
        "aoi": aoi_geom
    }
    job_res = client.post("/api/jobs", json=job_payload)
    assert job_res.status_code == 200
    job = job_res.json()
    assert job["id"].startswith("job_")
    assert job["status"] in [JobStatus.QUEUED.value, JobStatus.RUNNING.value]

    # 6. Retrieve Job Detail
    detail_res = client.get(f"/api/jobs/{job['id']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == job["id"]
    assert len(detail["downloads"]) > 0

    # 7. Pause & Resume
    pause_res = client.post(f"/api/jobs/{job['id']}/pause")
    # Might be running or completed, pause returns 200 if paused
    if pause_res.status_code == 200:
        resume_res = client.post(f"/api/jobs/{job['id']}/resume")
        assert resume_res.status_code == 200
