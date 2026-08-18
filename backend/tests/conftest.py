"""Ortak test fixture'lari.

Testler GERCEK PostgreSQL uzerinde calisir; bellek ici veri kaldirildi
(`backend/_mock_arsiv/`). Baglanti `TEST_DATABASE_URL`, o yoksa `DATABASE_URL`
uzerinden gelir:

    TEST_DATABASE_URL=postgresql+psycopg://kullanici:parola@host:5432/veritabani pytest -q

Ikisi de tanimli degilse `@pytest.mark.db` isaretli testler ATLANIR; veri
kaynagina dokunmayan testler (risk hesabi, orkestrasyon grafigi, guvenlik
kurallari, hata zarflari) calismaya devam eder.

⚠️ Isaret edilen veritabani TEST veritabani olmalidir: sohbet ve denetim
testleri gercekten satir yazar.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.config import settings
from app.main import app

TEST_DATABASE_URL = (os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()

#: `db/v5_schema_and_data.sql` seed'indeki demo kullanici.
DEMO_USER_ID = 1
DEMO_EMAIL = "mehmet@example.com"
DEMO_PASSWORD = "demo1234"

DB_YOK_MESAJI = (
    "TEST_DATABASE_URL / DATABASE_URL tanimli degil; bu test gercek bir veritabani ister."
)


def pytest_collection_modifyitems(config, items):
    """Baglanti yoksa `db` isaretli testleri atlar."""
    if TEST_DATABASE_URL:
        return

    atla = pytest.mark.skip(reason=DB_YOK_MESAJI)
    for item in items:
        if "db" in item.keywords:
            item.add_marker(atla)


@pytest.fixture(autouse=True)
def _veritabani(request, monkeypatch):
    """`db` isaretli testleri veritabanina baglar.

    `autouse`: bir testin ayar degistirmesi digerlerini etkilemesin.
    `reset_repositories` onbellekleri temizler; aksi halde ilk baglanti tum
    test oturumu boyunca yapisir.
    """
    if "db" not in request.keywords:
        yield
        return

    from app.repositories.deps import reset_repositories

    monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    reset_repositories()
    yield
    reset_repositories()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def client_no_raise() -> TestClient:
    """500 senaryolari icin: sunucu hatasini firlatmak yerine yaniti dondurur."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def token() -> str:
    """Demo kullanici icin gecerli JWT."""
    return create_access_token(DEMO_USER_ID)


@pytest.fixture
def auth(token: str) -> dict[str, str]:
    """Korumali uclar icin Authorization header'i."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def override_settings(monkeypatch):
    """Test icinde ayarlari gecici olarak degistirir.

    Kullanim: override_settings(log_level="DEBUG", cors_origins="http://a.com")
    Test bitince monkeypatch degisiklikleri geri alir.
    """

    def _override(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setattr(settings, key, value)

    return _override
