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
from app.repositories.deps import get_market_repository, get_portfolio_repository

logger = logging.getLogger(__name__)

#: Veritabanina YAZILMASINA izin verilen fiyat kaynaklari.
#:
#: `ApiMarketProvider` veri yoksa bos liste dondurur. Bu beyaz liste yeni bir
#: saglayici eklendiginde yazma izninin ACIKCA verilmesini zorunlu kilar.
#:
#: NEDEN GEREKLI: herkes ayni Supabase'e bagli. Tek bir gelistiricinin
#: `.env`'inde `simulated` yazmasi ortak tarihceyi kirletmeye yetiyor -
#: 20 Agustos 2026'da `price_history`'ye tek gunde 3.616 sahte satir boyle
#: girdi. Kullaniciya taze SAHTE fiyat gostermek, bayat GERCEK fiyat
#: gostermekten daha kotudur.
#:
#: Beyaz liste (kara liste degil) bilincli: yeni bir saglayici eklenirse
#: yazma izni ACIKCA verilmelidir, yanlislikla degil.
YAZILABILIR_KAYNAKLAR = frozenset({"api"})

#: Bunun altindaki tick araliginda gunluk api kotasi saatler icinde dolar.
#: 16 ticker x (3600/60) tick/saat = saatte 960 istek -> 2.500'luk tavan
#: ~2,6 saatte biter. Varsayilan 300 saniyede saatte 192 istek olur.
ASGARI_ONERILEN_TICK_SANIYE = 300
ONE_MINUTE_RETENTION_DAYS = 30
PORTFOLIO_SNAPSHOT_RETENTION_DAYS = 30


async def price_tick(provider: MarketDataProvider, write_live: bool) -> int:
    """Tek bir guncelleme adimi. Test edilebilir olmasi icin ayri fonksiyon.

    Kaynak `YAZILABILIR_KAYNAKLAR` icinde degilse HICBIR SEY yazilmaz -
    `assets.current_price` bile guncellenmez - ve `0` doner.
    """
    repository = get_market_repository()
    assets = await repository.get_assets_for_price_update()
    if not assets:
        return 0

    updates = await provider.next_prices(assets)

    # API veri uretemediyse `updates` bostur ve repository mevcut fiyatlara
    # dokunmaz.
    kaynak = getattr(provider, "son_kaynak", provider.name)

    if kaynak not in YAZILABILIR_KAYNAKLAR:
        # WARNING seviyesi bilincli: "gercek fiyat alamiyoruz" fark edilmesi
        # gereken bir durumdur. Yahoo saatlerce cokerse log gurultulu olur -
        # gurultunun kendisi de bilgidir.
        logger.warning(
            "gercek fiyat alinamadi; bu tick veritabanina YAZILMADI",
            extra={"source": kaynak, "skipped_assets": len(updates)},
        )
        return 0

    yazilan = await repository.apply_price_updates(updates, write_live=write_live, source=kaynak)

    # Paper emirleri eski/cache fiyatiyla degil, yalnizca bu tick'te dis
    # kaynaktan dogrulanmis fiyat gelen varliklarla gerceklestiririz.
    try:
        from app.services.trading import bekleyen_emirleri_isle

        gerceklesen = await bekleyen_emirleri_isle(updates)
        if gerceklesen:
            logger.info("paper emirleri gerceklesti", extra={"orders": gerceklesen})
    except Exception:  # noqa: BLE001 - emir motoru fiyat akisini durdurmamali
        logger.exception("paper emirleri islenemedi")

    # Emirlerin gerceklesmesi pozisyon ve nakdi degistirebilir. Bu nedenle
    # snapshot fiyat yazimindan ve emir islemeden SONRA alinir. Ancak hicbir
    # Yahoo fiyati yazilamayan bir tur, eski fiyatlarla yeni bir grafik noktasi
    # uretmemelidir. Boylece grafigin en sag noktasi daima son BASARILI fiyat
    # turunun portfoy degeridir.
    if yazilan > 0:
        try:
            snapshot_count = await get_portfolio_repository().write_value_snapshots()
            logger.debug("portfoy snapshot'i yazildi", extra={"portfolios": snapshot_count})
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - snapshot fiyat akisini durdurmamali
            logger.exception("portfoy snapshot'i yazilamadi")

    # Mum arsivleme, ozellikle uygulamanin ilk Yahoo paketinde uzun surebilir.
    # Portfoy snapshot'ini bunun arkasinda bekletmeyiz; aksi halde dashboard
    # yeni fiyati gosterirken grafik bir onceki noktada kalabilir.
    mumlar = getattr(provider, "son_mumlar", [])
    if mumlar:
        try:
            await repository.upsert_candles(mumlar, source="yahoo")
        except Exception:  # noqa: BLE001 - mum yazimi fiyat akisini durdurmamali
            logger.exception("OHLCV mumlari yazilamadi")

    # Otonom oneri turu: sinyal uretimi ve TTL kapanisi. Fiyat yazildiktan
    # SONRA calisir - sinyaller bu tick'te dogrulanmis fiyatlari gorsun.
    try:
        from app.services.recommendation import expire_due_recommendations, generate_recommendations

        dolan = await expire_due_recommendations()
        if dolan:
            logger.info("suresi dolan oneriler kapatildi", extra={"expired": dolan})
        sonuc = await generate_recommendations()
        if sonuc.get("recommendations"):
            logger.info("otonom oneri uretildi", extra=sonuc)
    except Exception:  # noqa: BLE001 - oneri motoru fiyat akisini durdurmamali
        logger.exception("otonom oneri turu basarisiz")

    # Bildirim outbox'ini ayni turda bosalt. Mail kanali bagli degilse bu cagri
    # satirlari SKIPPED olarak kapatir - PENDING birikip, kanal aylar sonra
    # acildiginda gecmis bildirimlerin topluca gitmesini onler.
    try:
        from app.notifications.dispatcher import dispatch_notifications

        await dispatch_notifications()
    except Exception:  # noqa: BLE001 - bildirim fiyat akisini durdurmamali
        logger.exception("bildirim outbox'i islenemedi")

    return yazilan


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


