"""Supabase/PostgreSQL uzerindeki baglantilari DUSURUR (`pg_terminate_backend`).

NEDEN VAR: session pooler'inda 25 slot var ve ekip paylasiyor. Biri
backend'ini kapatmadan makinesini kapattiginda ya da bir surec 'idle in
transaction' takildiginda slot geri gelmez; slotlar dolunca yeni backend
acan herkes sessizce bellek ici veriye duser.

⚠️ BU BETIK BASKALARININ ISINI KESER. Varsayilan davranis KURU CALISMADIR:
`--onayla` verilmedikce hicbir sey oldurulmez, yalnizca "kesilecek olanlar"
listelenir.

KULLANIM (backend venv'i acikken):

    python backend/scripts/db_baglanti_kes.py                 # kuru calisma
    python backend/scripts/db_baglanti_kes.py --onayla        # bostakileri kes
    python backend/scripts/db_baglanti_kes.py --bosta-sn 300 --onayla
    python backend/scripts/db_baglanti_kes.py --uygulama polifin-backend --onayla
    python backend/scripts/db_baglanti_kes.py --pid 12345 --onayla
    python backend/scripts/db_baglanti_kes.py --aktifleri-de --onayla   # TEHLIKELI

VARSAYILAN GUVENLIK SINIRLARI (hepsi bilincli):
  * yalnizca `state IN ('idle', 'idle in transaction')` - CALISAN sorgular
    dokunulmaz (`--aktifleri-de` ile acilir)
  * yalnizca `backend_type = 'client backend'` - autovacuum, walwriter,
    checkpointer gibi sunucu sureclerine dokunulmaz
  * `KORUNAN_ROLLER` listesindeki Supabase sistem rolleri atlanir; bunlari
    oldurmek Studio'yu, pooler'i ve Auth'u bozar
  * betigin kendi baglantisi atlanir
  * en az `--bosta-sn` saniyedir bekleyenler (varsayilan 60) - az once
    acilmis saglikli bir havuz baglantisi kesilmez
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - kurulum uyarisi
    print("psycopg kurulu degil. Backend venv'ini acin: pip install 'psycopg[binary]'")
    raise SystemExit(2) from None

UYGULAMA_ADI = "polifin-ops-kes"

#: Supabase'in kendi rolleri. Bunlarin baglantisini kesmek panoyu, pooler'i
#: ve arka plan islerini bozar - filtreye takilsalar bile atlanirlar.
#: `--korumasiz` ile devre disi birakilabilir, ama gercekten gerekmedikce
#: kullanilmamali.
KORUNAN_ROLLER = {
    "supabase_admin",
    "supabase_auth_admin",
    "supabase_storage_admin",
    "supabase_replication_admin",
    "supabase_read_only_user",
    "supabase_realtime_admin",
    "authenticator",
    "pgbouncer",
    "dashboard_user",
    "pgsodium_keyiduser",
}

ADAY_SQL = r"""
SELECT
    pid,
    COALESCE(usename, '-')                                     AS kullanici,
    COALESCE(NULLIF(application_name, ''), '-')                AS uygulama,
    COALESCE(host(client_addr), 'local')                       AS istemci,
    COALESCE(state, '-')                                       AS durum,
    backend_type                                               AS tur,
    EXTRACT(EPOCH FROM (now() - state_change))::int            AS durum_sn,
    EXTRACT(EPOCH FROM (now() - backend_start))::int           AS yas_sn,
    LEFT(REGEXP_REPLACE(COALESCE(query, ''), '\s+', ' ', 'g'), 60) AS sorgu
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
  AND backend_type = 'client backend'
