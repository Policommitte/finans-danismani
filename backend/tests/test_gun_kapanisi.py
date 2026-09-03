"""Gun devri: `live_prices` -> `price_history` kapanis akisi.

Test edilen davranis (mimari v4 bolum 8, canli fiyat yonlendirmesi):

    her tick   -> live_prices'a satir           (gun ici, cok satir)
    gun bitince-> gunun SON satiri price_history'ye kapanis olarak yazilir,
                  o gune ait live_prices satirlari silinir, prev_close tazelenir

Bu testler GERCEK veritabani ister (`@pytest.mark.db`) cunku dogrulanan sey
tam olarak SQL semantigidir: saat dilimine gore gun siniri, `DISTINCT ON` ile
son satir secimi ve silmenin yalnizca kapanan gunu kapsamasi. Bunlari taklit
bir depoyla test etmek yalnizca taklidi test etmek olurdu.

Her test kendi yazdigini geri alir: `assets` fiyat kolonlari ve dokunulan
`price_history` satirlari eski haline dondurulur, `live_prices` temizlenir.
Alinmasaydi sonraki toplam/dagilim testleri seed degerini gormezdi.
"""

from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text

from app.config import settings
from tests.conftest import SahteApiSaglayici

pytestmark = pytest.mark.db

#: Testlerde kullanilan varlik (seed'de her zaman var).
SEMBOL = "THYAO"


def _session():
    from app.db.session import get_session_factory

    return get_session_factory()()


async def _query(sql: str, params: dict | None = None) -> list[dict]:
    async with _session() as session:
        sonuc = await session.execute(text(sql), params or {})
        return [dict(satir) for satir in sonuc.mappings().all()]


async def _execute(sql: str, params: dict | None = None) -> None:
    async with _session() as session:
        await session.execute(text(sql), params or {})
        await session.commit()


async def _asset_id(sembol: str = SEMBOL) -> int:
    satir = await _query("SELECT id FROM assets WHERE symbol = :s", {"s": sembol})
    return int(satir[0]["id"])


async def _day_start(gun_farki: int) -> str:
    """Bugunden `gun_farki` gun onceki TURKIYE tarihini `YYYY-AA-GG` dondurur."""
    satir = await _query(
        """
        SELECT CAST(
                   date_trunc('day', now() AT TIME ZONE CAST(:tz AS TEXT))
                   - make_interval(days => :fark)
               AS DATE) AS gun
        """,
        {"tz": settings.market_day_timezone, "fark": gun_farki},
    )
    return str(satir[0]["gun"])


async def _add_live_price(asset_id: int, gun: str, saat: str, fiyat: float, kaynak: str) -> None:
    """Belirli bir gun/saatte (Turkiye saati) canli fiyat satiri yaratir."""
    await _execute(
        """
        INSERT INTO live_prices (asset_id, price, source, created_at)
        VALUES (:aid, :fiyat, :kaynak,
                CAST(CAST(:gun AS DATE) + CAST(:saat AS TIME) AS TIMESTAMP)
                    AT TIME ZONE CAST(:tz AS TEXT))
        """,
        {
            "aid": asset_id,
            "fiyat": fiyat,
            "kaynak": kaynak,
            "gun": gun,
            "saat": saat,
            "tz": settings.market_day_timezone,
        },
    )


#: Testlerin dokundugu zaman penceresi. Seed verisi bu araligi doldurdugu
#: icin once BOSALTILIR, test bitince birebir geri konur - aksi halde
#: "kapanis yazildi mi" sorgulari seed satirlarini sayardi.
PENCERE = "5 days"


@asynccontextmanager
async def _clean_environment():
    """Test penceresini bosaltir, cikista `assets` ve `price_history`'yi geri koyar."""
    async with _session() as session:
        onceki_varlik = (
            (
                await session.execute(
                    text("SELECT id, current_price, prev_close, daily_change_pct FROM assets")
                )
            )
            .mappings()
            .all()
        )
        onceki_gecmis = (
            (
                await session.execute(
                    text(
                        "SELECT asset_id, ts, price, source FROM price_history "
                        f"WHERE ts >= now() - INTERVAL '{PENCERE}'"
                    )
                )
            )
            .mappings()
            .all()
        )
        await session.execute(text("DELETE FROM live_prices"))
        await session.execute(
            text(f"DELETE FROM price_history WHERE ts >= now() - INTERVAL '{PENCERE}'")
        )
        await session.commit()

    try:
        yield
    finally:
        async with _session() as session:
            await session.execute(text("DELETE FROM live_prices"))
            await session.execute(
                text(f"DELETE FROM price_history WHERE ts >= now() - INTERVAL '{PENCERE}'")
            )
            for satir in onceki_gecmis:
                await session.execute(
                    text(
                        "INSERT INTO price_history (asset_id, ts, price, source) "
                        "VALUES (:a, :t, :p, :k) ON CONFLICT (asset_id, ts) DO NOTHING"
                    ),
                    {
                        "a": satir["asset_id"],
                        "t": satir["ts"],
                        "p": satir["price"],
                        "k": satir["source"],
                    },
                )
            for satir in onceki_varlik:
                await session.execute(
                    text(
                        "UPDATE assets SET current_price = :p, prev_close = :pc, "
                        "daily_change_pct = :d WHERE id = :i"
                    ),
                    {
                        "p": satir["current_price"],
                        "pc": satir["prev_close"],
                        "d": satir["daily_change_pct"],
                        "i": satir["id"],
                    },
                )
            await session.commit()


