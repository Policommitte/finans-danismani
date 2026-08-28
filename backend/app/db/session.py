"""Asenkron DB oturum yonetimi (SQLAlchemy 2.x + psycopg3).

Engine ILK KULLANIMDA olusturulur (`lru_cache`), import aninda degil: DB
surucusu kurulu olmayan ya da DATABASE_URL tanimlamamis bir gelistiricide
uygulama yine de acilir. `settings.database_url` bos oldugunda bu modulun
hicbir fonksiyonu cagrilmaz - repository katmani bellek ici veriye duser
(bkz. `app/repositories/deps.py`).

Neden async: FastAPI endpoint'leri ve MCP tool'lari async; senkron bir surucu
kullanilirsa her DB cagrisi olay dongusunu bloklar ve SSE akisi tokenlar
arasinda takilir.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

logger = logging.getLogger(__name__)


def _async_url(url: str) -> str:
    """DATABASE_URL'i asenkron surucuye cevirir.

    `.env` dosyalarinda yaygin olan senkron yazimlari sessizce duzeltiriz;
    aksi halde "surucu async degil" hatasi kurulum sirasinda saatler yakar.
    """
    if url.startswith("postgresql+psycopg://") or url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


@lru_cache
def get_engine() -> AsyncEngine:
    """Uygulama genelinde TEK engine (havuz burada tutulur)."""
    if not settings.database_enabled:
        raise RuntimeError(
            "DATABASE_URL tanimli degil. DB'siz calisiliyorsa repository "
            "katmani bellek ici veriyi kullanmalidir; bu fonksiyon cagrilmamali."
        )

    url = _async_url(settings.database_url)
    logger.info("db engine olusturuluyor", extra={"driver": url.split("://", 1)[0]})
    return create_async_engine(
        url,
        # Havuz siniri ACIKCA verilir - gerekcesi config.py'de.
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
        echo=settings.db_echo,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI `Depends` icin oturum uretici."""
    async with get_session_factory()() as session:
        yield session


async def ping() -> bool:
    """`/health/db` icin basit baglanti kontrolu."""
    from sqlalchemy import text

    async with get_session_factory()() as session:
        await session.execute(text("SELECT 1"))
    return True


async def dispose_engine() -> None:
    """Uygulama kapanirken havuzu kapatir (lifespan)."""
    if not settings.database_enabled:
        return
    engine = get_engine()
    await engine.dispose()
