import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ai.config import ai_config
from backend.ai.models import ChatRequest
from backend.ai.services.chat_service import ChatService
from backend.ai.services.project_context import build_project_context
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import Base
from backend.app.models.models import Asset, Dataset


def test_project_context_summarizes_catalog_and_saved_aois_without_paths(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        dataset = Dataset(
            id="scene-1",
            collection="sentinel-2-l2a",
            dataset_id="S2A_43SFS_20240602",
            title="Sentinel-2 scene",
            platform="Sentinel-2A",
            sensor="MSI",
            acquisition_date=datetime(2024, 6, 2, tzinfo=timezone.utc),
            cloud_cover=4.5,
            resolution=10,
        )
        db.add(dataset)
        db.flush()
        db.add(
            Asset(
                id="scene-1_B04",
                dataset_id=dataset.id,
                asset_name="B04",
                url="https://example.invalid/secret?token=do-not-include",
                local_path="/private/data/scene-1_B04.tif",
                status="downloaded",
            )
        )
        db.commit()

        aoi_dir = tmp_path / "aois"
        aoi_dir.mkdir()
        (aoi_dir / "aoi_ladakh.geojson").write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Polygon", "coordinates": []},
                            "properties": {"name": "Ladakh study area", "area_km2": 1250.5},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        context = build_project_context(db, aoi_dir)

    assert "1 catalog record(s)" in context
    assert "S2A_43SFS_20240602" in context
    assert 'assets=["B04"]' in context
    assert '"Ladakh study area"' in context
    assert "area_km2=1250.5" in context
    assert "/private/data" not in context
    assert "example.invalid" not in context
    assert "Filesystem existence is not checked." in context


def test_chat_preparation_attaches_local_project_context(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir()
    (aoi_dir / "aoi_ladakh.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": []},
                        "properties": {"name": "Ladakh study area", "area_km2": 1250.5},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(settings, "aois_dir", aoi_dir)
    monkeypatch.setattr(ai_config, "_configs", {})
    monkeypatch.setattr(ai_config, "_active_provider", "gemini")
    service = ChatService(session_factory=session_factory)
    prepared = service.prepare_execution(ChatRequest(provider="gemini", prompt="What data is available?"))

    assert prepared.conversation_id
    assert "GeoHarvest local project context:" in prepared.system_instruction
    assert '"Ladakh study area"' in prepared.system_instruction
    assert "Raster/vector contents and absolute paths are not included." in prepared.system_instruction

    service.delete_conversation(prepared.conversation_id)
