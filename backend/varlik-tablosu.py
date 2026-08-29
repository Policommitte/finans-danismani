"""`assets` tablosunu okunakli bicimde gosterir - SALT OKUR.

Kullanim (backend/ klasorunun ICINDEN):

    python varlik-tablosu.py

Ne gosterir
-----------
1. `assets` satirlari: guncel fiyat, prev_close, gunluk/haftalik degisim ve
   fiyatin en son ne zaman guncellendigi.
2. Her varlik icin gun ici durum: bugun `live_prices`'a kac satir yazilmis,
   sonuncusu saat kacta, ve `price_history`'deki son kapanis hangi gune ait.

Ikinci tablo "hangi varlik guncelleniyor, hangisi takilmis" sorusunu tek
bakista cevaplar. Hicbir sey yazmaz, yalnizca SELECT calistirir.
"""

from __future__ import annotations

import asyncio
import sys

# WINDOWS: psycopg'nin async surucusu varsayilan ProactorEventLoop ile
# calismaz (ayni duzeltme uygulama tarafinda `run.py` icinde).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Varlik adlari Turkce karakter iceriyor ("Türk Hava Yollari"). Windows
# konsolunun varsayilan kod sayfasi bunlari bozuk gosterir; UTF-8'e cevirip
# desteklemeyen terminalde de patlamamasi icin errors="replace" veriyoruz.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - eski/farkli terminaller
    pass

TZ = "Europe/Istanbul"


def _sayi(deger, basamak: int = 4) -> str:
    if deger is None:
        return "-"
    return f"{float(deger):,.{basamak}f}"


def _yuzde(deger) -> str:
    if deger is None:
        return "-"
    return f"{float(deger):+.2f}"


def _saat(deger) -> str:
    return "-" if deger is None else str(deger)[:16]


async def main() -> int:
    try:
        from sqlalchemy import text

        from app.db.session import get_session_factory
        from app.repositories.deps import describe_backend
    except Exception as exc:  # pragma: no cover
        print(f"HATA: modul yuklenemedi ({exc}). backend/ icinden calistirin.")
        return 1

    if describe_backend() != "postgresql":
        print("HATA: veritabanina baglanilamadi (bellek ici yedege dusuldu).")
        print("      backend/.env icindeki DATABASE_URL'i kontrol edin ve")
        print("      komutu backend/ klasorunun ICINDEN calistirin.")
        return 1

    fabrika = get_session_factory()

    async def sorgu(sql: str, params: dict | None = None) -> list[dict]:
        async with fabrika() as oturum:
            sonuc = await oturum.execute(text(sql), params or {})
            return [dict(s) for s in sonuc.mappings().all()]

    # --- 1) assets ------------------------------------------------------
    satirlar = await sorgu(
        """
        SELECT a.id, a.symbol, a.name, ac.code AS sinif, a.currency,
               a.current_price, a.prev_close, a.daily_change_pct,
               a.weekly_change_pct, a.yearly_change_pct,
               a.price_updated_at AT TIME ZONE CAST(:tz AS TEXT) AS guncelleme
        FROM assets a
        LEFT JOIN asset_categories ac ON ac.id = a.category_id
        ORDER BY ac.code, a.symbol
        """,
        {"tz": TZ},
    )
    if not satirlar:
        print("assets tablosu BOS.")
        return 2

    print(f"=== assets ({len(satirlar)} varlik) ===")
    baslik = (
        f"  {'id':>3} {'sembol':<11} {'ad':<22} {'sinif':<10} {'kur':<4} "
        f"{'guncel':>13} {'prev_close':>13} {'gun%':>7} {'hafta%':>8}  {'guncelleme (TR)':<16}"
    )
    print(baslik)
    print("  " + "-" * (len(baslik) - 2))
    for s in satirlar:
        print(
            f"  {s['id']:>3} {s['symbol']:<11} {(s['name'] or '')[:22]:<22} "
            f"{(s['sinif'] or '-'):<10} {(s['currency'] or '-'):<4} "
            f"{_sayi(s['current_price']):>13} {_sayi(s['prev_close']):>13} "
            f"{_yuzde(s['daily_change_pct']):>7} {_yuzde(s['weekly_change_pct']):>8}  "
            f"{_saat(s['guncelleme']):<16}"
        )

    # --- 2) Gun ici durum ------------------------------------------------
    print("\n=== VARLIK BASINA GUN ICI DURUM ===")
    durum = await sorgu(
        """
        SELECT a.symbol,
               (SELECT count(*) FROM live_prices lp
                 WHERE lp.asset_id = a.id
                   AND lp.created_at >= (
                       date_trunc('day', now() AT TIME ZONE CAST(:tz AS TEXT))
                   ) AT TIME ZONE CAST(:tz AS TEXT)) AS bugun_canli,
               (SELECT max(lp.created_at) AT TIME ZONE CAST(:tz AS TEXT)
                  FROM live_prices lp WHERE lp.asset_id = a.id) AS son_canli,
               (SELECT max(ph.ts) AT TIME ZONE CAST(:tz AS TEXT)
                  FROM price_history ph WHERE ph.asset_id = a.id) AS son_kapanis
        FROM assets a ORDER BY a.symbol
        """,
        {"tz": TZ},
    )
    baslik2 = (
        f"  {'sembol':<11} {'bugun live_prices':>18}  {'son canli (TR)':<17} "
        f"{'son price_history (TR)':<22}"
    ).rstrip()
    print(baslik2)
    print("  " + "-" * (len(baslik2) - 2))
    for s in durum:
        print(
            f"  {s['symbol']:<11} {s['bugun_canli']:>18}  {_saat(s['son_canli']):<17} "
            f"{_saat(s['son_kapanis']):<22}"
        )

    guncellenmeyen = [s["symbol"] for s in durum if s["bugun_canli"] == 0]
    if guncellenmeyen:
        print(f"\n  NOT: bugun hic canli fiyat yazilmayan varlik: {', '.join(guncellenmeyen)}")
        print("       (fiyat gorevi kapaliysa ya da Yahoo'da karsiligi yoksa normaldir)")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
