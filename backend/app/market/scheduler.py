"""Periyodik fiyat guncelleme gorevi (mimari v4 bolum 8).

Bu katman ISTEK AKISINDAN BAGIMSIZDIR: ayri bir asyncio gorevi olarak
`main.py` lifespan'inde baslar. Sohbet veya dashboard istegi gelmese de
fiyatlar ilerler; gelen istek ise fiyat uretmez, yalnizca okur.

Gorev HICBIR ZAMAN uygulamayi dusurmez: bir tick hata verirse loglanir ve
dongu devam eder.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.market.provider import MarketDataProvider, build_provider
from app.repositories.deps import get_market_repository

logger = logging.getLogger(__name__)


async def price_tick(provider: MarketDataProvider, write_history: bool) -> int:
    """Tek bir guncelleme adimi. Test edilebilir olmasi icin ayri fonksiyon."""
    repository = get_market_repository()
    assets = await repository.get_prices_for_simulation()
    if not assets:
        return 0

    updates = await provider.next_prices(assets)

    # Saglayici yedege dusmus olabilir (kota/ag hatasi); bu durumda kaynak
    # "api" DEGIL "simulated"dir. `son_kaynak` yoksa saglayici adi kullanilir.
    kaynak = getattr(provider, "son_kaynak", provider.name)

    return await repository.apply_price_updates(updates, write_history=write_history, source=kaynak)


async def run_price_scheduler(provider: MarketDataProvider | None = None) -> None:
    """Sonsuz dongu - `asyncio.create_task` ile baslatilir, iptal edilerek durur.

    `price_history` her tick'te DEGIL, N tick'te bir yazilir: dakikada bir satir
    x 17 varlik x gunler = gereksiz sisme. Grafikler icin bu cozunurluk yeterli.
    """
    provider = provider or build_provider()
    tick = 0

    logger.info(
        "fiyat gorevi basladi",
        extra={"provider": provider.name, "period_s": settings.price_tick_seconds},
    )

    while True:
        try:
            tick += 1
            gecmis_yaz = tick % max(settings.price_history_every_n_ticks, 1) == 0
            sayi = await price_tick(provider, write_history=gecmis_yaz)
            logger.debug("fiyat tick", extra={"updated": sayi, "history": gecmis_yaz})
        except asyncio.CancelledError:
            logger.info("fiyat gorevi durduruldu")
            raise
        except Exception:  # noqa: BLE001 - tek tick hatasi dongunu durdurmamali
            logger.exception("fiyat tick basarisiz")

        await asyncio.sleep(settings.price_tick_seconds)
