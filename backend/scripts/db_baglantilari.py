"""Supabase/PostgreSQL uzerindeki ACIK BAGLANTILARI listeler (salt okunur).

NEDEN VAR: ekip tek bir Supabase ornegini paylasiyor ve session pooler'inda
TOPLAM 25 slot var (bkz. `.env.example` - "Veritabani baglanti havuzu").
Slotlar dolunca backend sessizce bellek ici veriye duser: sayfalar acilir
ama portfoy/risk/likit para BOS gorunur. Bu betik "slotu kim tutuyor"
sorusunu cevaplar.

KULLANIM (backend venv'i acikken):

    python backend/scripts/db_baglantilari.py
    python backend/scripts/db_baglantilari.py --hepsi        # tum veritabanlari
    python backend/scripts/db_baglantilari.py --json         # makine okunur
    python backend/scripts/db_baglantilari.py --dsn "postgresql://..."

NEDEN `app.db.session` KULLANILMIYOR: o modul bir HAVUZ acar (DB_POOL_SIZE
kadar baglanti), yani sorunu olcerken sorunu buyutur. Burada tek bir
dogrudan baglanti acilir ve is bitince kapatilir.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - kurulum uyarisi
    print("psycopg kurulu degil. Backend venv'ini acin: pip install 'psycopg[binary]'")
    raise SystemExit(2) from None

#: Bu betigin kendi baglantisi listede boyle gorunur (ve kesme betiginde
#: bilerek atlanir).
UYGULAMA_ADI = "polifin-ops-liste"

LISTE_SQL = r"""
SELECT
    pid,
    COALESCE(usename, '-')                                     AS kullanici,
    COALESCE(NULLIF(application_name, ''), '-')                AS uygulama,
    COALESCE(host(client_addr), 'local')                       AS istemci,
    COALESCE(datname, '-')                                     AS veritabani,
    COALESCE(state, backend_type)                              AS durum,
    backend_type                                               AS tur,
    EXTRACT(EPOCH FROM (now() - backend_start))::int           AS yas_sn,
    EXTRACT(EPOCH FROM (now() - state_change))::int            AS durum_sn,
    EXTRACT(EPOCH FROM (now() - xact_start))::int              AS islem_sn,
    COALESCE(wait_event_type || ':' || wait_event, '-')        AS bekleme,
    LEFT(REGEXP_REPLACE(COALESCE(query, ''), '\s+', ' ', 'g'), 70) AS sorgu,
    pid = pg_backend_pid()                                     AS ben
FROM pg_stat_activity
WHERE (%(hepsi)s OR datname = current_database())
ORDER BY (state = 'idle in transaction') DESC, backend_start
"""

OZET_SQL = """
SELECT
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS tavan,
    (SELECT count(*) FROM pg_stat_activity
      WHERE backend_type = 'client backend')                              AS istemci_toplam,
    (SELECT count(*) FROM pg_stat_activity
      WHERE backend_type = 'client backend'
        AND datname = current_database())                                 AS bu_vt,
    current_database()                                                    AS vt,
    current_user                                                          AS rol