# ---------------------------------------------------------------------------
# Tick -> live_prices
# ---------------------------------------------------------------------------


async def test_tick_writes_live_prices_not_price_history():
    """Yonlendirmenin ozu: gun ici tick GECMIS tabloyu sismez."""
    from app.market.scheduler import price_tick

    async with _clean_environment():
        gecmis_once = (await _query("SELECT count(*) AS n FROM price_history"))[0]["n"]

        await price_tick(SahteApiSaglayici(), write_live=True)

        canli = (await _query("SELECT count(*) AS n FROM live_prices"))[0]["n"]
        gecmis_sonra = (await _query("SELECT count(*) AS n FROM price_history"))[0]["n"]

        assert canli > 0, "canli fiyat live_prices'a yazilmali"
        assert gecmis_sonra == gecmis_once, "gun ici tick price_history'ye YAZMAMALI"


async def test_no_live_row_written_when_write_live_disabled():
    from app.market.scheduler import price_tick

    async with _clean_environment():
        await price_tick(SahteApiSaglayici(), write_live=False)

        assert (await _query("SELECT count(*) AS n FROM live_prices"))[0]["n"] == 0


async def test_tick_does_not_touch_prev_close():
    """`daily_change_pct` "dune gore" kalmali: prev_close gun ici sabittir.

    Onceki davranista her tick `prev_close = current_price` yapiyordu; boylece
    yuzde "son tick'e gore degisim"e donusuyor ve gun ici 100 -> 102 -> 104
    icin +2, +4 yerine +2, +1.96 cikiyordu.
    """
    from app.market.scheduler import price_tick

    async with _clean_environment():
        onceki = await _query("SELECT id, prev_close FROM assets ORDER BY id")

        await price_tick(SahteApiSaglayici(carpan=1.02), write_live=True)
        await price_tick(SahteApiSaglayici(carpan=1.04), write_live=True)

        sonraki = await _query("SELECT id, prev_close FROM assets ORDER BY id")
        assert sonraki == onceki


# ---------------------------------------------------------------------------
# Gun kapanisi
# ---------------------------------------------------------------------------


async def test_todays_rows_do_not_wait_for_close():
    """Gun daha bitmedi: bugunun canli satirlari silinmemeli."""
    from app.market.scheduler import close_finished_days
    from app.repositories.deps import get_market_repository

    async with _clean_environment():
        aid = await _asset_id()
        bugun = await _day_start(0)
        await _add_live_price(aid, bugun, "10:00", 100.0, "api")

        assert await get_market_repository().pending_close_days() == []
        assert await close_finished_days() == 0
        assert (await _query("SELECT count(*) AS n FROM live_prices"))[0]["n"] == 1


async def test_day_close_writes_last_price_to_history_and_clears_day():
    from app.market.scheduler import close_finished_days

    async with _clean_environment():
        aid = await _asset_id()
        dun = await _day_start(1)
        bugun = await _day_start(0)

        await _add_live_price(aid, dun, "09:30", 100.0, "api")
        await _add_live_price(aid, dun, "13:00", 105.0, "api")
        await _add_live_price(aid, dun, "17:45", 110.0, "api")  # gunun SON fiyati
        await _add_live_price(aid, bugun, "09:30", 120.0, "api")  # yeni gun - kalmali

        assert await close_finished_days() == 1

        kapanis = await _query(
            """
            SELECT price, source FROM price_history
            WHERE asset_id = :a
              AND ts = CAST(CAST(:gun AS DATE) AS TIMESTAMP) AT TIME ZONE CAST(:tz AS TEXT)
            """,
            {"a": aid, "gun": dun, "tz": settings.market_day_timezone},
        )
        assert len(kapanis) == 1
        assert float(kapanis[0]["price"]) == 110.0
        assert kapanis[0]["source"] == "api"

        kalan = await _query("SELECT price FROM live_prices ORDER BY id")
        assert [float(k["price"]) for k in kalan] == [120.0], "yalnizca kapanan gun silinmeli"


async def test_close_updates_prev_close():
    from app.market.scheduler import close_finished_days

    async with _clean_environment():
        aid = await _asset_id()
        dun = await _day_start(1)
        await _add_live_price(aid, dun, "17:45", 111.0, "api")

        await close_finished_days()

        satir = await _query("SELECT prev_close FROM assets WHERE id = :a", {"a": aid})
        assert float(satir[0]["prev_close"]) == 111.0


