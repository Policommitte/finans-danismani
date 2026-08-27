"""Kimlik dogrulama testleri (§14-8).

Sinanan davranislar:
  * Dogru kimlik bilgisiyle token uretilir, `/me` calisir.
  * Yanlis kimlik bilgisi ile kullanici bulunamamasi AYNI mesaji verir
    (hangi e-postalarin kayitli oldugu sizmasin).
  * Korumali uclar token'siz 401 doner ve proje hata sozlesmesine uyar.
"""

import pytest

from app.auth.security import create_access_token, decode_access_token, verify_password
from tests.conftest import DEMO_EMAIL, DEMO_PASSWORD, DEMO_USER_ID

pytestmark = pytest.mark.db

KORUMALI_UCLAR = [
    "/api/auth/me",
    "/api/dashboard/summary",
    "/api/portfolio/summary",
    "/api/portfolio/holdings",
    "/api/portfolio/allocation",
    "/api/portfolio/transactions",
    "/api/market/assets",
    "/api/risk/profile",
    "/api/conversations",
]


def test_login_token_dondurur(client):
    yanit = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["token_type"] == "bearer"
    assert decode_access_token(govde["access_token"]) == DEMO_USER_ID


def test_login_yanlis_sifreyi_reddeder(client):
    yanit = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": "yanlis"})

    assert yanit.status_code == 401
    assert yanit.json()["error"]["code"] == "unauthorized"


def test_login_bilinmeyen_kullanici_ile_ayni_mesaji_verir(client):
    """Kullanici numaralandirmasina karsi: iki durum ayirt EDILEMEMELI."""
    yanlis_sifre = client.post(
        "/api/auth/login", json={"email": DEMO_EMAIL, "password": "yanlis"}
    ).json()
    yok = client.post(
        "/api/auth/login", json={"email": "yok@example.com", "password": DEMO_PASSWORD}
    ).json()

    assert yanlis_sifre["error"]["message"] == yok["error"]["message"]


def test_login_gecersiz_eposta_bicimini_reddeder(client):
    yanit = client.post("/api/auth/login", json={"email": "eposta-degil", "password": "x"})

    assert yanit.status_code == 422
    assert yanit.json()["error"]["code"] == "validation_error"


def test_me_profil_dondurur_ama_sifre_hashini_dondurmez(client, auth):
    yanit = client.get("/api/auth/me", headers=auth)

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["id"] == DEMO_USER_ID
    assert govde["email"] == DEMO_EMAIL
    assert "password_hash" not in govde


@pytest.mark.parametrize("yol", KORUMALI_UCLAR)
def test_korumali_uclar_tokensiz_401_doner(client, yol):
    yanit = client.get(yol)

    assert yanit.status_code == 401
    hata = yanit.json()["error"]
    # Proje hata sozlesmesi: code + message + request_id (backend-kararlar.md §4)
    assert hata["code"] == "unauthorized"
    assert hata["request_id"]
    assert yanit.headers["X-Request-ID"] == hata["request_id"]


def test_gecersiz_token_401_doner(client):
    yanit = client.get("/api/auth/me", headers={"Authorization": "Bearer bozuk.token.dizesi"})

    assert yanit.status_code == 401


def test_suresi_dolmus_token_401_doner(client):
    suresi_dolmus = create_access_token(DEMO_USER_ID, expires_minutes=-1)

    yanit = client.get("/api/auth/me", headers={"Authorization": f"Bearer {suresi_dolmus}"})

    assert yanit.status_code == 401


def test_silinmis_kullanicinin_tokeni_calismaz(client):
    """Token gecerli ama kullanici yok: yetki DB'deki guncel kayda gore verilir."""
    yanit = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {create_access_token(9999)}"}
    )

    assert yanit.status_code == 401


def test_bozuk_hash_istisna_firlatmaz():
    """Bozuk hash 500 degil 'gecersiz kimlik' anlamina gelmeli."""
    assert verify_password("demo1234", "bu-bir-bcrypt-hashi-degil") is False
    assert verify_password("", "") is False


# --- register / onboarding (US16) -------------------------------------------


async def _kullaniciyi_sil(email: str) -> None:
    """Testin olusturdugu satiri temizler - `create()` testler disinda hicbir
    yerden cagrilmadigindan, bu yardimci olmadan test veritabani birikir."""
    from sqlalchemy import text

    from app.db.session import get_session_factory

    async with get_session_factory()() as session:
        await session.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
        await session.commit()


def test_register_kullanici_olusturur_ve_token_doner(client):
    import asyncio

    eposta = "onboarding-test-register@example.com"
    try:
        yanit = client.post(
            "/api/auth/register",
            json={
                "email": eposta,
                "password": "Test1234!",
                "first_name": "Test",
                "last_name": "Kullanici",
            },
        )

        assert yanit.status_code == 201
        govde = yanit.json()
        assert govde["token_type"] == "bearer"
        assert decode_access_token(govde["access_token"]) is not None
    finally:
        asyncio.run(_kullaniciyi_sil(eposta))


def test_register_yinelenen_eposta_409_doner(client):
    yanit = client.post(
        "/api/auth/register",
        json={
            "email": DEMO_EMAIL,
            "password": "Test1234!",
            "first_name": "Test",
            "last_name": "Kullanici",
        },
    )

    assert yanit.status_code == 409
    assert yanit.json()["error"]["code"] == "conflict"


def test_me_onboarding_completed_alanini_dondurur(client, auth):
    yanit = client.get("/api/auth/me", headers=auth)

    assert yanit.status_code == 200
    assert yanit.json()["onboarding_completed"] is True  # demo kullanici seed'de true


def test_yeni_kayitli_kullanici_onboarding_completed_false_baslar(client):
    import asyncio

    eposta = "onboarding-test-flag@example.com"
    try:
        kayit = client.post(
            "/api/auth/register",
            json={
                "email": eposta,
                "password": "Test1234!",
                "first_name": "Test",
                "last_name": "Kullanici",
            },
        )
        token = kayit.json()["access_token"]

        yanit = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert yanit.json()["onboarding_completed"] is False
    finally:
        asyncio.run(_kullaniciyi_sil(eposta))


def test_onboarding_complete_risk_toleransini_ve_bayragi_gunceller(client):
    import asyncio

    eposta = "onboarding-test-complete@example.com"
    try:
        kayit = client.post(
            "/api/auth/register",
            json={
                "email": eposta,
                "password": "Test1234!",
                "first_name": "Test",
                "last_name": "Kullanici",
            },
        )
        headers = {"Authorization": f"Bearer {kayit.json()['access_token']}"}

        yanit = client.post(
            "/api/auth/onboarding/complete", json={"risk_tolerance": "HIGH"}, headers=headers
        )

        assert yanit.status_code == 200
        govde = yanit.json()
        assert govde["risk_tolerance"] == "HIGH"
        assert govde["onboarding_completed"] is True

        # /me uzerinden de kalicilik dogrulanir
        me = client.get("/api/auth/me", headers=headers).json()
        assert me["risk_tolerance"] == "HIGH"
        assert me["onboarding_completed"] is True
    finally:
        asyncio.run(_kullaniciyi_sil(eposta))
