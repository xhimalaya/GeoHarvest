import time
import logging
import sqlite3
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.db")

DATABASE_URL = settings.get_database_url

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30.0},
        echo=False
    )

    # Enable SQLite WAL mode, foreign keys, and busy timeout on every connection
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def wait_for_db(max_retries: int = 15, retry_interval: float = 2.0):
    """Wait for database server to become reachable before initializing tables."""
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            if attempt < max_retries:
                logger.info(f"Waiting for database connection (attempt {attempt}/{max_retries})...")
                time.sleep(retry_interval)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise

def init_db():
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    # Seed default providers if not existing
    from backend.app.models.models import Provider
    db = SessionLocal()
    try:
        p1 = db.query(Provider).filter(Provider.provider_id == "aws-earthsearch").first()
        if not p1:
            db.add(Provider(
                id="prov_aws",
                provider_id="aws-earthsearch",
                name="AWS Earth Search (Element 84)",
                type="stac",
                enabled=True,
                authenticated=True
            ))
        p2 = db.query(Provider).filter(Provider.provider_id == "planetary-computer").first()
        if not p2:
            db.add(Provider(
                id="prov_pc",
                provider_id="planetary-computer",
                name="Microsoft Planetary Computer",
                type="stac",
                enabled=True,
                authenticated=True
            ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
