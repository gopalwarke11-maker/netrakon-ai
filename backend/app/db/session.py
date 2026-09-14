"""SQLAlchemy engine and FastAPI session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True) if settings.database_url else None
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield one transactional SQLAlchemy session per request."""
    if engine is None:
        raise RuntimeError(
            "DATABASE_URL is required. Set it to a PostgreSQL SQLAlchemy URL before starting NETRAKON AI."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
