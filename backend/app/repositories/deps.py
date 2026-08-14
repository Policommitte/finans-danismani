"""Repository saglayicilari - implementasyon secimi TEK yerde.

`settings.database_url` doluysa SQL implementasyonlari, bos ise bellek ici
implementasyonlar kullanilir. Endpoint, servis, MCP tool ve ajan kodunun hicbiri
bu secimi bilmez; hepsi `base.py` protokollerine konusur.

Ornekler tekildir (`lru_cache`): bellek ici sohbet deposu istekler arasinda
korunmali, SQL tarafinda ise oturum fabrikasi tekrar tekrar kurulmamalidir.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings
from app.repositories.base import (
    AuditRepository,
    ChatRepository,
    MarketRepository,
    PortfolioRepository,
    RagRepository,
    UserRepository,
)
from app.repositories.in_memory import (
    InMemoryAuditRepository,
    InMemoryChatRepository,
    InMemoryMarketRepository,
    InMemoryPortfolioRepository,
    InMemoryRagRepository,
    InMemoryUserRepository,
)

logger = logging.getLogger(__name__)


@lru_cache
def _session_factory():
    from app.db.session import get_session_factory

    return get_session_factory()


@lru_cache
def get_user_repository() -> UserRepository:
    if settings.database_enabled:
        from app.repositories.sql import SqlUserRepository

        return SqlUserRepository(_session_factory())
    return InMemoryUserRepository()


@lru_cache
def get_portfolio_repository() -> PortfolioRepository:
    if settings.database_enabled:
        from app.repositories.sql import SqlPortfolioRepository

        return SqlPortfolioRepository(_session_factory())
    return InMemoryPortfolioRepository()


@lru_cache
def get_market_repository() -> MarketRepository:
    if settings.database_enabled:
        from app.repositories.sql import SqlMarketRepository

        return SqlMarketRepository(_session_factory())
    return InMemoryMarketRepository()


@lru_cache
def get_rag_repository() -> RagRepository:
    if settings.database_enabled:
        from app.repositories.sql import SqlRagRepository

        return SqlRagRepository(_session_factory())
    return InMemoryRagRepository()


@lru_cache
def get_chat_repository() -> ChatRepository:
    if settings.database_enabled:
        from app.repositories.sql import SqlChatRepository

        return SqlChatRepository(_session_factory())
    return InMemoryChatRepository()


@lru_cache
def get_audit_repository() -> AuditRepository:
    if settings.database_enabled:
        from app.repositories.sql import SqlAuditRepository

        return SqlAuditRepository(_session_factory())
    return InMemoryAuditRepository()


def reset_repositories() -> None:
    """Onbellekleri temizler.

    Testler ortam degiskenlerini degistirdikten sonra (orn. DATABASE_URL) bu
    fonksiyonu cagirir; aksi halde ilk secim tum test oturumu boyunca yapisir.
    """
    for provider in (
        _session_factory,
        get_user_repository,
        get_portfolio_repository,
        get_market_repository,
        get_rag_repository,
        get_chat_repository,
        get_audit_repository,
    ):
        provider.cache_clear()


def describe_backend() -> str:
    """Log ve `/health` icin: hangi veri kaynagi bagli?"""
    return "postgresql" if settings.database_enabled else "in-memory"
