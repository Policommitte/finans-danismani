"""`/api/auth` - giris, kayit, profil ve onboarding.

`user_id` HICBIR ZAMAN URL ya da govde ile tasinmaz; token'dan cozulur
(mimari v4 bolum 10.2). Bu yuzden `/me` deseni kullanilir ve buradaki
testler bir istegin baskasinin kimligini yazamadigini da dogrular.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.api.routes import auth as auth_rotasi
from app.auth.security import create_access_token
from tests.conftest import DEMO_EMAIL, DEMO_PASSWORD, DEMO_USER_ID


def _checksum_tamamla(ilk_dokuz: str) -> str:
    h = [int(k) for k in ilk_dokuz]
    onuncu = ((sum(h[0:9:2]) * 7) - sum(h[1:8:2])) % 10
    return f"{ilk_dokuz}{onuncu}{(sum(h) + onuncu) % 10}"


GECERLI_TCKN = _checksum_tamamla("246813579")


def kayit_govdesi(**degisiklik) -> dict:
    govde = {
        "first_name": "Yeni",
        "last_name": "Kullanici",
        "email": "yeni.kullanici@example.com",
        "password": "guclu-parola-123",
        "tckn": GECERLI_TCKN,
        "birth_date": "1990-05-17",
        "phone_number": "+905301112233",
    }
    govde.update(degisiklik)
    return govde


@pytest.fixture
def nvi(monkeypatch):
    """NVI SOAP servisini degistirir - test HICBIR kosulda aga cikmaz.

    ⚠️ Yamalanan yer `app.api.routes.auth.verify_identity`, kaynak modul
    DEGIL: rota `from app.services.nvi import verify_identity` yaptigi icin
    ismi kendi modulune BAGLAMISTIR; kaynagi yamalamak rotayi etkilemez.
    """

    def _kur(sonuc=True):
        cagrilar: list[dict] = []

        async def _sahte(**kwargs):
            cagrilar.append(kwargs)
            return sonuc

        monkeypatch.setattr(auth_rotasi, "verify_identity", _sahte)
        return cagrilar

    return _kur


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


def test_gecersiz_tckn_NVI_ye_GITMEDEN_reddedilir(client, nvi, temiz_veri):
    """Ucretsiz on-eleme: bariz gecersiz numara icin dis servise hic istek
    atilmamali."""
    cagrilar = nvi(True)
    yanit = client.post("/api/auth/register", json=kayit_govdesi(tckn="12345678901"))
    assert yanit.status_code == 422
    assert cagrilar == []


def test_kayitli_eposta_409_verir(client, nvi, temiz_veri):
    nvi(True)
    yanit = client.post("/api/auth/register", json=kayit_govdesi(email=DEMO_EMAIL))
    assert yanit.status_code == 409
    assert yanit.json()["error"]["code"] == "conflict"


def test_nvi_ulasilamazsa_503_verir(client, nvi, temiz_veri):
    """⚠️ `None` KESIN bir "false" DEGILDIR: biri "kimlik uyusmuyor",
    digeri "su an bilmiyoruz" demektir - kullanici farkli mesaj gormeli."""
    nvi(None)
    yanit = client.post("/api/auth/register", json=kayit_govdesi())
    assert yanit.status_code == 503
    assert yanit.json()["error"]["code"] == "service_unavailable"


def test_nufus_kaydiyla_eslesmeyen_bilgi_422_verir(client, nvi, temiz_veri):
    nvi(False)
    yanit = client.post("/api/auth/register", json=kayit_govdesi())
    assert yanit.status_code == 422
    assert yanit.json()["error"]["code"] == "business_rule_error"


@pytest.mark.parametrize(
    "bozukluk",
    [
        {"email": "gecersiz-eposta"},
        {"tckn": "123"},
        {"birth_date": "gecersiz-tarih"},
        {"password": ""},
    ],
)
def test_bicimi_bozuk_kayit_govdesi_422_verir(client, bozukluk):
    assert client.post("/api/auth/register", json=kayit_govdesi(**bozukluk)).status_code == 422


def test_dogum_yili_NVI_ye_tarihten_turetilerek_gonderilir(client, nvi, temiz_veri):
    """NVI `DogumYili` bekler, tam tarih degil - cevrim rotada yapilir."""
    cagrilar = nvi(False)  # kaydi tamamlamadan cik
    client.post("/api/auth/register", json=kayit_govdesi(birth_date="1990-05-17"))

    assert cagrilar[0]["dogum_yili"] == date(1990, 5, 17).year
    assert cagrilar[0]["tckn"] == GECERLI_TCKN


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
