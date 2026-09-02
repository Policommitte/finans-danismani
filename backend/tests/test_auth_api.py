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
    "/api/trading/account",
    "/api/risk/profile",
    "/api/conversations",
]


def test_login_returns_token(client):
    yanit = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["token_type"] == "bearer"
    assert decode_access_token(govde["access_token"]) == DEMO_USER_ID


def test_login_rejects_wrong_password(client):
    yanit = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": "yanlis"})

    assert yanit.status_code == 401
    assert yanit.json()["error"]["code"] == "unauthorized"


def test_login_gives_same_message_for_unknown_user(client):
    """Kullanici numaralandirmasina karsi: iki durum ayirt EDILEMEMELI."""
    yanlis_sifre = client.post(
        "/api/auth/login", json={"email": DEMO_EMAIL, "password": "yanlis"}
    ).json()
    yok = client.post(
        "/api/auth/login", json={"email": "yok@example.com", "password": DEMO_PASSWORD}
    ).json()

    assert yanlis_sifre["error"]["message"] == yok["error"]["message"]


def test_login_rejects_invalid_email_format(client):
    yanit = client.post("/api/auth/login", json={"email": "eposta-degil", "password": "x"})

    assert yanit.status_code == 422
    assert yanit.json()["error"]["code"] == "validation_error"


def test_me_returns_profile_without_password_hash(client, auth):
    yanit = client.get("/api/auth/me", headers=auth)

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["id"] == DEMO_USER_ID
    assert govde["email"] == DEMO_EMAIL
    assert "password_hash" not in govde


@pytest.mark.parametrize("yol", KORUMALI_UCLAR)
def test_protected_endpoints_return_401_without_token(client, yol):
    yanit = client.get(yol)

    assert yanit.status_code == 401
    hata = yanit.json()["error"]
    # Proje hata sozlesmesi: code + message + request_id (backend-kararlar.md §4)
    assert hata["code"] == "unauthorized"
    assert hata["request_id"]
    assert yanit.headers["X-Request-ID"] == hata["request_id"]


def test_invalid_token_returns_401(client):
    yanit = client.get("/api/auth/me", headers={"Authorization": "Bearer bozuk.token.dizesi"})

    assert yanit.status_code == 401


def test_expired_token_returns_401(client):
    suresi_dolmus = create_access_token(DEMO_USER_ID, expires_minutes=-1)

    yanit = client.get("/api/auth/me", headers={"Authorization": f"Bearer {suresi_dolmus}"})

    assert yanit.status_code == 401


def test_deleted_user_token_does_not_work(client):
    """Token gecerli ama kullanici yok: yetki DB'deki guncel kayda gore verilir."""
    yanit = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {create_access_token(9999)}"}
    )

    assert yanit.status_code == 401


def test_corrupt_hash_does_not_raise():
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


#: Resmi mod-10 saglamasini gecen, gercek bir kisiye ait OLMAYAN test
#: TCKN'leri. Her test kendi numarasini kullanir - `tckn_hash` UNIQUE
#: oldugu icin ayni numara iki farkli (temizlenmemis) kayitta CAKISABILIR.
GECERLI_TCKN_1 = "76048764754"
GECERLI_TCKN_2 = "39141777694"
GECERLI_TCKN_3 = "11152449388"
GECERLI_TCKN_4 = "49825979160"
GECERLI_TCKN_5 = "44167211084"
GECERLI_TCKN_6 = "55807302178"
GECERLI_TCKN_7 = "27400297540"
GECERLI_TCKN_8 = "62601815964"


def _kayit_govdesi(email: str, tckn: str, **overrides) -> dict:
    govde = {
        "email": email,
        "password": "Test1234!",
        "first_name": "Test",
        "last_name": "Kullanici",
        "tckn": tckn,
        "birth_date": "1990-01-01",
        "phone_number": "05551234567",
    }
    govde.update(overrides)
    return govde


def _nvi_sonucu(deger):
    """`verify_identity`'yi sabit bir sonuc donen sahte bir coroutine ile degistirir."""

    async def _sahte(**kwargs):
        return deger

    return _sahte


def test_register_kullanici_olusturur_ve_token_doner(client, monkeypatch):
    import asyncio

    monkeypatch.setattr("app.api.routes.auth.verify_identity", _nvi_sonucu(True))
    eposta = "onboarding-test-register@example.com"
    try:
        yanit = client.post("/api/auth/register", json=_kayit_govdesi(eposta, GECERLI_TCKN_1))

        assert yanit.status_code == 201
        govde = yanit.json()
        assert govde["token_type"] == "bearer"
        assert decode_access_token(govde["access_token"]) is not None
    finally:
        asyncio.run(_kullaniciyi_sil(eposta))


