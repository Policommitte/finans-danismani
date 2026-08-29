"""`live_prices` tablosunun gercek yapisini gosterir - TEK SEFERLIK.

Kullanim (backend/ klasorunun icinden):

    python live-prices-bilgi.py

Ciktida parola gosterilmez. Sonucu paylasabilirsiniz.
"""

from __future__ import annotations

import sys


def _dsn() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].strip()
    try:
        from app.config import settings
    except Exception as exc:
        print(f"HATA: app.config okunamadi ({exc}). backend/ icinden calistirin.")
        sys.exit(1)
    url = settings.database_url.strip()
    if not url:
        print("HATA: DATABASE_URL bos (backend/.env).")
        sys.exit(1)
    for onek in ("postgresql+psycopg://", "postgresql+asyncpg://"):
        if url.startswith(onek):
            return url.replace(onek, "postgresql://", 1)
    return url.replace("postgres://", "postgresql://", 1)


def main() -> int:
    import psycopg

    with psycopg.connect(_dsn(), connect_timeout=15) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.live_prices') IS NOT NULL")
        if not cur.fetchone()[0]:
            print("live_prices tablosu BULUNAMADI (public seması).")
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name ILIKE '%%live%%'"
            )
            benzer = [r[0] for r in cur.fetchall()]
            print("Benzer isimli tablolar:", benzer or "yok")
            return 1

        print("=== KOLONLAR ===")
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='live_prices'
            ORDER BY ordinal_position
            """
        )
        for ad, tip, nullable, varsayilan in cur.fetchall():
            v = f" DEFAULT {varsayilan}" if varsayilan else ""
            print(f"  {ad:<22} {tip:<28} {'NULL' if nullable == 'YES' else 'NOT NULL'}{v}")

        print("\n=== KISITLAR (PK / UNIQUE / FK / CHECK) ===")
        cur.execute(
            """
            SELECT con.conname, pg_get_constraintdef(con.oid)
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace ns ON ns.oid = rel.relnamespace
            WHERE ns.nspname='public' AND rel.relname='live_prices'
            ORDER BY con.contype
            """
        )
        satirlar = cur.fetchall()
        for ad, tanim in satirlar:
            print(f"  {ad}: {tanim}")
        if not satirlar:
            print("  (hic kisit yok - PK bile yok)")

        print("\n=== INDEKSLER ===")
        cur.execute(
            "SELECT indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='live_prices'"
        )
        idx = [r[0] for r in cur.fetchall()]
        print("\n".join(f"  {i}" for i in idx) if idx else "  (indeks yok)")

        print("\n=== ICERIK ===")
        cur.execute("SELECT count(*) FROM live_prices")
        adet = cur.fetchone()[0]
        print(f"  satir sayisi: {adet}")
        if adet:
            cur.execute("SELECT * FROM live_prices ORDER BY 1 LIMIT 3")
            kolonlar = [d.name for d in cur.description]
            print(f"  ornek satirlar ({', '.join(kolonlar)}):")
            for satir in cur.fetchall():
                print("   ", satir)

        print("\n=== price_history KOLONLARI (karsilastirma icin) ===")
        cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='price_history' ORDER BY ordinal_position"
        )
        for ad, tip in cur.fetchall():
            print(f"  {ad:<22} {tip}")

        print("\n=== SUNUCU ZAMANI ===")
        cur.execute("SHOW timezone")
        tz = cur.fetchone()[0]
        cur.execute("SELECT now(), current_date")
        simdi, bugun = cur.fetchone()
        print(f"  timezone={tz}  now()={simdi}  current_date={bugun}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
