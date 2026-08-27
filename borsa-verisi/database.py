"""PostgreSQL yazma katmani - yalnizca bolum 2 (Varlik & Piyasa) tablolari.

DOKUNULAN TABLOLAR
    assets            -> UPDATE (fiyat ve degisim metrikleri)
    price_history     -> INSERT (source='api')
    market_api_usage  -> UPSERT (gunluk cagri sayaci)

DOKUNULMAYAN HER SEY
    Portfoy, sohbet, RAG ve kullanici tablolarina HIC yazilmaz. `assets`
    tablosunda da yalnizca fiyat sutunlari guncellenir; `symbol`, `name`,
    `category_id` ve `currency` DEGISTIRILMEZ.

NEDEN INSERT DEGIL UPDATE?
    Varliklar semanin dummy data bolumunde zaten tanimli ve portfoy satirlari
    `asset_id` ile onlara bagli. Yeni satir eklemek yerine mevcut satirlar
    guncellenir; veritabaninda bilinmeyen bir sembol gelirse ATLANIR ve
    raporda gosterilir - sessizce yeni varlik yaratilmaz.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

import psycopg

from yahoo import PiyasaVerisi

logger = logging.getLogger(__name__)

#: docker-compose.yml'deki gelistirme veritabani.
VARSAYILAN_DSN = "postgresql://finans:finans@localhost:5432/finans"

#: SQLAlchemy surucusu ("postgresql+psycopg://") psycopg'nin anlamadigi bir
#: bicimdir; surucu eki temizlenir.
_SURUCU_EKI = re.compile(r"^postgresql\+\w+://")


@dataclass
class YazmaSonucu:
    """Bir yazma turunun ozeti."""

    guncellenen_varlik: int = 0
    yazilan_gecmis: int = 0
    bulunamayan_semboller: list[str] = field(default_factory=list)
    #: `assets` tablosunda olmadigi icin yazilamayan kolonlar.
    atlanan_kolonlar: list[str] = field(default_factory=list)


def dsn_getir(acik_dsn: str | None = None) -> str:
    """Baglanti adresini cozer: parametre -> DATABASE_URL -> varsayilan."""
    ham = acik_dsn or os.getenv("DATABASE_URL") or VARSAYILAN_DSN
    return _SURUCU_EKI.sub("postgresql://", ham.strip())


def baglan(dsn: str | None = None) -> psycopg.Connection:
    """Veritabanina baglanir. Otomatik commit KAPALI - yazma tek islemde."""
    return psycopg.connect(dsn_getir(dsn), autocommit=False)


# ---------------------------------------------------------------------------
# Okuma
# ---------------------------------------------------------------------------


def sembol_id_haritasi(conn: psycopg.Connection) -> dict[str, int]:
    """`assets` tablosundaki sembol -> id eslemesi."""
    with conn.cursor() as cur:
        cur.execute("SELECT symbol, id FROM assets")
        return {satir[0]: satir[1] for satir in cur.fetchall()}


# ---------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------

_ASSETS_UPDATE = """
UPDATE assets SET
    current_price     = %(current_price)s,
    prev_close        = COALESCE(%(prev_close)s, prev_close),
    daily_change_pct  = COALESCE(%(daily)s,  daily_change_pct),
    weekly_change_pct = COALESCE(%(weekly)s, weekly_change_pct),
    yearly_change_pct = COALESCE(%(yearly)s, yearly_change_pct),
    price_updated_at  = now()
WHERE symbol = %(symbol)s
"""

#: `assets` tablosunda BULUNMAYABILECEK kolonlar -> yazilacak SQL parcasi.
#:
#: NEDEN: Repo semasi (`db/v5_schema_and_data.sql`) ile calisan veritabani
#: her zaman birebir ayni olmayabilir. Var olmayan bir kolona yazmak TUM
#: islemi iptal eder ve binlerce satirlik fiyat verisi geri alinir; bu yuzden
#: UPDATE ifadesi calisma aninda semaya gore kurulur.
#:
#: GECMIS NOT (16 Agustos 2026): ekibin paylasilan Supabase veritabaninda o
#: tarihte `prev_close` ve `price_updated_at` YOKTU ve bu
#: mekanizma sayesinde toplama yine de tamamlandi. Bu KALICI bir durum
#: DEGILDIR, giderilmesi gereken bir sema kaymasidir: backend'in fiyat gorevi
#: (`app/repositories/sql.py`) bu kolonlari OPSIYONEL saymaz, dogrudan
#: kullanir - eksiklerse fiyat guncelleme 15 dakikada bir hata verir.
#: Kolonlari eklemek icin: `db/migrations/001_assets_fiyat_kolonlari.sql`.
_OPSIYONEL_KOLONLAR: dict[str, str] = {
    "prev_close": "prev_close = COALESCE(%(prev_close)s, prev_close)",
    "price_updated_at": "price_updated_at = now()",
}

#: Her zaman var oldugu varsayilan cekirdek kolonlar.
_ZORUNLU_ATAMALAR: tuple[str, ...] = (
    "current_price = %(current_price)s",
    "daily_change_pct = COALESCE(%(daily)s, daily_change_pct)",
    "weekly_change_pct = COALESCE(%(weekly)s, weekly_change_pct)",
    "yearly_change_pct = COALESCE(%(yearly)s, yearly_change_pct)",
)


def mevcut_kolonlar(conn: psycopg.Connection, tablo: str) -> set[str]:
    """Tablodaki kolon adlarini doner."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            (tablo,),
        )
        return {satir[0] for satir in cur.fetchall()}