def test_register_yinelenen_eposta_409_doner(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.verify_identity", _nvi_sonucu(True))
    yanit = client.post("/api/auth/register", json=_kayit_govdesi(DEMO_EMAIL, GECERLI_TCKN_2))

    assert yanit.status_code == 409
    assert yanit.json()["error"]["code"] == "conflict"


def test_register_gecersiz_tckn_saglama_422_doner(client, monkeypatch):
    """Saglama (checksum) gecmeyen bir numara icin NVI'ye HIC istek atilmamali."""
    cagrildi = False

    async def _cagrilirsa_isaretle(**kwargs):
        nonlocal cagrildi
        cagrildi = True
        return True

    monkeypatch.setattr("app.api.routes.auth.verify_identity", _cagrilirsa_isaretle)

    yanit = client.post(
        "/api/auth/register",
        json=_kayit_govdesi("gecersiz-tckn@example.com", "12345678900"),
    )

    assert yanit.status_code == 422
    assert yanit.json()["error"]["code"] == "business_rule_error"
    assert "geçersiz" in yanit.json()["error"]["message"]
    assert cagrildi is False


def test_register_nvi_dogrulamasi_basarisiz_422_doner(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.verify_identity", _nvi_sonucu(False))

    yanit = client.post(
        "/api/auth/register",
        json=_kayit_govdesi("nvi-basarisiz@example.com", GECERLI_TCKN_5),
    )

    assert yanit.status_code == 422
    assert yanit.json()["error"]["code"] == "business_rule_error"
    assert "nüfus kayıtlarıyla eşleşmiyor" in yanit.json()["error"]["message"]


def test_register_nvi_ulasilamiyor_503_doner(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.verify_identity", _nvi_sonucu(None))

    yanit = client.post(
        "/api/auth/register",
        json=_kayit_govdesi("nvi-ulasilamiyor@example.com", GECERLI_TCKN_6),
    )

    assert yanit.status_code == 503
    assert yanit.json()["error"]["code"] == "service_unavailable"
    assert "ulaşılamıyor" in yanit.json()["error"]["message"]


def test_register_nvi_dogrulamasi_basarili_kullanici_olusturur(client, monkeypatch):
    import asyncio

    monkeypatch.setattr("app.api.routes.auth.verify_identity", _nvi_sonucu(True))
    eposta = "nvi-basarili@example.com"
    try:
        kayit = client.post("/api/auth/register", json=_kayit_govdesi(eposta, GECERLI_TCKN_7))
        assert kayit.status_code == 201
        token = kayit.json()["access_token"]

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert me["tckn_last4"] == GECERLI_TCKN_7[-4:]
        assert me["birth_date"] == "1990-01-01"
        assert me["phone_number"] == "05551234567"
        # ham TCKN ya da hash'i hicbir yanitta yer almamali
        assert GECERLI_TCKN_7 not in kayit.text
        assert GECERLI_TCKN_7 not in str(me)
        assert "tckn_hash" not in me
        assert "tckn" not in me
    finally:
        asyncio.run(_kullaniciyi_sil(eposta))


def test_register_nvi_bypass_ayari_dogrulamayi_atlar(client, override_settings):
    """`nvi_verification_enabled=False` iken NVI'ye HIC gidilmeden kayit basarili olur."""
    import asyncio

    override_settings(nvi_verification_enabled=False)
    eposta = "nvi-bypass@example.com"
    try:
        yanit = client.post("/api/auth/register", json=_kayit_govdesi(eposta, GECERLI_TCKN_8))

        assert yanit.status_code == 201
    finally:
        asyncio.run(_kullaniciyi_sil(eposta))


def test_me_onboarding_completed_alanini_dondurur(client, auth):
    yanit = client.get("/api/auth/me", headers=auth)

    assert yanit.status_code == 200
    assert yanit.json()["onboarding_completed"] is True  # demo kullanici seed'de true


def test_yeni_kayitli_kullanici_onboarding_completed_false_baslar(client, monkeypatch):
    import asyncio

    monkeypatch.setattr("app.api.routes.auth.verify_identity", _nvi_sonucu(True))
    eposta = "onboarding-test-flag@example.com"
    try:
        kayit = client.post("/api/auth/register", json=_kayit_govdesi(eposta, GECERLI_TCKN_3))
        token = kayit.json()["access_token"]

        yanit = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert yanit.json()["onboarding_completed"] is False
    finally:
        asyncio.run(_kullaniciyi_sil(eposta))


def test_onboarding_complete_risk_toleransini_ve_bayragi_gunceller(client, monkeypatch):
    import asyncio

    monkeypatch.setattr("app.api.routes.auth.verify_identity", _nvi_sonucu(True))
    eposta = "onboarding-test-complete@example.com"
    try:
        kayit = client.post("/api/auth/register", json=_kayit_govdesi(eposta, GECERLI_TCKN_4))
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
