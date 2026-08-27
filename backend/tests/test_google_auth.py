"""Google ile giris testleri.

`fetch_google_profile` GERCEK Google'a ag istegi atar; testlerde bu fonksiyon
monkeypatch ile sahtelenir. Bilinerek `db` isaretlenmez - bellek ici modda da
calismali (UserRepository.create/get_by_email her iki modda da mevcut).
"""

from unittest.mock import AsyncMock

import pytest

from app.auth.security import decode_access_token
from tests.conftest import DEMO_EMAIL, DEMO_USER_ID


def _sahte_profil(
    email: str, verified: bool = True, given_name: str = "Test", family_name: str = "Kullanici"
):
    return {
        "email": email,
        "given_name": given_name,
        "family_name": family_name,
        "email_verified": verified,
    }


def test_google_bilinmeyen_email_yeni_kullanici_olusturur_ve_onboarding_gerektirir(
    client, monkeypatch
):
    eposta = "google-yeni-kullanici@example.com"
    monkeypatch.setattr(
        "app.api.routes.auth.fetch_google_profile",
        AsyncMock(return_value=_sahte_profil(eposta)),
    )

    yanit = client.post("/api/auth/google", json={"access_token": "sahte-token"})

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["token_type"] == "bearer"

    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {govde['access_token']}"}
    ).json()
    assert me["email"] == eposta
    assert me["onboarding_completed"] is False  # yeni kayit -> zorunlu onboarding


def test_google_kayitli_email_mevcut_hesaba_giris_yapar(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.fetch_google_profile",
        AsyncMock(return_value=_sahte_profil(DEMO_EMAIL)),
    )

    yanit = client.post("/api/auth/google", json={"access_token": "sahte-token"})

    assert yanit.status_code == 200
    assert decode_access_token(yanit.json()["access_token"]) == DEMO_USER_ID


def test_google_dogrulanmamis_email_reddedilir(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.fetch_google_profile",
        AsyncMock(return_value=_sahte_profil("dogrulanmamis@example.com", verified=False)),
    )

    yanit = client.post("/api/auth/google", json={"access_token": "sahte-token"})

    assert yanit.status_code == 401
    assert yanit.json()["error"]["code"] == "unauthorized"


def test_google_gecersiz_token_reddedilir(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.fetch_google_profile", AsyncMock(return_value=None))

    yanit = client.post("/api/auth/google", json={"access_token": "gecersiz"})

    assert yanit.status_code == 401


def test_google_bos_access_token_422_doner(client):
    yanit = client.post("/api/auth/google", json={"access_token": ""})

    assert yanit.status_code == 422


@pytest.mark.db
def test_google_yeni_kullanici_satiri_temizlenir(client, monkeypatch):
    """Gercek DB'ye karsi calisirsa olusturulan satirin kalici kalmadigini dogrular."""
    import asyncio

    from sqlalchemy import text

    from app.db.session import get_session_factory

    eposta = "google-db-test@example.com"
    monkeypatch.setattr(
        "app.api.routes.auth.fetch_google_profile",
        AsyncMock(return_value=_sahte_profil(eposta)),
    )

    try:
        yanit = client.post("/api/auth/google", json={"access_token": "sahte-token"})
        assert yanit.status_code == 200
    finally:

        async def _sil():
            async with get_session_factory()() as session:
                await session.execute(
                    text("DELETE FROM users WHERE email = :email"), {"email": eposta}
                )
                await session.commit()

        asyncio.run(_sil())
