import pytest
from pathlib import Path
from backend.core.credentials.manager import CredentialManager, PLATFORM_SPECS


@pytest.fixture
def temp_credential_manager(tmp_path):
    env_file = tmp_path / ".env"
    return CredentialManager(env_path=env_file)


def test_list_platform_specs():
    specs = PLATFORM_SPECS
    assert len(specs) >= 6
    ids = [s.id for s in specs]
    assert "copernicus-dataspace" in ids
    assert "nasa-earthdata" in ids
    assert "planetary-computer" in ids
    assert "isro-bhuvan-vedas" in ids
    assert "ecmwf-cds" in ids
    assert "commercial-planet-maxar" in ids


def test_save_mask_and_clear_credentials(temp_credential_manager):
    mgr = temp_credential_manager
    # Initially not configured
    status_initial = mgr.get_platform_status("copernicus-dataspace")
    assert status_initial is not None
    assert status_initial.is_configured is False

    # Save credentials
    updated = mgr.save_platform_credentials(
        platform_id="copernicus-dataspace",
        fields={
            "s3_access_key": "AKIAEXAMPLE1234",
            "s3_secret_key": "SUPER_SECRET_KEY_9999",
            "username": "tester@copernicus.eu"
        }
    )
    assert updated.is_configured is True
    # Secret must be masked
    assert "SUPER_SECRET" not in updated.fields["s3_secret_key"]
    assert "••••" in updated.fields["s3_secret_key"]
    assert updated.fields["s3_secret_key"].endswith("9999")
    # Non-secret is plaintext
    assert updated.fields["s3_access_key"] == "AKIAEXAMPLE1234"
    assert updated.fields["username"] == "tester@copernicus.eu"

    # Verify saved in temp .env file
    env_content = mgr.env_path.read_text()
    assert "GEOHARVEST_CDSE_S3_ACCESS_KEY=AKIAEXAMPLE1234" in env_content
    assert "GEOHARVEST_CDSE_S3_SECRET_KEY=SUPER_SECRET_KEY_9999" in env_content

    # Clear credentials
    cleared = mgr.clear_platform_credentials("copernicus-dataspace")
    assert cleared.is_configured is False
    assert cleared.fields["s3_access_key"] == ""
    assert cleared.fields["s3_secret_key"] == ""


def test_api_credentials_endpoints(client, tmp_path, monkeypatch):
    from backend.core.credentials import manager
    temp_env = tmp_path / ".env"
    monkeypatch.setattr(manager.credential_manager, "env_path", temp_env)

    # 1. GET /api/credentials
    resp = client.get("/api/credentials")
    assert resp.status_code == 200
    platforms = resp.json()
    assert len(platforms) >= 6

    # 2. GET /api/credentials/specs
    resp_specs = client.get("/api/credentials/specs")
    assert resp_specs.status_code == 200
    specs = resp_specs.json()
    assert len(specs) >= 6

    # 3. POST /api/credentials
    save_resp = client.post("/api/credentials", json={
        "platform_id": "copernicus-dataspace",
        "fields": {
            "s3_access_key": "DEMO_KEY",
            "s3_secret_key": "DEMO_SECRET_VAL",
            "s3_endpoint": "https://eodata.dataspace.copernicus.eu"
        }
    })
    assert save_resp.status_code == 200
    data = save_resp.json()
    assert data["is_configured"] is True
    assert "••••" in data["fields"]["s3_secret_key"]

    # 4. POST /api/credentials/test
    test_resp = client.post("/api/credentials/test", json={"platform_id": "copernicus-dataspace"})
    assert test_resp.status_code == 200
    test_data = test_resp.json()
    assert "connected" in test_data
    assert "message" in test_data

    # 5. DELETE /api/credentials/copernicus-dataspace
    del_resp = client.delete("/api/credentials/copernicus-dataspace")
    assert del_resp.status_code == 200
    assert del_resp.json()["is_configured"] is False

