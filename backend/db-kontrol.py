"""Veritabani baglantisi ve sema kontrolu - TEK SEFERLIK TESHIS BETIGI.

Repoya eklenmesi gerekmez; sorunu bulunca silebilirsiniz.

Kullanim (backend/ klasorunun icinden):

    python db-kontrol.py
        -> backend/.env icindeki DATABASE_URL kullanilir

    python db-kontrol.py "postgresql://kullanici:parola@host:5432/postgres"
        -> verilen URL kullanilir (parolayi ekranda gostermez)

Ne yapar:
  1. Baglanabiliyor mu?
  2. Backend'in ihtiyac duydugu tablolar var mi?
  3. `assets` tablosunda backend'in YAZDIGI kolonlar var mi?
     (eksikse fiyat gorevi her tick'te sessizce patlar)
  4. Tablolarda kac satir var? (bos DB de "calisiyor" gorunur)
"""

from __future__ import annotations

import sys

# Backend'in `assets` uzerinde OKUDUGU/YAZDIGI kolonlar.
# Kaynak: app/repositories/sql.py -> get_prices_for_simulation / apply_price_updates
ASSETS_ZORUNLU = [
    "id",
    "symbol",
    "name",
    "currency",
    "current_price",
    "prev_close",  # apply_price_updates: SET prev_close = ...
    "daily_change_pct",
    "weekly_change_pct",
    "yearly_change_pct",
    "sim_volatility",  # get_prices_for_simulation: SELECT ... sim_volatility
    "price_updated_at",  # apply_price_updates: SET price_updated_at = now()
    "category_id",
]

TABLOLAR = [
    "users",
    "asset_categories",
    "assets",
    "portfolios",
    "portfolio_assets",
    "transactions",
    "price_history",
    "market_api_usage",
    "chat_sessions",
    "chat_messages",
    "tool_calls",
    "security_events",
]

GORUNUMLER = [
    "v_fx_rates",
    "v_holdings_valued",
    "v_portfolio_summary",
    "v_portfolio_allocation",
]


def _dsn_al() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].strip()

    try:
        from app.config import settings
    except Exception as exc:
        print(f"HATA: app.config okunamadi ({exc}). backend/ icinden calistirin.")
        sys.exit(1)

    url = settings.database_url.strip()
    if not url:
        print("HATA: DATABASE_URL bos.")
        print("      -> backend/.env dosyasina yazin VE komutu backend/ icinden calistirin.")
        sys.exit(1)
    return url


