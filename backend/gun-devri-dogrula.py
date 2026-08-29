"""Gun devri dogrulamasi - GECE YARISINI BEKLEMEDEN test eder.

Kullanim (backend/ klasorunun ICINDEN):

    python gun-devri-dogrula.py

Ne yapar
--------
1. `db/migrations/002_live_prices.sql` uygulanmis mi diye bakar.
2. BOS bir gun secip oraya sahte canli fiyat satirlari yazar.
3. Gun devrini calistirir - gercek uretim kodu.
4. Kapanisin `price_history`'ye dogru yazildigini, `live_prices`'in o gun
   icin bosaldigini ve `prev_close`'un guncellendigini kontrol eder.
5. YAZDIGI HER SEYI GERI ALIR.

Ortak veritabaninda calistirmak neden guvenli
---------------------------------------------
* Test gunu SABIT DEGIL: gecmisin en eski gununden 30 gun oncesi secilir ve
  o tarihte gercekten satir olmadigi ayrica dogrulanir. Ekip ne kadar geriye
  backfill yaparsa yapsin betik gercek bir satirin uzerine yazmaz.
* Baska gunler de kapanmayi bekliyorsa (gercek tick'lerden kalmis) betik
  ONLARA DOKUNMAZ - yalnizca kendi test gununu kapatir.
* `assets` uzerinde gecici olarak `prev_close` degisir; betik sonunda eski
  degerine dondurulur.

Betigin hic dokunmadiklari: portfoy, sohbet, RAG, kullanici tablolari; guncel
fiyatlar; gercek `price_history` satirlari.
"""

from __future__ import annotations

import asyncio
import sys

# WINDOWS: psycopg'nin async surucusu Windows'un varsayilan ProactorEventLoop'u
# ile CALISMAZ. Uygulama tarafinda ayni duzeltme `run.py` icinde yapiliyor;
# bu betik uvicorn'dan bagimsiz calistigi icin kendi loop'unu kurmadan ONCE
# ayni policy'yi burada da ayarlamak zorunda. Satir, `asyncio.run()`
# cagrilmadan once ve modul seviyesinde olmali.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_SEMBOL = "THYAO"
TEST_FIYATLARI = [(9.0, "09:30"), (11.0, "13:00"), (13.0, "17:45")]  # sonuncusu kapanis

TAMAM = "  [TAMAM]"
HATA = "  [HATA] "


def _basari(mesaj: str) -> bool:
    print(f"{TAMAM} {mesaj}")
    return True


def _hata(mesaj: str) -> bool:
    print(f"{HATA} {mesaj}")
    return False


