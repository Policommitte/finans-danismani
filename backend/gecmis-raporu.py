"""`price_history` yogunluk raporu - SALT OKUR, hicbir sey yazmaz.

Kullanim (backend/ klasorunun ICINDEN):

    python gecmis-raporu.py

Ne gosterir
-----------
1. Yil x kaynak kirilimi: hangi yilda kac satir, hangi etiketle.
2. Varlik bazinda aralik, satir sayisi ve ORTALAMA GUN ARALIGI - "gunluk mu
   yoksa aylik mi" sorusunun cevabi budur (1'e yakinsa gunluk, 20-30 ise
   aylik).
3. En buyuk bosluklar: iki ardisik kayit arasindaki en uzun sureler.

Betik yalnizca SELECT calistirir; INSERT/UPDATE/DELETE yoktur.
"""

from __future__ import annotations

import asyncio
import sys

# WINDOWS: psycopg'nin async surucusu varsayilan ProactorEventLoop ile
# calismaz (ayni duzeltme uygulama tarafinda `run.py` icinde).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


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

    async def sorgu(sql: str) -> list[dict]:
        async with fabrika() as oturum:
            sonuc = await oturum.execute(text(sql))
            return [dict(s) for s in sonuc.mappings().all()]

    # --- 1) Yil x kaynak --------------------------------------------------
    print("=== YIL x KAYNAK ===")
    satirlar = await sorgu(
        """
        SELECT CAST(date_part('year', ts) AS INT) AS yil, source, count(*) AS adet
        FROM price_history GROUP BY 1, 2 ORDER BY 1, 2
        """
    )
    if not satirlar:
        print("  price_history BOS.")
        return 0

    print(f"  {'yil':<6} {'kaynak':<12} {'satir':>8}")
    for s in satirlar:
        print(f"  {s['yil']:<6} {s['source']:<12} {s['adet']:>8}")

    toplam = sum(s["adet"] for s in satirlar)
    print(f"  {'TOPLAM':<19} {toplam:>8}")

    # --- 2) Varlik bazinda yogunluk --------------------------------------
    # ortalama gun araligi = kapsanan gun sayisi / (kayit sayisi - 1)
    # 1'e yakin  -> gunluk seri
    # 5'e yakin  -> is gunu bazli ama eksikli
    # 20-30      -> aylik
    print("\n=== VARLIK BAZINDA YOGUNLUK ===")
    print(
        f"  {'sembol':<12} {'ilk':<12} {'son':<12} {'satir':>7} "
        f"{'ort.gun':>8}  {'son 90 gun':>10}"
    )
    satirlar = await sorgu(
        """
        SELECT a.symbol,
               CAST(min(ph.ts) AS DATE) AS ilk,
               CAST(max(ph.ts) AS DATE) AS son,
               count(*) AS adet,
               CASE WHEN count(*) > 1
                    THEN ROUND((CAST(max(ph.ts) AS DATE) - CAST(min(ph.ts) AS DATE))::NUMERIC
                               / (count(*) - 1), 1)
               END AS ort_gun,
               count(*) FILTER (WHERE ph.ts >= now() - INTERVAL '90 days') AS son90
        FROM price_history ph
        JOIN assets a ON a.id = ph.asset_id
        GROUP BY a.symbol ORDER BY a.symbol
        """
    )
    for s in satirlar:
        ort = "-" if s["ort_gun"] is None else f"{s['ort_gun']}"
        print(
            f"  {s['symbol']:<12} {str(s['ilk']):<12} {str(s['son']):<12} "
            f"{s['adet']:>7} {ort:>8}  {s['son90']:>10}"
        )

    # --- 3) En buyuk bosluklar -------------------------------------------
    print("\n=== EN BUYUK BOSLUKLAR (ardisik iki kayit arasi) ===")
    satirlar = await sorgu(
        """
        SELECT symbol, CAST(onceki AS DATE) AS baslangic, CAST(ts AS DATE) AS bitis,
               CAST(ts AS DATE) - CAST(onceki AS DATE) AS gun
        FROM (
            SELECT a.symbol, ph.ts,
                   lag(ph.ts) OVER (PARTITION BY ph.asset_id ORDER BY ph.ts) AS onceki
            FROM price_history ph JOIN assets a ON a.id = ph.asset_id
        ) t
        WHERE onceki IS NOT NULL
        ORDER BY gun DESC LIMIT 10
        """
    )
    for s in satirlar:
        print(f"  {s['symbol']:<12} {s['baslangic']} -> {s['bitis']}   {s['gun']:>4} gun")

    print("\nYORUM: 'ort.gun' 1-2 ise gunluk seri, 5 civari ise is gunu bazli,")
    print("       20-30 ise aylik demektir. Ayni varlikta yillar arasi buyuk")
    print("       fark varsa geriye donuk backfill farkli cozunurlukte cekilmis.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
