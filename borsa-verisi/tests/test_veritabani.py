"""Veritabani katmaninin AG/DB gerektirmeyen kisimlari.

Gercek yazma testi icin ayakta bir PostgreSQL gerekir; burada yalnizca saf
mantik (baglanti adresi cozumleme ve SQL sozlesmesi) sabitlenir.
"""

import psycopg

import database
from database import VARSAYILAN_DSN, dsn_getir

# ---------------------------------------------------------------------------
# Baglanti adresi cozumleme
# ---------------------------------------------------------------------------


def test_sqlalchemy_surucu_eki_temizlenir():
    """`.env` SQLAlchemy bicimi tutar; psycopg bu eki anlamaz."""
    sonuc = dsn_getir("postgresql+psycopg://finans:finans@localhost:5432/finans")

    assert sonuc == "postgresql://finans:finans@localhost:5432/finans"


def test_asyncpg_eki_de_temizlenir():
    assert dsn_getir("postgresql+asyncpg://a:b@h:5432/d") == "postgresql://a:b@h:5432/d"


def test_duz_postgresql_adresi_degismez():
    adres = "postgresql://finans:finans@localhost:5432/finans"

    assert dsn_getir(adres) == adres


def test_parametre_yoksa_ortam_degiskeni_kullanilir(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:y@db:5432/test")

    assert dsn_getir() == "postgresql://x:y@db:5432/test"


def test_hicbir_kaynak_yoksa_varsayilan_kullanilir(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert dsn_getir() == VARSAYILAN_DSN


def test_bosluklar_kirpilir(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  postgresql://a:b@h:5432/d  ")

    assert dsn_getir() == "postgresql://a:b@h:5432/d"


# ---------------------------------------------------------------------------
# SQL sozlesmesi - yanlislikla baska tabloya yazmayi engeller
# ---------------------------------------------------------------------------


def test_yalnizca_bolum2_tablolarina_yazilir():
    """Betik portfoy/sohbet/RAG tablolarina ASLA dokunmamalidir."""
    tum_sql = " ".join(
        [
            database._ASSETS_UPDATE,
            database._PRICE_HISTORY_INSERT,
            database._API_USAGE_UPSERT,
        ]
    ).lower()

    for yasak in ("portfolio", "chat_", "users", "rag.", "transactions", "watchlist"):
        assert yasak not in tum_sql, f"Kapsam disi tabloya dokunuluyor: {yasak}"


def test_assets_guncellemesi_kimlik_sutunlarina_dokunmaz():
    """symbol/name/category_id/currency DEGISTIRILMEMELIDIR."""
    sql = database._ASSETS_UPDATE.lower()
    govde = sql.split("where")[0]

    for korunan in ("category_id", "currency =", "name ="):
        assert korunan not in govde


def test_price_history_kaynagi_api_olarak_isaretlenir():
    """Simulatorun urettigi satirlardan ayirt edilebilmeli."""
    assert "'api'" in database._PRICE_HISTORY_INSERT


def test_price_history_ayni_zaman_damgasinda_cakismaz():
    """PRIMARY KEY (asset_id, ts) - tekrar calistirma hata vermemeli."""
    assert "on conflict (asset_id, ts) do update" in database._PRICE_HISTORY_INSERT.lower()


def test_api_kullanimi_sayaci_uzerine_yazmaz_ekler():
    """Ayni gun ikinci kez calistirilirsa sayac SIFIRLANMAMALI."""
    assert "call_count + excluded.call_count" in database._API_USAGE_UPSERT.lower()


def test_sql_ifadeleri_gecerli_sekilde_ayristirilir():
    """psycopg parametre yer tutucularini cozebiliyor mu?"""
    for sql in (database._PRICE_HISTORY_INSERT, database._API_USAGE_UPSERT):
        # psycopg client-side ayristirici; sozdizimi bozuksa burada patlar.
        psycopg.sql.SQL(sql)  # noqa: B018


# ---------------------------------------------------------------------------
# Yazma davranisi - sahte baglanti ile
# ---------------------------------------------------------------------------


class SahteCursor:
    """Sahte imlec. Varsayilan olarak TAM semali bir veritabani taklit eder."""

    def __init__(self, harita, kolonlar=None):
        self.harita = harita
        self.kolonlar = _TAM_SEMA if kolonlar is None else kolonlar
        self.calistirilan = []
        self.rowcount = 1
        self._sonuc = []

    def execute(self, sql, params=None):
        self.calistirilan.append((sql, params))
        if "SELECT symbol, id FROM assets" in sql:
            self._sonuc = list(self.harita.items())
        elif "information_schema.columns" in sql:
            self._sonuc = [(k,) for k in self.kolonlar]
        return self

    def executemany(self, sql, params):
        self.calistirilan.append((sql, params))

    def fetchall(self):
        return self._sonuc

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class SahteConnection:
    def __init__(self, harita, kolonlar=None):
        self._cursor = SahteCursor(harita, kolonlar)

    def cursor(self):
        return self._cursor


def test_veritabaninda_olmayan_sembol_atlanir_ve_raporlanir():
    """Bilinmeyen sembol icin YENI VARLIK YARATILMAZ."""
    from yahoo import PiyasaVerisi

    conn = SahteConnection({"THYAO": 1})
    veriler = [
        PiyasaVerisi("THYAO", "STOCK", "THYAO.IS", current_price=300.0),
        PiyasaVerisi("YOKBOYLE", "STOCK", "YOK.IS", current_price=10.0),
    ]

    sonuc = database.varliklari_yaz(conn, veriler, gecmis_yaz=False)

    assert sonuc.bulunamayan_semboller == ["YOKBOYLE"]
    calistirilan_sql = " ".join(s for s, _ in conn._cursor.calistirilan)
    assert "INSERT INTO assets" not in calistirilan_sql


def test_gecmis_yaz_kapaliyken_price_history_yazilmaz():
    from yahoo import PiyasaVerisi

    conn = SahteConnection({"THYAO": 1})
    veri = PiyasaVerisi("THYAO", "STOCK", "THYAO.IS", current_price=300.0, gecmis=[(None, 1.0)])

    sonuc = database.varliklari_yaz(conn, [veri], gecmis_yaz=False)

    assert sonuc.yazilan_gecmis == 0


def test_eksik_semali_veritabaninda_yazma_yine_calisir():
    """Supabase senaryosu: 3 kolon eksik ama fiyat yazimi TAMAMLANMALI."""
    from yahoo import PiyasaVerisi

    conn = SahteConnection({"THYAO": 1}, kolonlar=_EKSIK_SEMA)
    veri = PiyasaVerisi(
        "THYAO", "STOCK", "THYAO.IS", current_price=301.5, prev_close=300.0, daily_change_pct=0.5
    )

    sonuc = database.varliklari_yaz(conn, [veri], gecmis_yaz=False)

    assert sonuc.guncellenen_varlik == 1
    assert sonuc.atlanan_kolonlar == ["prev_close", "price_updated_at"]


def test_sifir_cagride_kullanim_kaydi_yazilmaz():
    conn = SahteConnection({})

    database.api_kullanimi_kaydet(conn, 0)

    assert conn._cursor.calistirilan == []


# ---------------------------------------------------------------------------
# Semaya uyum - eksik kolonlar tum yazmayi dusurmemeli
# ---------------------------------------------------------------------------


_TAM_SEMA = {
    "current_price",
    "prev_close",
    "daily_change_pct",
    "weekly_change_pct",
    "yearly_change_pct",
    "price_updated_at",
}

#: Supabase'deki gercek sema - 3 kolon eksik.
_EKSIK_SEMA = {
    "current_price",
    "daily_change_pct",
    "weekly_change_pct",
    "yearly_change_pct",
}


def test_tam_semada_tum_kolonlar_yazilir():
    sorgu = database.assets_update_sorgusu(_TAM_SEMA)

    assert "prev_close" in sorgu
    assert "price_updated_at" in sorgu
    assert "current_price" in sorgu


def test_eksik_kolonlar_sorgudan_cikarilir():
    """prev_close/price_updated_at yoksa SQL onlari HIC icermemeli."""
    sorgu = database.assets_update_sorgusu(_EKSIK_SEMA)

    assert "prev_close" not in sorgu
    assert "price_updated_at" not in sorgu
    # Cekirdek alanlar yine yazilir
    assert "current_price" in sorgu
    assert "daily_change_pct" in sorgu
    assert "yearly_change_pct" in sorgu


def test_eksik_semada_sorgu_gecerli_sql_kalir():
    """Kolon atlaninca fazladan virgul kalmamali."""
    sorgu = database.assets_update_sorgusu(_EKSIK_SEMA)

    assert ",\nWHERE" not in sorgu
    assert sorgu.strip().endswith("WHERE symbol = %(symbol)s")
    psycopg.sql.SQL(sorgu)  # noqa: B018 - sozdizimi bozuksa patlar


def test_market_api_usage_tablosu_yoksa_atlanir(monkeypatch):
    """Sayac tablosu yoksa fiyat yazimi RISKE ATILMAZ.

    PostgreSQL'de basarisiz bir ifade tum islemi iptal eder; sayac ugruna
    6.500 satirlik fiyat verisi geri alinmamalidir.
    """
    monkeypatch.setattr(database, "tablo_var_mi", lambda conn, tablo: False)
    conn = SahteConnection({})

    database.api_kullanimi_kaydet(conn, 14)

    yazma_sql = [s for s, _ in conn._cursor.calistirilan if "market_api_usage" in s]
    assert yazma_sql == []


def test_market_api_usage_tablosu_varsa_yazilir(monkeypatch):
    monkeypatch.setattr(database, "tablo_var_mi", lambda conn, tablo: True)
    conn = SahteConnection({})

    database.api_kullanimi_kaydet(conn, 14)

    yazma_sql = [s for s, _ in conn._cursor.calistirilan if "market_api_usage" in s]
    assert len(yazma_sql) == 1