def _senkron(url: str) -> str:
    for onek in ("postgresql+psycopg://", "postgresql+asyncpg://"):
        if url.startswith(onek):
            return url.replace(onek, "postgresql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def main() -> int:
    import psycopg

    dsn = _senkron(_dsn_al())

    # Parolayi ekranda gosterme.
    gorunur = dsn
    if "@" in dsn and "//" in dsn:
        bas, son = dsn.split("//", 1)
        kimlik, host = son.split("@", 1)
        kullanici = kimlik.split(":", 1)[0]
        gorunur = f"{bas}//{kullanici}:***@{host}"
    print(f"Baglanti: {gorunur}\n")

    try:
        conn = psycopg.connect(dsn, connect_timeout=10)
    except Exception as exc:
        print(f"[1] BAGLANTI  : BASARISIZ -> {type(exc).__name__}: {exc}")
        print("\n    Bu durumda backend hata VERMEZ, bellek ici sahte veriye duser")
        print("    ve /health 'in-memory' doner. Once bunu duzeltin.")
        return 1

    print("[1] BAGLANTI  : OK")
    sema_eksik = 0
    veri_eksik = 0

    with conn, conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, version()")
        db, kullanici, surum = cur.fetchone()
        print(f"    veritabani={db} kullanici={kullanici}")
        print(f"    {surum.split(',')[0]}\n")

        # --- tablolar ---
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        mevcut = {r[0] for r in cur.fetchall()}
        eksik_tablo = [t for t in TABLOLAR if t not in mevcut]
        print(f"[2] TABLOLAR  : {len(TABLOLAR) - len(eksik_tablo)}/{len(TABLOLAR)}")
        if eksik_tablo:
            print(f"    EKSIK: {', '.join(eksik_tablo)}")
            sema_eksik += 1

        # --- gorunumler ---
        cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema = 'public'")
        gorunum_var = {r[0] for r in cur.fetchall()}
        eksik_gorunum = [g for g in GORUNUMLER if g not in gorunum_var]
        print(f"[3] VIEW'LAR  : {len(GORUNUMLER) - len(eksik_gorunum)}/{len(GORUNUMLER)}")
        if eksik_gorunum:
            print(f"    EKSIK: {', '.join(eksik_gorunum)}  -> portfoy uclari 500 verir")
            sema_eksik += 1

        # --- assets kolonlari ---
        if "assets" in mevcut:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'assets'"
            )
            kolonlar = {r[0] for r in cur.fetchall()}
            eksik_kolon = [k for k in ASSETS_ZORUNLU if k not in kolonlar]
            print(
                f"[4] assets KOLONLARI: {len(ASSETS_ZORUNLU) - len(eksik_kolon)}/{len(ASSETS_ZORUNLU)}"
            )
            if eksik_kolon:
                print(f"    EKSIK: {', '.join(eksik_kolon)}")
                print("    -> Fiyat gorevi her tick'te 'UndefinedColumn' ile SESSIZCE patlar.")
                sema_eksik += 1
        else:
            print("[4] assets KOLONLARI: tablo yok, atlandi")

        # --- satir sayilari ---
        print("[5] SATIR SAYILARI:")
        for tablo in ("users", "assets", "price_history", "portfolios", "portfolio_assets"):
            if tablo not in mevcut:
                continue
            cur.execute(f"SELECT count(*) FROM {tablo}")  # noqa: S608 - sabit liste
            print(f"    {tablo:<18} {cur.fetchone()[0]:>8}")

        rag_bos = False
        for tam_ad in ("rag.documents", "rag.chunks"):
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", (tam_ad,))
            if not cur.fetchone()[0]:
                print(f"    {tam_ad:<18}      YOK")
                sema_eksik += 1
                continue
            cur.execute(f"SELECT count(*) FROM {tam_ad}")  # noqa: S608 - sabit liste
            adet = cur.fetchone()[0]
            print(f"    {tam_ad:<18} {adet:>8}")
            if adet == 0:
                rag_bos = True
        if rag_bos:
            print("    ^ RAG indeksi BOS -> /api/market/search bos doner, sohbet")
            print("      yanitlarinda kaynak gosterilmez, MarketResearchAgent'in")
            print("      RAG yolu her zaman 'icerik bulunamadi' der.")
            veri_eksik += 1

        # --- fiyat gecmisi: kaynak dagilimi ve tarih araligi ---
        if "price_history" in mevcut:
            print("[6] price_history DETAYI:")
            cur.execute("SELECT min(ts)::date, max(ts)::date FROM price_history")
            ilk, son = cur.fetchone()
            print(f"    tarih araligi      {ilk} .. {son}")
            cur.execute(
                "SELECT source, count(*) FROM price_history GROUP BY source ORDER BY 2 DESC"
            )
            for kaynak, adet in cur.fetchall():
                print(f"    source={kaynak:<12} {adet:>8}")

        # --- Yahoo eslemesi olmayan varliklar ---
        if "assets" in mevcut:
            cur.execute("SELECT symbol FROM assets ORDER BY symbol")
            print("[7] VARLIKLAR: " + ", ".join(r[0] for r in cur.fetchall()))

    print()
    if sema_eksik:
        print(f"SONUC: SEMA EKSIK ({sema_eksik} kalem).")
        print("       db/v5_schema_and_data.sql yuklenmeli.")
        print("       ⚠️ DIKKAT: o dosya bastaki DROP blokuyla MEVCUT VERIYI SILER.")
        print("       Veritabaninda gercek veri varsa ONCE YEDEK ALIN.")
    elif veri_eksik:
        print(f"SONUC: Sema TAM, ama {veri_eksik} yerde VERI eksik.")
        print("       ⚠️ Sema dosyasini YENIDEN YUKLEMEYIN - bastaki DROP blogu")
        print("       mevcut gercek veriyi de siler. Eksik olan veriyi ilgili")
        print("       betikle/ekiple ayrica doldurun.")
    else:
        print("SONUC: Sema ve veri tam gorunuyor.")
    return 0 if not (sema_eksik or veri_eksik) else 2


if __name__ == "__main__":
    sys.exit(main())
