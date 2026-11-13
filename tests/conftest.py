import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Default test database to isolated SQLite test DB
os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'data' / 'test_geoharvest.db'}")
os.environ.setdefault("GEOHARVEST_ENVIRONMENT", "test")

from backend.app.dependencies.database import Base, engine, SessionLocal, init_db
from backend.app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    yield


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def fixtures_dir():
    """Returns the absolute Path to the standardized test fixtures directory."""
    return ROOT_DIR / "tests" / "fixtures"


@pytest.fixture
def isolated_test_dir(tmp_path):
    """Provides an isolated temporary directory for test outputs, ensuring automatic cleanup."""
    test_dir = tmp_path / "run"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir
