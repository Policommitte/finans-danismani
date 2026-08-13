"""Saglik uclari - kimlik dogrulama GEREKTIRMEZ (izleme araclari icin)."""

import logging

from fastapi import APIRouter

from app.config import settings
from app.repositories.deps import describe_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Uygulama ayakta mi")
async def health() -> dict[str, str]:
    """Uygulamanin ayakta oldugunu ve hangi veri kaynagina bagli oldugunu doner."""
    return {"status": "ok", "data_source": describe_backend()}


@router.get("/health/db", summary="Veritabani baglantisi calisiyor mu")
async def health_db() -> dict[str, str]:
    """DB baglantisini dener.

    DATABASE_URL tanimli degilse bu bir HATA DEGILDIR: sistem bellek ici veriyle
    calisiyordur ve `status="disabled"` doner. Boylece izleme araci "DB yok"
    ile "DB var ama erisilemiyor" durumlarini ayirt edebilir.
    """
    if not settings.database_enabled:
        return {"status": "disabled", "detail": "DATABASE_URL tanimli degil, bellek ici veri."}

    from app.db.session import ping

    try:
        await ping()
    except Exception:  # noqa: BLE001 - saglik ucu 500 yerine durum bildirmeli
        logger.exception("veritabani saglik kontrolu basarisiz")
        return {"status": "error", "detail": "Veritabanina baglanilamadi."}

    return {"status": "ok", "database": "reachable"}
