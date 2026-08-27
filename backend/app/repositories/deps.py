"""Repository saglayicilari - implementasyon secimi TEK yerde.

BIRINCIL KAYNAK: PostgreSQL. YEDEK: bellek ici veri.

    1. `DATABASE_URL` tanimli VE baglanti kuruluyorsa -> `sql.py`
    2. Aksi halde                                    -> `in_memory.py`

Ikinci madde bir CALISMA MODU degil, YEDEK plandir: DB tanimli degilse ya da
ayakta degilse sistem hata vermek yerine bellek ici veriyle acilir. Yedege
dusuldugu her seferinde WARNING loglanir ve `/health` `data_source: in-memory`
doner - yani yedekte oldugumuz gizlenmez.

Baglanti bir kez denenir ve sonuc onbeleklenir (`_veritabani_calisiyor`);
her istekte tekrar denemek gereksiz gecikme yaratirdi. `reset_repositories()`
bu karari da sifirlar.

Endpoint, servis, MCP tool ve ajan kodunun hicbiri bu secimi bilmez; hepsi
`base.py` protokollerine konusur.
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
    TradingRepository,
    UserRepository,
)
from app.repositories.in_memory import (
    InMemoryAuditRepository,
    InMemoryChatRepository,
    InMemoryMarketRepository,
    InMemoryPortfolioRepository,
    InMemoryRagRepository,
    InMemoryTradingRepository,
    InMemoryUserRepository,
)

logger = logging.getLogger(__name__)

#: Baglanti denemesi icin ust sinir (saniye). Uygulama acilisi bir DB
#: zaman asimi yuzunden dakikalarca asili kalmamali.
BAGLANTI_TIMEOUT_SANIYE = 5


def _senkron_dsn(url: str) -> str:
    """Baglanti denemesi icin `postgresql://...` bicimine cevirir.

    Deneme SENKRON yapilir: bu fonksiyon repository secilirken (async olmayan
    bir baglamda da) cagrilabilir ve tek seferliktir.
    """
    for onek in ("postgresql+psycopg://", "postgresql+asyncpg://"):
        if url.startswith(onek):
            return url.replace(onek, "postgresql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


@lru_cache
def _veritabani_calisiyor() -> bool:
    """DB tanimli mi ve gercekten baglanilabiliyor mu? (bir kez denenir)"""
    if not settings.database_enabled:
        logger.warning("DATABASE_URL tanimli degil; bellek ici veriye dusuluyor.")
        return False

    try:
        import psycopg

        with psycopg.connect(
            _senkron_dsn(settings.database_url),
            connect_timeout=BAGLANTI_TIMEOUT_SANIYE,
        ) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 - baglanti hatasi uygulamayi dusurmemeli
        logger.warning(
            "veritabanina baglanilamadi; bellek ici veriye dusuluyor",
            extra={"hata": f"{type(exc).__name__}: {exc}"},
        )
        return False

    return True


@lru_cache
def _session_factory():
    from app.db.session import get_session_factory

    return get_session_factory()


@lru_cache
def get_user_repository() -> UserRepository:
    if _veritabani_calisiyor():
        from app.repositories.sql import SqlUserRepository

        return SqlUserRepository(_session_factory())
    return InMemoryUserRepository()


@lru_cache
def get_portfolio_repository() -> PortfolioRepository:
    if _veritabani_calisiyor():
        from app.repositories.sql import SqlPortfolioRepository

        return SqlPortfolioRepository(_session_factory())
    return InMemoryPortfolioRepository()


@lru_cache
def get_market_repository() -> MarketRepository:
    if _veritabani_calisiyor():
        from app.repositories.sql import SqlMarketRepository

        return SqlMarketRepository(_session_factory())
    return InMemoryMarketRepository()


@lru_cache
def get_trading_repository() -> TradingRepository:
    if _veritabani_calisiyor():
        from app.repositories.sql import SqlTradingRepository

        return SqlTradingRepository(_session_factory())
    return InMemoryTradingRepository()


@lru_cache
def get_rag_repository() -> RagRepository:
    if _veritabani_calisiyor():
        from app.repositories.sql import SqlRagRepository

        return SqlRagRepository(_session_factory())
    return InMemoryRagRepository()


@lru_cache
def get_chat_repository() -> ChatRepository:
    if _veritabani_calisiyor():
        from app.repositories.sql import SqlChatRepository

        return SqlChatRepository(_session_factory())
    return InMemoryChatRepository()


@lru_cache
def get_audit_repository() -> AuditRepository:
    if _veritabani_calisiyor():
        from app.repositories.sql import SqlAuditRepository

        return SqlAuditRepository(_session_factory())
    return InMemoryAuditRepository()


def reset_repositories() -> None:
    """Onbellekleri temizler.

    Testler ortam degiskenlerini degistirdikten sonra (orn. DATABASE_URL) bu
    fonksiyonu cagirir; aksi halde ilk secim tum test oturumu boyunca yapisir.
    """
    for provider in (
        _veritabani_calisiyor,
        _session_factory,
        get_user_repository,
        get_portfolio_repository,
        get_market_repository,
        get_trading_repository,
        get_rag_repository,
        get_chat_repository,
        get_audit_repository,
    ):
        provider.cache_clear()


def describe_backend() -> str:
    """Log ve `/health` icin: hangi veri kaynagi bagli?"""
    return "postgresql" if _veritabani_calisiyor() else "in-memory"
