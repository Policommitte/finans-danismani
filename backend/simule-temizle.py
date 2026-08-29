"""`source='simulated'` satirlarini siler - baska HICBIR SEYE dokunmaz.

Kullanim (backend/ klasorunun ICINDEN):

    python simule-temizle.py            # SADECE RAPOR - hicbir sey silmez
    python simule-temizle.py --uygula   # simule satirlari siler

Neden gerekli
-------------
20 Agustos 2026'da `PRICE_TICK_SECONDS=60` ayarli bir ornek gunluk Yahoo
kotasini ~2,6 saatte doldurdu; sonrasinda saglayici simulatore dustu ve gunun
kalani sahte fiyatla yazildi. Etiket dogruydu (`source='simulated'`) ama sahte
veri tarihcenin icindeydi: grafik sahte noktalarla karisik ciziliyor ve
`weekly_change_pct` 7 gun onceki satir olarak bir simule tick yakalarsa yanlis
cikiyor.

Kod tarafi artik kapali (bkz. `app/market/scheduler.py` ->
YAZILABILIR_KAYNAKLAR): simule fiyat veritabanina hicbir yoldan giremiyor.
Ama gecmisteki kirlilik kendiliginden temizlenmez.

Guvenlik
--------
* Yalnizca `source = 'simulated'` satirlarina dokunur. `api` ve `backfill`
  satirlari - yani gercek verinin tamami - ETKILENMEZ.
* Varsayilan calisma DENEME modudur; `--uygula` verilmeden tek satir silinmez.
* Silmeden ONCE ne silinecegini sayar ve gosterir, silmeden SONRA kalan
  dagilimi tekrar okur.
* `users`, portfoy, sohbet, RAG tablolarina hic bakmaz.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

# WINDOWS: psycopg'nin async surucusu varsayilan ProactorEventLoop ile
# calismaz (ayni duzeltme uygulama tarafinda `run.py` icinde).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main(uygula: bool) -> int:
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

    def _dagilim_yaz(baslik: str, satirlar: list[dict]) -> None:
        print(f"  {baslik}")
        if not satirlar:
            print("    (tablo bos)")
            return
        for s in satirlar:
            print(f"    source={s['source']:<12} {s['adet']:>7} satir")

    ph_sql = "SELECT source, count(*) AS adet FROM price_history GROUP BY source ORDER BY 2 DESC"
    lp_sql = "SELECT source, count(*) AS adet FROM live_prices GROUP BY source ORDER BY 2 DESC"

    print("=== MEVCUT DURUM ===")
    _dagilim_yaz("price_history:", await sorgu(ph_sql))
    _dagilim_yaz("live_prices:", await sorgu(lp_sql))

    silinecek = (
        await sorgu(
            """
            SELECT
              (SELECT count(*) FROM price_history WHERE source = 'simulated') AS ph,
              (SELECT count(*) FROM live_prices   WHERE source = 'simulated') AS lp
            """
        )
    )[0]
    toplam = int(silinecek["ph"]) + int(silinecek["lp"])

    print("\n=== SILINECEK ===")
    print(f"  price_history  source='simulated'  {silinecek['ph']:>7} satir")
    print(f"  live_prices    source='simulated'  {silinecek['lp']:>7} satir")
    print(f"  {'TOPLAM':<34} {toplam:>7} satir")

    if toplam == 0:
        print("\nSONUC: silinecek simule satir yok. Yapacak bir sey yok.")
        return 0

    if not uygula:
        print("\nDENEME MODU - hicbir sey silinmedi.")
        print("Silmek icin:  python simule-temizle.py --uygula")
        return 3

    print("\nSiliniyor...")
    async with fabrika() as oturum:
        ph_sonuc = await oturum.execute(
            text("DELETE FROM price_history WHERE source = 'simulated'")
        )
        lp_sonuc = await oturum.execute(text("DELETE FROM live_prices WHERE source = 'simulated'"))
        await oturum.commit()
    print(f"  price_history: {ph_sonuc.rowcount} satir silindi")
    print(f"  live_prices  : {lp_sonuc.rowcount} satir silindi")

    print("\n=== SONRAKI DURUM ===")
    ph_son = await sorgu(ph_sql)
    lp_son = await sorgu(lp_sql)
    _dagilim_yaz("price_history:", ph_son)
    _dagilim_yaz("live_prices:", lp_son)

    kalan = [s for s in ph_son + lp_son if s["source"] == "simulated"]
    if kalan:
        print("\nSONUC: hala simule satir var (silme eksik kaldi).")
        return 4

    print("\nSONUC: TAMAM. Gercek veri (api / backfill) oldugu gibi duruyor.")
    return 0


if __name__ == "__main__":
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument(
        "--uygula", action="store_true", help="Gercekten sil (varsayilan: deneme)"
    )
    args = ayristirici.parse_args()
    sys.exit(asyncio.run(main(uygula=args.uygula)))
