"""`/api/auth` - giris, kayit, profil ve onboarding.

`user_id` HICBIR ZAMAN URL ya da govde ile tasinmaz; token'dan cozulur
(mimari v4 bolum 10.2). Bu yuzden `/me` deseni kullanilir ve buradaki
testler bir istegin baskasinin kimligini yazamadigini da dogrular.
"""

from __future__ import annotations

import pytest

from app.auth.security import create_access_token
from tests.conftest import DEMO_EMAIL, DEMO_PASSWORD, DEMO_USER_ID


def kayit_govdesi(**degisiklik) -> dict:
    """`POST /api/auth/register` govdesi - GUNCEL sozlesme.

    ⚠️ Eskiden burada `tckn`, `birth_date`, `phone_number` ve NVI SOAP
    dogrulamasi vardi. O akis KALDIRILDI (bkz. `app/schemas/auth.py`
    ::RegisterRequest): kayit artik yalnizca e-posta + sifre ister,
    `account_number` ise "banka hesabi baglama" SIMULASYONUNDA girilir ve
    DOGRULANMAZ. Fazladan alanlar Pydantic tarafindan yok sayilir.
    """
    govde = {
        "email": "yeni.kullanici@example.com",
        "password": "guclu-parola-123",
    }
    govde.update(degisiklik)
    return govde


# --- Giris ----------------------------------------------------------------


def test_dogru_bilgilerle_giris_token_dondurur(client):
    yanit = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert yanit.status_code == 200

    govde = yanit.json()
    assert govde["token_type"] == "bearer"
    assert govde["expires_in"] > 0
    assert govde["access_token"]


def test_uretilen_token_korumali_uca_erisir(client):
    token = client.post(
        "/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    ).json()["access_token"]

    yanit = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert yanit.status_code == 200
    assert yanit.json()["email"] == DEMO_EMAIL


@pytest.mark.parametrize(
    "govde",
    [
        {"email": DEMO_EMAIL, "password": "yanlis-parola"},
        {"email": "hic-kayitli-degil@example.com", "password": DEMO_PASSWORD},
    ],
)
def test_yanlis_kimlik_bilgisi_401_verir(client, govde):
    assert client.post("/api/auth/login", json=govde).status_code == 401


def test_kullanici_yok_ile_parola_yanlis_AYNI_mesaji_verir(client):
    """Farkli mesaj vermek hangi e-postalarin kayitli oldugunu SIZDIRIR."""
    yanlis_parola = client.post(
        "/api/auth/login", json={"email": DEMO_EMAIL, "password": "x" * 12}
    ).json()["error"]["message"]
    yok = client.post(
        "/api/auth/login", json={"email": "yok@example.com", "password": "x" * 12}
    ).json()["error"]["message"]
    assert yanlis_parola == yok


# --- /me ------------------------------------------------------------------


def test_me_parola_ozetini_SIZDIRMAZ(client, auth):
    """`UserRepository.get_by_id` sozlesmesi: donen sozlukte
    `password_hash` YOKTUR."""
    govde = client.get("/api/auth/me", headers=auth).json()
    assert "password_hash" not in govde
    assert "tckn_hash" not in govde


def test_me_tckn_yi_yalnizca_maskeli_gosterir(client, auth):
    govde = client.get("/api/auth/me", headers=auth).json()
    assert govde["tckn_last4"] is None or len(govde["tckn_last4"]) == 4


def test_me_token_daki_kullaniciyi_doner_govdeyi_DEGIL(client):
    """Kimlik yalnizca token'dan gelir; istek govdesi/parametresi onu
    degistiremez."""
    ikinci_kullanici = create_access_token(2)
    govde = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {ikinci_kullanici}"},
        params={"user_id": DEMO_USER_ID},
    ).json()
    assert govde["id"] == 2


def test_silinmis_kullanicinin_token_i_gecersizdir(client):
    """Yetki kararlari her istekte DB'den okunur - elde kalmis token yetki
    tasimaya devam etmemeli."""
    yok_olan = create_access_token(999_999)
    yanit = client.get("/api/auth/me", headers={"Authorization": f"Bearer {yok_olan}"})
    assert yanit.status_code == 401