"""


#: `backend/` klasoru - `app` paketi ve `.env` burada durur.
BACKEND_KOK = Path(__file__).resolve().parent.parent


def _kok_ekle() -> None:
    """`app` paketini import edebilmek icin backend kokunu sys.path'e ekler.

    `python scripts/db_baglantilari.py` calistirildiginda sys.path[0] betigin
    KENDI klasorudur (`scripts/`), `backend/` DEGIL - bu yuzden `import app`
    basarisiz olur. Kullaniciyi `python -m scripts...` yazmaya zorlamak
    yerine yolu burada duzeltiyoruz.
    """
    kok = str(BACKEND_KOK)
    if kok not in sys.path:
        sys.path.insert(0, kok)


def _env_dosyasindan_dsn() -> str:
    """`backend/.env` icinden DATABASE_URL'i dogrudan okur (yedek yol).

    `Settings(env_file=".env")` dosyayi CALISMA DIZININE gore arar; betik
    repo kokunden calistirilirsa `.env` bulunamaz ve `database_url` bos
    doner. Bu fonksiyon dosyayi betigin konumuna gore bulur, yani betik
    nereden calistirilirsa calistirilsin ayni sonucu verir.
    """
    dosya = BACKEND_KOK / ".env"
    if not dosya.exists():
        return ""
    for satir in dosya.read_text(encoding="utf-8", errors="replace").splitlines():
        satir = satir.strip()
        if satir.startswith("DATABASE_URL="):
            return satir.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def dsn_hazirla(url: str) -> str:
    """SQLAlchemy yazimini duz libpq DSN'ine cevirir.

    `.env`'deki DATABASE_URL `postgresql+psycopg://` ile yazilmis olabilir;
    psycopg bu on eki tanimaz.
    """
    for surucu in ("postgresql+psycopg", "postgresql+asyncpg", "postgres"):
        if url.startswith(surucu + "://"):
            return "postgresql://" + url.split("://", 1)[1]
    return url


def dsn_bul(verilen: str | None) -> str:
    """Baglanti dizesini bulur: --dsn > app.config > backend/.env."""
    if verilen:
        return dsn_hazirla(verilen)

    _kok_ekle()
    url = ""
    try:
        from app.config import settings

        url = settings.database_url.strip()
    except Exception as hata:  # noqa: BLE001 - amac cokmek degil, yedege dusmek
        # Genis yakalama BILINCLI: pydantic kurulu olmayabilir, `.env` bozuk
        # olabilir, `app` import zinciri baska bir sey isteyebilir. Bunlarin
        # hicbiri betigi durdurmamali - `.env` yedegi hala calisir.
        print(f"[i] app.config okunamadi ({type(hata).__name__}: {hata}); .env'e bakiliyor.")

    if not url:
        url = _env_dosyasindan_dsn()

    if not url:
        print(
            "DATABASE_URL bulunamadi.\n"
            f"  Bakilan yer : {BACKEND_KOK / '.env'}\n"
            "  Cozum       : baglanti dizesini elle verin, ornegin\n"
            '    python scripts/db_baglantilari.py --dsn "postgresql://kullanici:sifre@host:5432/postgres"'
        )
        raise SystemExit(2)
    return dsn_hazirla(url)


def pooler_uyarisi(dsn: str) -> str | None:
    """Pooler uzerinden baglaniliyorsa ne gordugumuz DEGISIR.

    Supavisor (`*.pooler.supabase.com`) arkasindayken `pg_stat_activity`
    gercek gelistirici baglantilarini degil, POOLER'in sunucu tarafi
    baglantilarini gosterir: `application_name` bos, istemci IP'si hep
    pooler'in kendisi olur. Slot kimde diye bakmak icin DOGRUDAN baglanti
    (`db.<ref>.supabase.co:5432`) gerekir.
    """
    host = (urlsplit(dsn).hostname or "").lower()
    if "pooler.supabase.com" in host:
        return (
            "POOLER UZERINDEN BAGLISINIZ (" + host + ").\n"
            "  Gorunen satirlar Supavisor'un sunucu baglantilaridir; hangi\n"
            "  gelistiricinin tuttugunu buradan goremezsiniz. Gercek sahipleri\n"
            "  gormek icin DOGRUDAN baglanti dizesini kullanin:\n"
            "    Supabase panosu > Project Settings > Database > Connection string\n"
            "    (Direct connection, db.<ref>.supabase.co:5432)"
        )
    return None


def sure(saniye: Any) -> str:
    if saniye is None:
        return "-"
    saniye = int(saniye)
    if saniye < 60:
        return f"{saniye}sn"
    if saniye < 3600:
        return f"{saniye // 60}dk"
    return f"{saniye // 3600}sa{(saniye % 3600) // 60:02d}"


def tablo_yaz(satirlar: list[dict[str, Any]]) -> None:
    basliklar = [
        ("pid", "PID", 7),
        ("kullanici", "KULLANICI", 16),
        ("uygulama", "UYGULAMA", 24),
        ("istemci", "ISTEMCI", 15),
        ("durum", "DURUM", 20),
        ("_yas", "YAS", 7),
        ("_durum_sn", "SURE", 7),
        ("_islem_sn", "ISLEM", 7),
        ("sorgu", "SORGU", 40),
    ]
    print("  ".join(baslik.ljust(genislik) for _, baslik, genislik in basliklar))
    print("  ".join("-" * genislik for _, _, genislik in basliklar))
    for satir in satirlar:
        gorunum = dict(satir)
        gorunum["_yas"] = sure(satir["yas_sn"])
        gorunum["_durum_sn"] = sure(satir["durum_sn"])
        gorunum["_islem_sn"] = sure(satir["islem_sn"])
        if satir["ben"]:
            gorunum["uygulama"] = gorunum["uygulama"] + " (BEN)"
        hucreler = []
        for anahtar, _, genislik in basliklar:
            metin = str(gorunum.get(anahtar) or "-")
            hucreler.append(metin[:genislik].ljust(genislik))
        print("  ".join(hucreler))


def grupla(satirlar: list[dict[str, Any]], anahtar: str, baslik: str) -> None:
    sayac: dict[str, int] = {}
    for satir in satirlar:
        sayac[str(satir[anahtar])] = sayac.get(str(satir[anahtar]), 0) + 1
    print(f"\n{baslik}")
    for ad, adet in sorted(sayac.items(), key=lambda ikili: -ikili[1]):
        print(f"  {adet:>3}  {ad}")


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ayristirici.add_argument("--dsn", help="Baglanti dizesi (varsayilan: DATABASE_URL)")
    ayristirici.add_argument("--hepsi", action="store_true", help="Tum veritabanlarini goster")
    ayristirici.add_argument("--json", action="store_true", help="JSON olarak yaz")
    argumanlar = ayristirici.parse_args()

    dsn = dsn_bul(argumanlar.dsn)

    with psycopg.connect(dsn, connect_timeout=10, application_name=UYGULAMA_ADI) as baglanti:
        with baglanti.cursor(row_factory=dict_row) as imlec:
            imlec.execute(OZET_SQL)
            ozet = imlec.fetchone() or {}
            imlec.execute(LISTE_SQL, {"hepsi": argumanlar.hepsi})
            satirlar = imlec.fetchall()

    if argumanlar.json:
        print(json.dumps({"ozet": ozet, "baglantilar": satirlar}, default=str, indent=2))
        return 0

    uyari = pooler_uyarisi(dsn)
    if uyari:
        print("\n[!] " + uyari + "\n")

    istemci = [satir for satir in satirlar if satir["tur"] == "client backend"]
    bosta_islemde = [satir for satir in istemci if satir["durum"] == "idle in transaction"]

    print(f"Veritabani : {ozet.get('vt')}   Rol: {ozet.get('rol')}")
    print(
        f"Slotlar    : {ozet.get('istemci_toplam')}/{ozet.get('tavan')}"
        " istemci baglantisi (tum veritabanlari)"
    )
    print(f"Bu VT      : {ozet.get('bu_vt')} istemci baglantisi\n")

    tablo_yaz(satirlar)
    grupla(istemci, "uygulama", "UYGULAMAYA GORE")
    grupla(istemci, "istemci", "ISTEMCI IP'SINE GORE")
    grupla(istemci, "durum", "DURUMA GORE")

    if bosta_islemde:
        print(
            f"\n[!] {len(bosta_islemde)} baglanti 'idle in transaction' durumunda.\n"
            "    Bunlar hem slot hem KILIT tutar; oncelikli kesilecekler bunlardir:\n"
            "      python backend/scripts/db_baglanti_kes.py --onayla"
        )

    tavan = ozet.get("tavan") or 0
    toplam = ozet.get("istemci_toplam") or 0
    if tavan and toplam / tavan > 0.8:
        print(
            f"\n[!] Slotlarin %{toplam * 100 // tavan}'i dolu. Yeni backend acan "
            "gelistirici bellek ici veriye duser."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