ORDER BY (state = 'idle in transaction') DESC, state_change
"""

BOSTA_DURUMLAR = {"idle", "idle in transaction", "idle in transaction (aborted)"}


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
            '    python scripts/db_baglanti_kes.py --dsn "postgresql://kullanici:sifre@host:5432/postgres"'
        )
        raise SystemExit(2)
    return dsn_hazirla(url)


def pooler_uyarisi(dsn: str) -> str | None:
    """Pooler arkasindayken KESMEK SORUNU COZMEZ.

    Supavisor (`*.pooler.supabase.com`) kendi sunucu baglantilarini yonetir:
    birini oldurdugunuzde gelistiricinin uygulamasi kopmaz, pooler saniyeler
    icinde yenisini acar - slot geri gelmez, yalnizca sayac sifirlanir.
    Gercekten slot bosaltmak icin ya DOGRUDAN baglantiya gecin ya da slotu
    tutan gelistirici backend'ini kapatsin.
    """
    host = (urlsplit(dsn).hostname or "").lower()
    if "pooler.supabase.com" in host:
        return (
            "POOLER UZERINDEN BAGLISINIZ (" + host + ").\n"
            "  Burada olduracaginiz sey POOLER'in kendi baglantisidir; ilgili\n"
            "  gelistiricinin uygulamasi kopmaz ve pooler hemen yenisini acar.\n"
            "  Kalici cozum icin ya DOGRUDAN baglanti dizesini kullanin\n"
            "  (db.<ref>.supabase.co:5432) ya da slotu tutan kisi backend'ini\n"
            "  kapatsin. Supabase panosundan pooler'i yeniden baslatmak da\n"
            "  tum slotlari tek seferde bosaltir."
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


def elenme_sebebi(satir: dict[str, Any], argumanlar: argparse.Namespace) -> str | None:
    """Bu baglanti neden KESILMEYECEK? None donerse aday demektir."""
    if not argumanlar.korumasiz and satir["kullanici"] in KORUNAN_ROLLER:
        return "korunan Supabase rolu"
    if satir["uygulama"].startswith("polifin-ops"):
        return "bu betigin kendi baglantisi"
    if argumanlar.pid and satir["pid"] not in argumanlar.pid:
        return "--pid disinda"
    if argumanlar.uygulama and argumanlar.uygulama not in satir["uygulama"]:
        return "--uygulama eslesmedi"
    if argumanlar.kullanici and argumanlar.kullanici != satir["kullanici"]:
        return "--kullanici eslesmedi"
    if not argumanlar.aktifleri_de and satir["durum"] not in BOSTA_DURUMLAR:
        return f"bosta degil ({satir['durum']})"
    if (satir["durum_sn"] or 0) < argumanlar.bosta_sn:
        return f"{argumanlar.bosta_sn}sn'den yeni"
    return None


def main() -> int:
    ayristirici = argparse.ArgumentParser(
        description="Bostaki PostgreSQL baglantilarini dusurur. Varsayilan: kuru calisma.",
        epilog="Once `db_baglantilari.py` ile kimin tuttuguna bakin.",
    )
    ayristirici.add_argument("--dsn", help="Baglanti dizesi (varsayilan: DATABASE_URL)")
    ayristirici.add_argument(
        "--onayla",
        action="store_true",
        help="GERCEKTEN kes. Verilmezse yalnizca listelenir.",
    )
    ayristirici.add_argument(
        "--bosta-sn",
        type=int,
        default=60,
        metavar="N",
        help="En az N saniyedir ayni durumda olanlar (varsayilan: 60)",
    )
    ayristirici.add_argument("--uygulama", help="application_name icinde gecen metin")
    ayristirici.add_argument("--kullanici", help="Yalnizca bu DB rolu")
    ayristirici.add_argument(
        "--pid", type=int, nargs="+", metavar="PID", help="Yalnizca bu pid'ler"
    )
    ayristirici.add_argument(
        "--aktifleri-de",
        action="store_true",
        help="CALISAN sorgulari da kes - veri kaybettirebilir, dikkat",
    )
    ayristirici.add_argument(
        "--korumasiz",
        action="store_true",
        help="Supabase sistem rollerini de aday yap (onerilmez)",
    )
    argumanlar = ayristirici.parse_args()

    dsn = dsn_bul(argumanlar.dsn)
    uyari = pooler_uyarisi(dsn)
    if uyari:
        print("\n[!] " + uyari + "\n")

    with psycopg.connect(
        dsn, connect_timeout=10, application_name=UYGULAMA_ADI, autocommit=True
    ) as baglanti:
        with baglanti.cursor(row_factory=dict_row) as imlec:
            imlec.execute(ADAY_SQL)
            satirlar = imlec.fetchall()

            adaylar = []
            elenenler = []
            for satir in satirlar:
                sebep = elenme_sebebi(satir, argumanlar)
                (elenenler if sebep else adaylar).append((satir, sebep))

            print(f"Toplam istemci baglantisi : {len(satirlar)}")
            print(f"Kesilecek                 : {len(adaylar)}")
            print(f"Atlanacak                 : {len(elenenler)}\n")

            if not adaylar:
                print("Olcute uyan baglanti yok. Bir sey yapilmadi.")
                if elenenler:
                    print("\nAtlananlar:")
                    for satir, sebep in elenenler:
                        print(
                            f"  pid {satir['pid']:<8} {satir['kullanici']:<16}"
                            f" {satir['uygulama'][:24]:<24} -> {sebep}"
                        )
                return 0

            baslik = "KESILECEKLER" if argumanlar.onayla else "KESILECEKLER (KURU CALISMA)"
            print(baslik)
            for satir, _ in adaylar:
                print(
                    f"  pid {satir['pid']:<8} {satir['kullanici']:<16}"
                    f" {satir['uygulama'][:24]:<24} {satir['durum']:<26}"
                    f" {sure(satir['durum_sn']):>7}  {satir['sorgu'][:40]}"
                )

            if not argumanlar.onayla:
                print(
                    "\nHicbir sey kesilmedi (kuru calisma).\n"
                    "Gercekten kesmek icin ayni komuta --onayla ekleyin."
                )
                return 0

            print("\nKesiliyor...")
            kesilen = 0
            for satir, _ in adaylar:
                # `pg_terminate_backend` false donerse baglanti zaten kapanmistir;
                # hata firlatirsa rolun `pg_signal_backend` yetkisi yoktur.
                try:
                    imlec.execute("SELECT pg_terminate_backend(%s) AS ok", (satir["pid"],))
                    sonuc = imlec.fetchone()
                    basarili = bool(sonuc and sonuc["ok"])
                except psycopg.Error as hata:
                    print(f"  pid {satir['pid']:<8} HATA: {str(hata).strip()}")
                    continue
                kesilen += int(basarili)
                print(f"  pid {satir['pid']:<8} {'kesildi' if basarili else 'zaten kapali'}")

            # Kesme asenkrondur: sunucu sinyali gonderir, backend'in gercekten
            # dusmesi bir an surer. Sayimi hemen yaparsak eski degeri okuruz.
            time.sleep(1.0)
            imlec.execute(
                "SELECT count(*) AS n FROM pg_stat_activity"
                " WHERE datname = current_database() AND backend_type = 'client backend'"
            )
            kalan = imlec.fetchone()
            print(f"\n{kesilen} baglanti kesildi. Kalan istemci baglantisi: {kalan['n']}")

    print(
        "\nKALICI COZUM DEGIL: bu betik yangin sondurur. Slotlarin tekrar\n"
        "dolmamasi icin .env'de DB_POOL_SIZE/DB_MAX_OVERFLOW dusuk kalmali ve\n"
        "yalnizca arayuzle ugrasanlar PRICE_TICK_SECONDS=0 kullanmali."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
