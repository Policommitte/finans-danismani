"""`price_history`'deki simule satirlarin ZAMANLAMASINI cozer - SALT OKUR.

Kullanim (backend/ klasorunun ICINDEN):

    python simule-analiz.py

Cevapladigi soru
----------------
Simule satirlar hangi araliklarla yazilmis? 60 sn ise biri backend'i
`PRICE_TICK_SECONDS=60` ile calistirmis (eski .env degeri); 900 sn ise
varsayilan ayarla calistirmis ve sorun tick araligi degil, simulatore
DUSULMESI.

Hicbir sey yazmaz, yalnizca SELECT calistirir.
"""

from __future__ import annotations

import asyncio
import sys

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
        print("HATA: veritabanina baglanilamadi. backend/ icinden calistirin.")
        return 1

    fabrika = get_session_factory()

    async def sorgu(sql: str) -> list[dict]:
        async with fabrika() as oturum:
            sonuc = await oturum.execute(text(sql))
            return [dict(s) for s in sonuc.mappings().all()]

    # --- 1) Genel tablo --------------------------------------------------
    print("=== price_history: KAYNAK OZETI ===")
    for s in await sorgu(
        """
        SELECT source, count(*) AS adet,
               min(ts) AT TIME ZONE 'Europe/Istanbul' AS ilk,
               max(ts) AT TIME ZONE 'Europe/Istanbul' AS son,
               count(DISTINCT asset_id) AS varlik
        FROM price_history GROUP BY source ORDER BY 2 DESC
        """
    ):
        print(f"  source={s['source']:<12} {s['adet']:>6} satir  {s['varlik']:>3} varlik")
        print(f"  {'':<19} {s['ilk']}  ->  {s['son']}   (TR saati)")

    # --- 2) Simule satirlarin araliklari ---------------------------------
    print("\n=== SIMULE SATIRLAR ARASI ARALIK (tek varlik uzerinden) ===")
    araliklar = await sorgu(
        """
        SELECT saniye, count(*) AS kac_kez FROM (
            SELECT EXTRACT(EPOCH FROM (ts - lag(ts) OVER (ORDER BY ts)))::INT AS saniye
            FROM price_history
            WHERE source = 'simulated'
              AND asset_id = (SELECT asset_id FROM price_history
                               WHERE source='simulated' GROUP BY asset_id
                               ORDER BY count(*) DESC LIMIT 1)
        ) t
        WHERE saniye IS NOT NULL
        GROUP BY saniye ORDER BY kac_kez DESC LIMIT 10
        """
    )
    if not araliklar:
        print("  (simule satir yok)")
    else:
        print(f"  {'aralik':>10}  {'kac kez':>8}   yorum")
        for a in araliklar:
            sn = a["saniye"]
            if sn <= 90:
                yorum = f"~{sn} sn  <-- DAKIKALIK! PRICE_TICK_SECONDS=60 ile calistirilmis"
            elif 840 <= sn <= 960:
                yorum = "~15 dk  (varsayilan PRICE_TICK_SECONDS=900)"
            elif sn > 3600:
                yorum = f"~{sn // 3600} saat (backend kapali kalmis)"
            else:
                yorum = f"~{sn // 60} dk"
            print(f"  {sn:>10}  {a['kac_kez']:>8}   {yorum}")

    # --- 3) Gunluk dagilim -----------------------------------------------
    print("\n=== SIMULE SATIRLARIN GUNLERE DAGILIMI (TR saati) ===")
    for s in await sorgu(
        """
        SELECT CAST(ts AT TIME ZONE 'Europe/Istanbul' AS DATE) AS gun,
               count(*) AS adet, count(DISTINCT asset_id) AS varlik,
               min(ts) AT TIME ZONE 'Europe/Istanbul' AS ilk,
               max(ts) AT TIME ZONE 'Europe/Istanbul' AS son
        FROM price_history WHERE source='simulated'
        GROUP BY 1 ORDER BY 1
        """
    ):
        varlik_basi = s["adet"] // max(s["varlik"], 1)
        print(
            f"  {s['gun']}  {s['adet']:>5} satir  ({s['varlik']} varlik x ~{varlik_basi})  "
            f"{str(s['ilk'])[11:16]} - {str(s['son'])[11:16]}"
        )

    # --- 4) live_prices tarafinda durum ----------------------------------
    print("\n=== live_prices (yeni tablo) ===")
    for s in (
        await sorgu(
            """
        SELECT source, count(*) AS adet,
               min(created_at) AT TIME ZONE 'Europe/Istanbul' AS ilk,
               max(created_at) AT TIME ZONE 'Europe/Istanbul' AS son
        FROM live_prices GROUP BY source ORDER BY 2 DESC
        """
        )
        or [{"source": "(bos)", "adet": 0, "ilk": None, "son": None}]
    ):
        print(f"  source={s['source']:<12} {s['adet']:>6} satir   {s['ilk']} -> {s['son']}")

    # --- 5) Gun ici kirlilik ---------------------------------------------
    # Gercek gunluk kapanislar TAM SAATE oturur (BIST 00:00, kripto 03:00 TR).
    # Gun ici tick'ler `date_trunc('second', now())` ile yazildigi icin
    # rastgele dakika/saniye tasir. Ayrim bu kadar net.
    print("\n=== price_history'DEKI GUN ICI KIRLILIK (kapanis olmayan satirlar) ===")
    kirli = await sorgu(
        """
        SELECT CAST(ts AT TIME ZONE 'Europe/Istanbul' AS DATE) AS gun,
               source, count(*) AS adet,
               min(ts) AT TIME ZONE 'Europe/Istanbul' AS ilk,
               max(ts) AT TIME ZONE 'Europe/Istanbul' AS son
        FROM price_history
        WHERE (EXTRACT(minute FROM ts) <> 0 OR EXTRACT(second FROM ts) <> 0)
          -- 'backfill' toplu ve bilincli bir yukleme; kirlilik fiyat
          -- gorevinden gelir, yani 'api' / 'simulated' etiketlilerden.
          AND source IN ('api', 'simulated')
        GROUP BY 1, 2 ORDER BY 1 DESC, 3 DESC LIMIT 15
        """
    )
    if not kirli:
        print("  (yok - price_history'de yalnizca gunluk kapanislar var)")
    else:
        print(f"  {'gun':<12} {'source':<11} {'adet':>7}   {'ilk':<9} {'son':<9}")
        for k in kirli:
            print(
                f"  {str(k['gun']):<12} {k['source']:<11} {k['adet']:>7}   "
                f"{str(k['ilk'])[11:19]:<9} {str(k['son'])[11:19]:<9}"
            )
        print("  ^ Bu satirlar gun ici tick; yeni tasarimda live_prices'a gitmeliydiler.")
        print("    PR #19 oncesi bir checkout'tan yaziliyorlar.")

    # --- 6) Su an veritabanina bagli olanlar -------------------------------
    # Eski kodu kimin calistirdigini bulmanin en hizli yolu.
    print("\n=== SU AN BAGLI ISTEMCILER ===")
    try:
        istemciler = await sorgu(
            """
            SELECT COALESCE(NULLIF(application_name, ''), '(isimsiz)') AS uygulama,
                   COALESCE(host(client_addr), '(pooler)') AS adres,
                   state, count(*) AS adet,
                   min(backend_start) AT TIME ZONE 'Europe/Istanbul' AS en_eski
            FROM pg_stat_activity
            WHERE datname = current_database() AND pid <> pg_backend_pid()
            GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 15
            """
        )
        if not istemciler:
            print("  (baska bagli istemci yok)")
        for i in istemciler:
            print(
                f"  {i['uygulama']:<24} {i['adres']:<16} {str(i['state'] or '-'):<12} "
                f"{i['adet']:>3} baglanti   basladi: {str(i['en_eski'])[:16]}"
            )
    except Exception as exc:  # pragma: no cover - yetki yoksa
        print(f"  (okunamadi: {type(exc).__name__})")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
