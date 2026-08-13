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
