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


async def price_tick(provider: MarketDataProvider, write_live: bool) -> int:
    """Tek bir guncelleme adimi. Test edilebilir olmasi icin ayri fonksiyon."""
    repository = get_market_repository()
    assets = await repository.get_prices_for_simulation()
    if not assets:
        return 0

    updates = await provider.next_prices(assets)

    # Saglayici yedege dusmus olabilir (kota/ag hatasi); bu durumda kaynak
    # "api" DEGIL "simulated"dir. `son_kaynak` yoksa saglayici adi kullanilir.
    kaynak = getattr(provider, "son_kaynak", provider.name)

    return await repository.apply_price_updates(updates, write_live=write_live, source=kaynak)


async def close_finished_days() -> int:
    """Kapanmis gunleri `price_history`'ye tasir; kapatilan gun sayisini doner.

    Gun ici fiyatlar `live_prices`'ta birikir. Turkiye saatiyle gun degisince
    o gunun SON fiyati gecmis tabloya kapanis olarak yazilir ve gunun canli
    satirlari silinir.

    Kontrol her tick'te yapilir; bunun icin ayri bir zamanlayici KURULMAZ.
    Nedeni: sabit saatte tetiklenen bir gorev uygulama o anda kapaliysa
    (gece yeniden baslatma, hafta sonu) gunu sessizce atlardi. Bekleyen
    gunler `live_prices`'in kendisinden okundugu icin buradaki dongu
    kaldiginda yerden devam eder ve birikmis gunleri sirayla kapatir.
    """
    repository = get_market_repository()
    gunler = await repository.pending_close_days()

    for gun in gunler:
        adet = await repository.close_out_day(gun)
        logger.info("gun kapanisi yazildi", extra={"day": gun, "assets": adet})

    return len(gunler)


async def run_price_scheduler(provider: MarketDataProvider | None = None) -> None:
    """Sonsuz dongu - `asyncio.create_task` ile baslatilir, iptal edilerek durur.

    Her dongude once GUN DEVRI kontrol edilir, sonra fiyat tick'i atilir.
    Gun devri once gelir ki gun degistigi anda eski gunun kapanisi, yeni gunun
    ilk satiri yazilmadan once alinmis olsun.

    `live_prices`'a her tick'te DEGIL, N tick'te bir yazilir; `price_history`'ye
    ise yalnizca gunde bir kapanis satiri gider (bkz. `close_finished_days`).
    """
    provider = provider or build_provider()
    tick = 0

    logger.info(
        "fiyat gorevi basladi",
        extra={
            "provider": provider.name,
            "period_s": settings.price_tick_seconds,
            "day_tz": settings.market_day_timezone,
        },
    )

    while True:
        # Ayri try/except: gun kapanisi patlarsa fiyat guncellemesi yine de
        # calismali. Ikisi ayni bloka konsaydi kapanistaki kalici bir hata
        # fiyatlari da tamamen durdururdu.
        try:
            await close_finished_days()
        except asyncio.CancelledError:
            logger.info("fiyat gorevi durduruldu")
            raise
        except Exception:  # noqa: BLE001 - kapanis hatasi dongunu durdurmamali
            logger.exception("gun kapanisi basarisiz")

        try:
            tick += 1
            canli_yaz = tick % max(settings.price_history_every_n_ticks, 1) == 0
            sayi = await price_tick(provider, write_live=canli_yaz)
            logger.debug("fiyat tick", extra={"updated": sayi, "live": canli_yaz})
        except asyncio.CancelledError:
            logger.info("fiyat gorevi durduruldu")
            raise
        except Exception:  # noqa: BLE001 - tek tick hatasi dongunu durdurmamali
            logger.exception("fiyat tick basarisiz")

        await asyncio.sleep(settings.price_tick_seconds)
