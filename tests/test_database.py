from sqlalchemy import text
from backend.app.dependencies.database import engine, SessionLocal
from backend.app.models.models import Job, JobStatus


def test_database_connection():
    with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            result = conn.execute(text("PRAGMA journal_mode;")).scalar()
            assert str(result).lower() == "wal"
            fk = conn.execute(text("PRAGMA foreign_keys;")).scalar()
            assert fk == 1
        elif engine.dialect.name == "postgresql":
            result = conn.execute(text("SELECT 1;")).scalar()
            assert result == 1


def test_create_and_query_job(db_session):
    job = Job(
        id="test_job_1",
        type="harvest",
        status=JobStatus.PENDING,
        progress=0.0
    )
    db_session.add(job)
    db_session.commit()

    queried = db_session.query(Job).filter(Job.id == "test_job_1").first()
    assert queried is not None
    assert queried.status == JobStatus.PENDING
    assert queried.type == "harvest"

    # Cleanup
    db_session.delete(queried)
    db_session.commit()
