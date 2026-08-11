from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


@lru_cache
def get_engine() -> Engine:
    """Engine'i ilk kullanimda olusturur. Import aninda olusturulsaydi,
    DB surucusu kurulu olmayan gelistiricide uygulama hic acilmazdi."""
    return create_engine(settings.database_url, pool_pre_ping=True)


def get_db() -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
