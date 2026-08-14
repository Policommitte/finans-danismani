"""Ortak test fixture'lari.

Testler DATABASE_URL tanimsiz calisir: repository katmani bellek ici veriye
duser (`app/repositories/deps.py`). Boylece CI'da Postgres gerekmez ve testler
saniyeler icinde biter. SQL implementasyonlari ayrica isaretlenmis
entegrasyon testleriyle dogrulanir.
"""

import pytest
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.config import settings
from app.main import app

#: Bellek ici veri kumesindeki demo kullanici (SQL seed'i ile ayni kayit).
DEMO_USER_ID = 1
DEMO_EMAIL = "mehmet@example.com"
DEMO_PASSWORD = "demo1234"


@pytest.fixture(autouse=True)
def _bellek_ici_veri(monkeypatch):
    """Her test bellek ici repository'lerle baslar.

    `autouse`: bir testin DATABASE_URL tanimlamasi digerlerini etkilemesin.
    `reset_repositories` onbellekleri temizler; aksi halde ilk secim tum test
    oturumu boyunca yapisir.
    """
    from app.repositories.deps import reset_repositories
    from app.repositories.in_memory import reset_data

    monkeypatch.setattr(settings, "database_url", "")
    reset_repositories()
    # Fiyat gorevi bellek ici fiyatlari yerinde gunceller; sifirlanmazsa bir
    # testin tetikledigi tick digerinin bekledigi seed degerini bozar.
    reset_data()
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
