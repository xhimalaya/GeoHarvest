import sqlite3
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.dependencies.config import settings

DATABASE_URL = f"sqlite:///{settings.db_path}"

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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
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