def assets_update_sorgusu(kolonlar: set[str]) -> str:
    """Mevcut semaya gore UPDATE ifadesini kurar.

    Eksik kolonlar sessizce ATLANIR - boylece betik hem repo semasinda hem
    kolonlari eksik bir veritabaninda calisir.
    """
    atamalar = list(_ZORUNLU_ATAMALAR)

    for kolon, ifade in _OPSIYONEL_KOLONLAR.items():
        if kolon in kolonlar:
            atamalar.append(ifade)

    return "UPDATE assets SET\n    " + ",\n    ".join(atamalar) + "\nWHERE symbol = %(symbol)s"


_PRICE_HISTORY_INSERT = """
INSERT INTO price_history (asset_id, ts, price, source)
VALUES (%s, %s, %s, 'api')
ON CONFLICT (asset_id, ts) DO UPDATE
    SET price = EXCLUDED.price, source = EXCLUDED.source
"""

_API_USAGE_UPSERT = """
INSERT INTO market_api_usage (usage_date, call_count, last_call_at)
VALUES (CURRENT_DATE, %s, now())
ON CONFLICT (usage_date) DO UPDATE
    SET call_count   = market_api_usage.call_count + EXCLUDED.call_count,
        last_call_at = now()
"""


def varliklari_yaz(
    conn: psycopg.Connection,
    veriler: list[PiyasaVerisi],
    gecmis_yaz: bool = True,
) -> YazmaSonucu:
    """Fiyat verilerini veritabanina yazar.

    Tum yazma TEK islemde yapilir: cagiran `commit()` etmezse hicbir sey
    kalici olmaz. Boylece yarim yazilmis bir tur olusmaz.
    """
    sonuc = YazmaSonucu()
    harita = sembol_id_haritasi(conn)

    # Sorgu calisma aninda semaya gore kurulur; eksik kolonlar atlanir.
    kolonlar = mevcut_kolonlar(conn, "assets")
    sorgu = assets_update_sorgusu(kolonlar)
    sonuc.atlanan_kolonlar = sorted(set(_OPSIYONEL_KOLONLAR) - kolonlar)
    if sonuc.atlanan_kolonlar:
        logger.warning(
            "assets tablosunda bulunmayan kolonlar atlandi",
            extra={"kolonlar": sonuc.atlanan_kolonlar},
        )

    with conn.cursor() as cur:
        for veri in veriler:
            asset_id = harita.get(veri.db_symbol)
            if asset_id is None:
                sonuc.bulunamayan_semboller.append(veri.db_symbol)
                logger.warning("sembol veritabaninda yok", extra={"sembol": veri.db_symbol})
                continue

            parametreler = {
                "symbol": veri.db_symbol,
                "current_price": veri.current_price,
                "prev_close": veri.prev_close,
                "daily": veri.daily_change_pct,
                "weekly": veri.weekly_change_pct,
                "yearly": veri.yearly_change_pct,
            }
            cur.execute(sorgu, parametreler)
            sonuc.guncellenen_varlik += cur.rowcount

            if gecmis_yaz and veri.gecmis:
                cur.executemany(
                    _PRICE_HISTORY_INSERT,
                    [(asset_id, ts, fiyat) for ts, fiyat in veri.gecmis],
                )
                sonuc.yazilan_gecmis += len(veri.gecmis)

    return sonuc


def tablo_var_mi(conn: psycopg.Connection, tablo: str) -> bool:
    """Tablonun mevcut semada olup olmadigini soyler."""
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", (tablo,))
        return bool(cur.fetchone()[0])


def api_kullanimi_kaydet(conn: psycopg.Connection, cagri_sayisi: int) -> None:
    """Gunluk cagri sayacini artirir (`market_api_usage`).

    Yahoo resmi bir API degildir ve belgelenmis bir gunluk kotasi yoktur;
    yine de sema bu tabloyu tanimladigi ve asiri cagri gecici engellemeye yol
    actigi icin sayac tutulur.

    TABLO YOKSA SESSIZCE ATLANIR: bu sayac bir yan kayittir, asil is fiyat
    yazmaktir. Tablo bulunmadiginda PostgreSQL islemi (transaction) komple
    iptal eder ve 6.500 satirlik fiyat verisi de geri alinirdi - sayac
    ugruna asil veri kaybedilmez.
    """
    if cagri_sayisi <= 0:
        return

    if not tablo_var_mi(conn, "market_api_usage"):
        logger.warning(
            "market_api_usage tablosu yok, cagri sayaci atlandi " "(fiyat yazimi bundan ETKILENMEZ)"
        )
        return

    with conn.cursor() as cur:
        cur.execute(_API_USAGE_UPSERT, (cagri_sayisi,))