async def test_missed_days_closed_in_bulk():
    """Uygulama hafta sonu kapali kaldiysa acilista hepsi sirayla kapanmali."""
    from app.market.scheduler import close_finished_days
    from app.repositories.deps import get_market_repository

    async with _clean_environment():
        aid = await _asset_id()
        gunler = [await _day_start(3), await _day_start(2), await _day_start(1)]
        for sira, gun in enumerate(gunler, start=1):
            await _add_live_price(aid, gun, "17:45", 100.0 + sira, "api")

        assert await get_market_repository().pending_close_days() == gunler
        assert await close_finished_days() == 3

        kapanislar = await _query(
            "SELECT price FROM price_history WHERE asset_id = :a AND ts >= now() - "
            "INTERVAL '4 days' ORDER BY ts",
            {"a": aid},
        )
        assert [float(k["price"]) for k in kapanislar] == [101.0, 102.0, 103.0]
        assert (await _query("SELECT count(*) AS n FROM live_prices"))[0]["n"] == 0


async def test_close_is_rerunnable():
    """Ayni gunu iki kez kapatmak hata vermemeli, veri bozmamali."""
    from app.market.scheduler import close_finished_days

    async with _clean_environment():
        aid = await _asset_id()
        dun = await _day_start(1)
        await _add_live_price(aid, dun, "17:45", 110.0, "api")

        assert await close_finished_days() == 1
        assert await close_finished_days() == 0  # bekleyen gun kalmadi

        kapanis = await _query(
            "SELECT count(*) AS n FROM price_history WHERE asset_id = :a AND ts >= "
            "now() - INTERVAL '2 days'",
            {"a": aid},
        )
        assert kapanis[0]["n"] == 1


async def test_simulated_close_does_not_overwrite_real_data():
    """Yahoo'ya ulasilamayan bir gun, mevcut GERCEK kapanisi bozmamali."""
    from app.market.scheduler import close_finished_days

    async with _clean_environment():
        aid = await _asset_id()
        dun = await _day_start(1)

        # Gercek (backfill) kapanis zaten yazilmis olsun.
        await _execute(
            """
            INSERT INTO price_history (asset_id, ts, price, source)
            VALUES (:a, CAST(CAST(:gun AS DATE) AS TIMESTAMP)
                        AT TIME ZONE CAST(:tz AS TEXT), 999.0, 'backfill')
            ON CONFLICT (asset_id, ts) DO UPDATE SET price = 999.0, source = 'backfill'
            """,
            {"a": aid, "gun": dun, "tz": settings.market_day_timezone},
        )
        await _add_live_price(aid, dun, "17:45", 110.0, "simulated")

        await close_finished_days()

        satir = await _query(
            """
            SELECT price, source FROM price_history
            WHERE asset_id = :a
              AND ts = CAST(CAST(:gun AS DATE) AS TIMESTAMP) AT TIME ZONE CAST(:tz AS TEXT)
            """,
            {"a": aid, "gun": dun, "tz": settings.market_day_timezone},
        )
        assert float(satir[0]["price"]) == 999.0
        assert satir[0]["source"] == "backfill"


async def test_real_close_corrects_simulated_row():
    """Ters yon: gercek veri, daha once yazilmis simule kapanisi DUZELTMELI."""
    from app.market.scheduler import close_finished_days

    async with _clean_environment():
        aid = await _asset_id()
        dun = await _day_start(1)

        await _execute(
            """
            INSERT INTO price_history (asset_id, ts, price, source)
            VALUES (:a, CAST(CAST(:gun AS DATE) AS TIMESTAMP)
                        AT TIME ZONE CAST(:tz AS TEXT), 1.0, 'simulated')
            ON CONFLICT (asset_id, ts) DO UPDATE SET price = 1.0, source = 'simulated'
            """,
            {"a": aid, "gun": dun, "tz": settings.market_day_timezone},
        )
        await _add_live_price(aid, dun, "17:45", 110.0, "api")

        await close_finished_days()

        satir = await _query(
            """
            SELECT price, source FROM price_history
            WHERE asset_id = :a
              AND ts = CAST(CAST(:gun AS DATE) AS TIMESTAMP) AT TIME ZONE CAST(:tz AS TEXT)
            """,
            {"a": aid, "gun": dun, "tz": settings.market_day_timezone},
        )
        assert float(satir[0]["price"]) == 110.0
        assert satir[0]["source"] == "api"


async def test_day_boundary_follows_turkey_time():
    """UTC 22:00 Turkiye'de ERTESI gundur; kapanis o gune yazilmamali.

    Sunucu (Supabase) UTC calisiyor. Gun siniri UTC'ye birakilsaydi Turkiye
    saatiyle 01:00'deki bir tick bir onceki gune sayilirdi.
    """
    from app.repositories.deps import get_market_repository

    async with _clean_environment():
        aid = await _asset_id()
        dun = await _day_start(1)

        # Turkiye saatiyle dun 23:30 -> UTC'de dun 20:30. Ayni gune ait.
        await _add_live_price(aid, dun, "23:30", 110.0, "api")
        # Turkiye saatiyle BUGUN 00:30 -> hala kapanmamis gun.
        await _add_live_price(aid, await _day_start(0), "00:30", 120.0, "api")

        assert await get_market_repository().pending_close_days() == [dun]
