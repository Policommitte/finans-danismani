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

⚠️ `DATABASE_URL`'E GERI DUSULMEZ. Eski conftest "TEST_DATABASE_URL yoksa
DATABASE_URL" diyordu; `.env` uretim baglantisini tasidigi icin bu, yerelde
`pytest` yazan herkesin `db` testlerini URETIM veritabanina kosturmasi
demekti. CI baglantiyi acikca `TEST_DATABASE_URL` olarak verir
(bkz. `.github/workflows/backend-ci.yml`), bu yuzden geri dusus gereksiz.

TEST YAPISI
-----------
    tests/unit/         saf fonksiyon - I/O yok, uyku yok, ag yok
    tests/agents/       ajan sinifleri + orkestrasyon motoru (sahte LLM/MCP)
    tests/services/     app/services, app/leads, app/notifications, app/documents
    tests/api/          TestClient - bellek ici repo'ya konusur
    tests/integration/  GERCEK PostgreSQL ister (`@pytest.mark.db`)
    tests/helpers/      fixture degil, ARAC: sahte nesneler ve ureticiler
"""

from __future__ import annotations

import asyncio
import os
import sys
import warnings

import pytest
from fastapi.testclient import TestClient

from app.config import settings

if sys.platform == "win32":
    # psycopg'nin async surucusu Proactor event loop'u DESTEKLEMEZ
    # (bkz. run.py'deki ayni duzeltme). Bu satir olmadan `db` isaretli her
    # test baglanti kurarken `InterfaceError` firlatir.
    #
    # `catch_warnings`: Python 3.14 hem politika sinifini hem
    # `set_event_loop_policy`'yi DeprecationWarning ile isaretledi. Uyari
    # burada susturulur - pyproject'teki `filterwarnings` conftest IMPORT
    # edilirken henuz devrede degildir.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
    RAG'e dolayli dokunan her test sessizce UCRETLI bir API cagrisi
    yapardi. Dense yolu KASITLI olarak sinayan testler sahte embedder'i
    DOGRUDAN `SqlRagRepository`'ye enjekte eder, bu yuzden bu bosaltmadan
    etkilenmezler.
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


# ---------------------------------------------------------------------------
# Ag muhafizi
# ---------------------------------------------------------------------------

#: Geri dongu (loopback) adlari. Olay dongusunun ic haberlesme borusu ve
#: `TestClient` yalnizca bunlara baglanir; disari cikan hicbir cagri buraya
#: gitmez, bu yuzden muafiyet muhafizi zayiflatmaz.
_YEREL_SUNUCULAR = frozenset(
    {"", "localhost", "localhost.localdomain", "127.0.0.1", "::1", "0.0.0.0", "::"}
)

_AG_YASAK_MESAJI = (
    "Test icinde DIS ag baglantisi acilmaya calisildi ({hedef!r}). Dis servis "
    "cagrisini sahte bir nesneyle degistirin; gercekten aga cikmasi gerekiyorsa "
    "testi `@pytest.mark.db` ile isaretleyin."
)


def _yerel_mi(adres) -> bool:
    """`connect` adresinin geri donguye mi gittigini soyler.

    AF_UNIX adresleri (duz yol ya da soyut ad) da yereldir: surec ici
    haberlesme, aga cikmaz.
    """
    if isinstance(adres, (bytes, bytearray)):
        return True
    if isinstance(adres, str):
        return adres.startswith("/") or adres.startswith("\0") or adres in _YEREL_SUNUCULAR
    if isinstance(adres, tuple) and adres:
        sunucu = adres[0]
        if sunucu is None:
            return True
        if isinstance(sunucu, str):
            # IPv6 kapsam eki ("fe80::1%eth0") ayiklanir.
            return sunucu.split("%", 1)[0] in _YEREL_SUNUCULAR
    # Taninmayan adres bicimi: guvenli taraf YASAKLAMAKTIR.
    return False


def _yasakla(adres) -> None:
    if _yerel_mi(adres):
        return
    hedef = adres[0] if isinstance(adres, tuple) and adres else adres
    raise RuntimeError(_AG_YASAK_MESAJI.format(hedef=hedef))


@pytest.fixture(autouse=True)
def _ag_kapali(request, monkeypatch):
    """Testler DISARIYA CIKAMAZ - dis bir adrese baglanmak `RuntimeError` verir.

    NEDEN GEREKLI: bu kod tabani birden fazla dis servise konusur (Yahoo,
    yfinance, Pexels, NVI SOAP, Cohere, LLM saglayicilari). Yamalanmasi
    UNUTULAN tek bir cagri, testi sessizce yavaslatir, aga bagimli (flaky)
    yapar ve bazi durumlarda UCRETLI bir API cagrisina donusur. Yamayi
    hatirlamak yerine varsayilani kapatiyoruz.

    `db` isaretli testler muaftir - onlarin isi zaten gercek bir
    PostgreSQL'e baglanmaktir.

    ⚠️ YASAK "SOKET YARATMAK" DEGIL "DISARI BAGLANMAK".
    Onceden `socket.socket.__init__` topyekun kapatiliyordu ve bu, API
    testlerinin TAMAMINI (99 test) kiriyordu. `TestClient` gercekten ASGI
    ile surec icinde cagirir - ama bunun icin bir asyncio olay dongusu
    kurar ve HER olay dongusu kendi self-pipe'ini `socketpair()` ile acar;
    o da `socket.socket`'ten gecer. Hata
    "'ProactorEventLoop' object has no attribute '_ssock'" olarak yuzeye
    cikip asil nedeni gizliyordu. Windows'a OZGU DEGILDIR: Linux'ta da
    `asyncio` self-pipe icin ayni yoldan gecer.

    Bu yuzden yasak `connect`/`connect_ex` katmanina indirildi ve geri
    dongu adresleri muaf tutuldu. Soket YARATMAK serbest, DIS bir adrese
    BAGLANMAK yasak.

    ⚠️ Yama SINIFIN KENDISINE uygulanir (`socket.socket.connect`), modul
    ismine degil: `from socket import socket` yapan bir kutuphane de
    yakalanir. Yalnizca `socket.socket` ismini degistirmek onlari kacirirdi.
    """
    if "db" in request.keywords:
        yield
        return

    import socket as socket_modulu

    gercek_connect = socket_modulu.socket.connect
    gercek_connect_ex = socket_modulu.socket.connect_ex
    gercek_create_connection = socket_modulu.create_connection

    def _connect(self, adres, *args, **kwargs):
        _yasakla(adres)
        return gercek_connect(self, adres, *args, **kwargs)

    def _connect_ex(self, adres, *args, **kwargs):
        _yasakla(adres)
        return gercek_connect_ex(self, adres, *args, **kwargs)

    def _create_connection(adres, *args, **kwargs):
        _yasakla(adres)
        return gercek_create_connection(adres, *args, **kwargs)

    monkeypatch.setattr(socket_modulu.socket, "connect", _connect)
    monkeypatch.setattr(socket_modulu.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket_modulu, "create_connection", _create_connection)
    yield


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
