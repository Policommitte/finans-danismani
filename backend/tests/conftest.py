"""Ortak test altyapisi.

TASARIM KARARI - SUITE VARSAYILAN OLARAK VERITABANISIZ CALISIR
---------------------------------------------------------------
`backend/.env` GERCEK bir Supabase baglantisi tasir. `app.config.settings`
modul yuklenirken o dosyayi okur, `app/repositories/deps.py` de ilk
repository istegi geldiginde `settings.database_url`'e bakip GERCEKTEN
baglanmaya calisir. Yani hicbir sey yapilmazsa `pytest` calistirmak
URETIM VERITABANINA yazan testler uretir.

Bu yuzden `_veritabani_yalitimi` fixture'i AUTOUSE'dur ve `db` isareti
TASIMAYAN her test icin `settings.database_url`'i BOSALTIR. Sonuc:

  * Tum suite bellek ici repository'lerle calisir -> hizli ve yalitilmis.
  * Kimse kazara uretim verisine dokunamaz.
  * `db` isaretli testler yalnizca `TEST_DATABASE_URL` verildiginde calisir.

HIZ
---
`tests/unit/` altindaki her sey saf fonksiyon testidir: I/O yok, uyku yok,
ag yok. `tests/api/` TestClient kullanir ama bellek ici repo'ya konusur.
Suite `-n auto` ile paralel calisacak sekilde yazilmistir; paylasilan
mutable durum (bellek ici tohum veri) `temiz_veri` fixture'i ile
sifirlanir.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.config import settings

#: `db` isaretli testler icin baglanti. Yoksa o testler ATLANIR.
TEST_DATABASE_URL = (os.getenv("TEST_DATABASE_URL") or "").strip()

#: `db/v5_schema_and_data.sql` ve `in_memory.py` tohumundaki demo kullanici.
DEMO_USER_ID = 1
DEMO_EMAIL = "mehmet@example.com"
DEMO_PASSWORD = "demo1234"

DB_YOK_MESAJI = "TEST_DATABASE_URL tanimli degil; bu test gercek bir veritabani ister."


def pytest_collection_modifyitems(config, items):
    """`db` isaretli testleri baglanti yoksa atlar."""
    if TEST_DATABASE_URL:
        return
    atla = pytest.mark.skip(reason=DB_YOK_MESAJI)
    for item in items:
        if "db" in item.keywords:
            item.add_marker(atla)


@pytest.fixture(autouse=True)
def _veritabani_yalitimi(request, monkeypatch):
    """Testin hangi veri kaynagina konusacagini BELIRLER.

    `db` isareti YOKSA baglanti bosaltilir - `deps.py` bellek ici
    repository'lere duser. Isaret VARSA `TEST_DATABASE_URL`'e baglanir.

    Iki durumda da `reset_repositories()` cagrilir: saglayicilar
    `lru_cache`'lidir, temizlenmezse ilk testin sectigi kaynak tum oturuma
    yapisir.

    `embedding_api_key` de bosaltilir: `.env` gercek bir Cohere anahtari
    tasiyabilir ve `get_rag_repository()` onu embedder'a enjekte eder -
    RAG'e dolayli dokunann her test sessizce ucretli bir API cagrisi
    yapardi. Dense yolu sinayan testler sahte embedder'i DOGRUDAN enjekte
    eder, bu yuzden bu bosaltmadan etkilenmezler.
    """
    from app.repositories.deps import reset_repositories

    if "db" in request.keywords:
        monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    else:
        monkeypatch.setattr(settings, "database_url", "")

    monkeypatch.setattr(settings, "embedding_api_key", "")
    reset_repositories()
    yield
    reset_repositories()


@pytest.fixture(autouse=True)
def _ag_kapali(request, monkeypatch):
    """Testler DISARIYA CIKAMAZ - soket acmak `RuntimeError` firlatir.

    NEDEN GEREKLI: bu kod tabani birden fazla dis servise konusur (Yahoo,
    yfinance, Pexels, NVI SOAP, Cohere, LLM saglayicilari). Yamalanmasi
    UNUTULAN tek bir cagri, testi sessizce yavaslatir, aga bagimli
    (flaky) yapar ve bazi durumlarda UCRETLI bir API cagrisina donusur.
    Yamayi hatirlamak yerine varsayilani kapatiyoruz: bir test aga
    cikmaya calisirsa ANINDA ve acikca patlar.

    `db` isaretli testler muaftir - onlarin isi zaten gercek bir
    PostgreSQL'e baglanmaktir.

    ⚠️ `TestClient` sunucuyu SUREC ICINDE (ASGI) cagirir, soket acmaz;
    bu yuzden API testleri bu yasaktan etkilenmez.
    """
    if "db" in request.keywords:
        yield
        return

    import socket

    izinli = socket.socket

    class _YasakliSoket(izinli):
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "Test icinde ag baglantisi acilmaya calisildi. Dis servis "
                "cagrisini sahte bir nesneyle degistirin; gercekten aga "
                "cikmasi gerekiyorsa testi `@pytest.mark.db` ile isaretleyin."
            )

    monkeypatch.setattr(socket, "socket", _YasakliSoket)
    monkeypatch.setattr(socket, "create_connection", _yasak_baglanti)
    yield


def _yasak_baglanti(*args, **kwargs):
    raise RuntimeError("Test icinde ag baglantisi acilmaya calisildi (create_connection).")


@pytest.fixture
def temiz_veri():
    """Bellek ici tohum veriyi test ONCESI ve SONRASI sifirlar.

    Yalnizca YAZAN testler ister (emir acma, sohbet kaydi, yarisma
    katilimi). Salt okuyan testlerin bu maliyeti odemesine gerek yok -
    bu yuzden autouse DEGIL.
    """
    from app.repositories.in_memory import reset_data

    reset_data()
    yield
    reset_data()


# ---------------------------------------------------------------------------
# HTTP istemcileri
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """`lifespan` CALISTIRILMAZ - arka plan fiyat gorevi testte istenmez.

    `TestClient`'i context manager olarak kullanmadigimiz surece FastAPI
    lifespan'i tetiklenmez; `run_price_scheduler` da baslamaz.
    """
    from app.main import app

    return TestClient(app)


@pytest.fixture
def client_no_raise() -> TestClient:
    """500 senaryolari icin: istisnayi firlatmak yerine yaniti dondurur."""
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def token() -> str:
    from app.auth.security import create_access_token

    return create_access_token(DEMO_USER_ID)


@pytest.fixture
def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Ayar override'i
# ---------------------------------------------------------------------------


@pytest.fixture
def ayar(monkeypatch):
    """Testin sonunda geri alinan ayar degisikligi.

    Kullanim: `ayar(rag_top_k=3, profanity_cancels_finance=False)`
    """

    def _uygula(**kwargs):
        for alan, deger in kwargs.items():
            monkeypatch.setattr(settings, alan, deger)
        return settings

    return _uygula