async def cleanup_old_candles() -> int:
    """1 dakikalik mumlari 30 gunluk kayan pencerede tutar."""
    deleted = await get_market_repository().prune_candles(
        interval="1m", keep_days=ONE_MINUTE_RETENTION_DAYS
    )
    if deleted:
        logger.info("eski 1dk mumlari temizlendi", extra={"deleted": deleted})
    return deleted


async def cleanup_old_portfolio_snapshots() -> int:
    """Portfoy snapshot'larini 30 gunluk kayan pencerede tutar."""
    deleted = await get_portfolio_repository().prune_value_snapshots(
        keep_days=PORTFOLIO_SNAPSHOT_RETENTION_DAYS
    )
    if deleted:
        logger.info("eski portfoy snapshot'lari temizlendi", extra={"deleted": deleted})
    return deleted


async def reconcile_hourly_candles(provider: MarketDataProvider) -> int:
    """Dogru kaynak zamanlarini gunde bir kez tamamlanmis 1h mumlara uygular."""
    refresh = getattr(provider, "reconcile_hourly_candles", None)
    if refresh is None:
        return 0

    repository = get_market_repository()
    assets = await repository.get_assets_for_price_update()
    candles = await refresh(assets)
    if not candles:
        return 0
    written = await repository.upsert_candles(candles, source="yahoo_1h")
    logger.info("saatlik mumlar uzlastirildi", extra={"candles": written})
    return written


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

    # Yanlis ayarlanmis bir tick araligi SESSIZ degil GORUNUR olsun: kota
    # dolunca saglayici veri uretemez ve fiyatlar sessizce donar. Sebebi
    # burada bir kez soyluyoruz.
    if 0 < settings.price_tick_seconds < ASGARI_ONERILEN_TICK_SANIYE:
        logger.warning(
            "PRICE_TICK_SECONDS cok kisa - gunluk api kotasi saatler icinde dolar, "
            "sonrasinda fiyatlar hic guncellenmez",
            extra={
                "price_tick_seconds": settings.price_tick_seconds,
                "onerilen_asgari": ASGARI_ONERILEN_TICK_SANIYE,
            },
        )

    while True:
        # Ayri try/except: gun kapanisi patlarsa fiyat guncellemesi yine de
        # calismali. Ikisi ayni bloka konsaydi kapanistaki kalici bir hata
        # fiyatlari da tamamen durdururdu.
        closed_days = 0
        try:
            closed_days = await close_finished_days()
        except asyncio.CancelledError:
            logger.info("fiyat gorevi durduruldu")
            raise
        except Exception:  # noqa: BLE001 - kapanis hatasi dongunu durdurmamali
            logger.exception("gun kapanisi basarisiz")

        # Bekleyen gun kaydi kalici olarak kapandigi icin bu tetikleyici ayni
        # gun icinde yeniden baslatmalarda da gereksiz uzlastirma yapmaz.
        if closed_days:
            try:
                await reconcile_hourly_candles(provider)
            except asyncio.CancelledError:
                logger.info("fiyat gorevi durduruldu")
                raise
            except Exception:  # noqa: BLE001 - uzlastirma canli akisi durdurmamali
                logger.exception("saatlik mum uzlastirmasi basarisiz")

        try:
            tick += 1
            cleanup_every = max(86400 // max(settings.price_tick_seconds, 1), 1)
            if tick == 1 or tick % cleanup_every == 0:
                try:
                    await cleanup_old_candles()
                except Exception:  # noqa: BLE001 - bakim fiyat akisini durdurmamali
                    logger.exception("eski mum temizligi basarisiz")
                try:
                    await cleanup_old_portfolio_snapshots()
                except Exception:  # noqa: BLE001 - bakim fiyat akisini durdurmamali
                    logger.exception("eski portfoy snapshot temizligi basarisiz")
            canli_yaz = tick % max(settings.price_history_every_n_ticks, 1) == 0
            sayi = await price_tick(provider, write_live=canli_yaz)
            logger.debug("fiyat tick", extra={"updated": sayi, "live": canli_yaz})
        except asyncio.CancelledError:
            logger.info("fiyat gorevi durduruldu")
            raise
        except Exception:  # noqa: BLE001 - tek tick hatasi dongunu durdurmamali
            logger.exception("fiyat tick basarisiz")

        await asyncio.sleep(settings.price_tick_seconds)