@pytest.mark.parametrize(
    "baslik",
    [
        {},
        {"Authorization": ""},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic a2xhc2lr"},
        {"Authorization": "Bearer bozuk.token.imza"},
    ],
)
def test_eksik_veya_bozuk_authorization_401_verir(client, baslik):
    assert client.get("/api/auth/me", headers=baslik).status_code == 401


# --- Kayit ----------------------------------------------------------------


def test_kayit_201_ve_kullanilabilir_token_doner(client, temiz_veri):
    """Kayit OTOMATIK GIRIS yapar: donen token dogrudan `/me`'ye gecer."""
    yanit = client.post("/api/auth/register", json=kayit_govdesi())
    assert yanit.status_code == 201

    govde = yanit.json()
    assert govde["token_type"] == "bearer"
    assert govde["expires_in"] > 0

    ben = client.get("/api/auth/me", headers={"Authorization": f"Bearer {govde['access_token']}"})
    assert ben.status_code == 200
    assert ben.json()["email"] == "yeni.kullanici@example.com"


def test_kayitli_eposta_409_verir(client, temiz_veri):
    yanit = client.post("/api/auth/register", json=kayit_govdesi(email=DEMO_EMAIL))
    assert yanit.status_code == 409
    assert yanit.json()["error"]["code"] == "conflict"


def test_yeni_kullanici_onboardinge_ZORLANIR(client, temiz_veri):
    """`onboarding_completed`/`has_seen_tour` false baslar - AppShell bir
    sonraki yuklemede anket akisini ve ardindan urun turunu acar. `True`
    baslasaydi yeni kullanici bos bir panele duserdi."""
    token = client.post("/api/auth/register", json=kayit_govdesi()).json()["access_token"]
    profil = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert profil["onboarding_completed"] is False
    assert profil["has_seen_tour"] is False


def test_ad_soyad_epostadan_turetilir(client, temiz_veri):
    """Kayit formunda ad/soyad alani YOK; e-postanin yerel kismi ayristirilir."""
    token = client.post(
        "/api/auth/register", json=kayit_govdesi(email="ayse.yilmaz@example.com")
    ).json()["access_token"]
    profil = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert (profil["first_name"], profil["last_name"]) == ("Ayse", "Yilmaz")


def test_hesap_numarasi_DOGRULANMADAN_kabul_edilir(client, temiz_veri):
    """Banka baglama bir SIMULASYON: numara gercek bir API'ye sorulmaz,
    yalnizca bicim (en fazla 9 hane) sinirlanir."""
    assert (
        client.post(
            "/api/auth/register", json=kayit_govdesi(account_number="000000001")
        ).status_code
        == 201
    )


@pytest.mark.parametrize(
    "bozukluk",
    [
        {"email": "gecersiz-eposta"},
        {"password": ""},
        {"password": "kisa"},
        {"account_number": "1234567890"},
    ],
)
def test_bicimi_bozuk_kayit_govdesi_422_verir(client, temiz_veri, bozukluk):
    assert client.post("/api/auth/register", json=kayit_govdesi(**bozukluk)).status_code == 422


@pytest.mark.parametrize("eksik", ["email", "password"])
def test_zorunlu_alan_eksikse_422_verir(client, temiz_veri, eksik):
    govde = kayit_govdesi()
    govde.pop(eksik)
    assert client.post("/api/auth/register", json=govde).status_code == 422


# --- Onboarding -----------------------------------------------------------


def test_onboarding_tamamlama_toleransi_yazar(client, auth, temiz_veri):
    yanit = client.post(
        "/api/auth/onboarding/complete", json={"risk_tolerance": "LOW"}, headers=auth
    )
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["risk_tolerance"] == "LOW"
    assert govde["onboarding_completed"] is True


@pytest.mark.parametrize("deger", ["ASIRI", "", "low"])
def test_taninmayan_risk_toleransi_reddedilir(client, auth, deger):
    yanit = client.post(
        "/api/auth/onboarding/complete", json={"risk_tolerance": deger}, headers=auth
    )
    assert yanit.status_code == 422


def test_onboarding_kimlik_dogrulamasi_ister(client):
    yanit = client.post("/api/auth/onboarding/complete", json={"risk_tolerance": "LOW"})
    assert yanit.status_code == 401