async def main() -> int:
    try:
        from sqlalchemy import text

        from app.config import settings
        from app.db.session import get_session_factory
        from app.market.scheduler import close_finished_days
        from app.repositories.deps import describe_backend, get_market_repository
    except Exception as exc:  # pragma: no cover
        print(f"HATA: modul yuklenemedi ({exc}). backend/ icinden calistirin.")
        return 1

    if describe_backend() != "postgresql":
        print("HATA: veritabanina baglanilamadi (bellek ici yedege dusuldu).")
        print("      backend/.env icindeki DATABASE_URL'i kontrol edin ve")
        print("      komutu backend/ klasorunun ICINDEN calistirin.")
        return 1

    tz = settings.market_day_timezone
    fabrika = get_session_factory()
    repo = get_market_repository()
    print(f"Baglanti OK · gun saat dilimi = {tz}\n")

    async def sorgu(sql: str, params: dict | None = None) -> list[dict]:
        async with fabrika() as oturum:
            sonuc = await oturum.execute(text(sql), params or {})
            return [dict(s) for s in sonuc.mappings().all()]

    async def calistir(sql: str, params: dict | None = None) -> None:
        async with fabrika() as oturum:
            await oturum.execute(text(sql), params or {})
            await oturum.commit()

    # --- 1) Migration uygulanmis mi? ------------------------------------
    print("[1] SEMA")
    kolonlar = {
        s["column_name"]: s["is_nullable"]
        for s in await sorgu(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='live_prices'"
        )
    }
    if not kolonlar:
        _hata("live_prices tablosu YOK.")
        return 1

    sema_tamam = True
    if "source" not in kolonlar:
        sema_tamam = _hata("`source` kolonu YOK -> migration 002 calistirilmali.")
    else:
        _basari("`source` kolonu var")
    if kolonlar.get("asset_id") == "YES":
        sema_tamam = _hata("`asset_id` hala NULL kabul ediyor -> migration 002.")
    else:
        _basari("`asset_id` NOT NULL")

    indeksler = {
        s["indexname"]
        for s in await sorgu("SELECT indexname FROM pg_indexes WHERE tablename='live_prices'")
    }
    if "live_prices_created_idx" not in indeksler:
        sema_tamam = _hata("`created_at` indeksi YOK -> migration 002.")
    else:
        _basari("`created_at` indeksi var")

    if not sema_tamam:
        print("\nSONUC: once migration'i calistirin:")
        print('  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f ../db/migrations/002_live_prices.sql')
        return 2

    # --- Yedek al -------------------------------------------------------
    varlik = (
        await sorgu(
            "SELECT id, prev_close, current_price, daily_change_pct FROM assets WHERE symbol = :s",
            {"s": TEST_SEMBOL},
        )
    )[0]
    aid = varlik["id"]

    # --- Bos bir test gunu SEC ------------------------------------------
    # Sabit tarih tahmin etmek yerine gercek veriye bakiyoruz: gecmisin en
    # eski gununden 30 gun ONCESI kesinlikle bostur. Boylece ekip ne kadar
    # geriye backfill yaparsa yapsin betik gercek bir satirin uzerine yazmaz.
    aralik = (
        await sorgu(
            """
            SELECT CAST(min(ts) AT TIME ZONE CAST(:tz AS TEXT) AS DATE) AS ilk,
                   CAST(max(ts) AT TIME ZONE CAST(:tz AS TEXT) AS DATE) AS son,
                   count(*) AS adet
            FROM price_history WHERE asset_id = :a
            """,
            {"a": aid, "tz": tz},
        )
    )[0]
    print(
        f"    {TEST_SEMBOL} gecmisi: {aralik['ilk']} .. {aralik['son']}  ({aralik['adet']} satir)"
    )

    test_gunu = None
    for geri in range(30, 40):
        aday = (
            await sorgu(
                """
                SELECT CAST(COALESCE(
                           (SELECT min(ts) AT TIME ZONE CAST(:tz AS TEXT) FROM price_history
                             WHERE asset_id = :a),
                           now() AT TIME ZONE CAST(:tz AS TEXT)
                       ) AS DATE) - CAST(:geri AS INTEGER) AS gun
                """,
                {"a": aid, "tz": tz, "geri": geri},
            )
        )[0]["gun"]
        dolu = await sorgu(
            """
            SELECT 1 FROM price_history WHERE asset_id = :a
              AND ts = CAST(CAST(:g AS DATE) AS TIMESTAMP) AT TIME ZONE CAST(:tz AS TEXT)
            """,
            {"a": aid, "g": str(aday), "tz": tz},
        )
        if not dolu:
            test_gunu = str(aday)
            break

    if test_gunu is None:
        print("\nHATA: bos bir test gunu bulunamadi.")
        return 1
    print(f"    test gunu olarak {test_gunu} secildi (bos)")

    try:
        # --- 2) Sahte gun ici fiyatlar --------------------------------
        print("\n[2] GUN ICI CANLI FIYAT")
        await calistir(
            "DELETE FROM live_prices WHERE created_at < CAST(:g AS DATE) + 1",
            {"g": test_gunu},
        )
        for fiyat, saat in TEST_FIYATLARI:
            await calistir(
                """
                INSERT INTO live_prices (asset_id, price, source, created_at)
                VALUES (:a, :p, 'simulated',
                        CAST(CAST(:g AS DATE) + CAST(:s AS TIME) AS TIMESTAMP)
                            AT TIME ZONE CAST(:tz AS TEXT))
                """,
                {"a": aid, "p": fiyat, "g": test_gunu, "s": saat, "tz": tz},
            )
        adet = (
            await sorgu(
                "SELECT count(*) AS n FROM live_prices WHERE created_at < CAST(:g AS DATE) + 1",
                {"g": test_gunu},
            )
        )[0]["n"]
        _basari(f"{adet} canli satir yazildi (son fiyat {TEST_FIYATLARI[-1][0]})")

        # --- 3) Bekleyen gun gorunuyor mu? ----------------------------
        print("\n[3] BEKLEYEN GUN")
        bekleyen = await repo.pending_close_days()
        if test_gunu not in bekleyen:
            _hata(f"{test_gunu} bekleyenler arasinda YOK: {bekleyen}")
            return 3
        _basari(f"pending_close_days() -> {bekleyen}")

        baskalari = [g for g in bekleyen if g != test_gunu]

        # --- 4) Gun devri ---------------------------------------------
        print("\n[4] GUN DEVRI")
        if baskalari:
            # ORTAK VERITABANI KORUMASI: bunlar gercek tick'lerden kalmis,
            # kapanmayi bekleyen GERCEK gunler. `close_finished_days()`
            # hepsini kapatirdi - dogru davranis ama bir TEST betiginin
            # yapmasi gereken sey degil. Yalnizca kendi gunumuzu kapatiyoruz.
            print(f"    NOT: {len(baskalari)} gercek gun de kapanmayi bekliyor: {baskalari}")
            print("         Betik onlara DOKUNMUYOR; yalnizca kendi test gununu kapatiyor.")
            print("         (Backend calisir calismaz onlari kendisi kapatacak.)")
            await repo.close_out_day(test_gunu)
            _basari(f"close_out_day('{test_gunu}') calisti")
        else:
            kapatilan = await close_finished_days()
            _basari(f"close_finished_days() -> {kapatilan} gun kapatildi")

        sonuc = True

        kapanis = await sorgu(
            """
            SELECT price, source FROM price_history WHERE asset_id = :a
              AND ts = CAST(CAST(:g AS DATE) AS TIMESTAMP) AT TIME ZONE CAST(:tz AS TEXT)
            """,
            {"a": aid, "g": test_gunu, "tz": tz},
        )
        beklenen = TEST_FIYATLARI[-1][0]
        if kapanis and float(kapanis[0]["price"]) == beklenen:
            _basari(f"price_history kapanisi = {beklenen} (gunun SON fiyati)")
        else:
            sonuc = _hata(f"kapanis beklenen {beklenen} degil: {kapanis}")

        kalan = (
            await sorgu(
                "SELECT count(*) AS n FROM live_prices WHERE created_at < CAST(:g AS DATE) + 1",
                {"g": test_gunu},
            )
        )[0]["n"]
        if kalan == 0:
            _basari("o gunun live_prices satirlari silindi")
        else:
            sonuc = _hata(f"{kalan} canli satir silinmemis")

        yeni_prev = (await sorgu("SELECT prev_close FROM assets WHERE id = :a", {"a": aid}))[0][
            "prev_close"
        ]
        if yeni_prev is not None and float(yeni_prev) == beklenen:
            _basari(f"assets.prev_close = {beklenen} (kapanistan geldi)")
        else:
            sonuc = _hata(f"prev_close guncellenmedi: {yeni_prev}")

        if test_gunu not in await repo.pending_close_days():
            _basari("test gunu artik bekleyenler listesinde degil")
        else:
            sonuc = _hata("gun hala bekleyenler listesinde")

        print()
        print("SONUC: GUN DEVRI CALISIYOR." if sonuc else "SONUC: SORUN VAR (yukari bakin).")
        return 0 if sonuc else 4

    finally:
        # --- 5) Her seyi geri al --------------------------------------
        print("\n[5] TEMIZLIK")
        await calistir(
            "DELETE FROM live_prices WHERE created_at < CAST(:g AS DATE) + 1", {"g": test_gunu}
        )
        await calistir(
            """
            DELETE FROM price_history WHERE asset_id = :a
              AND ts = CAST(CAST(:g AS DATE) AS TIMESTAMP) AT TIME ZONE CAST(:tz AS TEXT)
            """,
            {"a": aid, "g": test_gunu, "tz": tz},
        )
        await calistir(
            "UPDATE assets SET prev_close = :pc, current_price = :cp, daily_change_pct = :d "
            "WHERE id = :a",
            {
                "pc": varlik["prev_close"],
                "cp": varlik["current_price"],
                "d": varlik["daily_change_pct"],
                "a": aid,
            },
        )
        print(f"{TAMAM} test verisi silindi, {TEST_SEMBOL} eski haline donduruldu")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
