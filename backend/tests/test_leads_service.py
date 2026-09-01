"""Lead tarama orkestrasyonu testleri (bellek ici repository ile).

GERCEK VERITABANINA DOKUNMAZ: `database_url` bilerek bosaltilir, boylece
`deps.py` bellek ici repository'ye duser. Mail gonderimi de stub'lanir -
hicbir SMTP baglantisi acilmaz.
"""

import pytest

from app.config import settings
from app.leads import mailer
from app.repositories import in_memory
from app.repositories.deps import reset_repositories
from app.services import lead_rules as rules
from app.services import leads as service


def _kullanici(user_id: int, likit_para: float) -> dict:
    """Tum uygunluk kurallarindan gecen bir musteri.

    Portfoyu/islemi olmadigi icin `total_value_try=0` ve
    `days_since_activity=None` olur - yani "hic yatirim yapmamis,
    hareketsiz" hedef kitlesi.
    """
    return {
        "id": user_id,
        "first_name": f"Test{user_id}",
        "last_name": "Kullanici",
        "email": f"test{user_id}@example.com",
        "password_hash": "x",
        "risk_tolerance": None,
        "monthly_income": 30_000.0,
        "marketing_consent": True,
        "role": "customer",
        "likit_para": likit_para,
    }


@pytest.fixture
def bellek_ici(monkeypatch):
    monkeypatch.setattr(settings, "database_url", "")
    monkeypatch.setattr(settings, "lead_engine_enabled", True)
    monkeypatch.setattr(settings, "lead_scan_min_interval_minutes", 0)
    reset_repositories()
    for depo in (
        in_memory._LEAD_SCANS,
        in_memory._LEAD_QUEUE_ENTRIES,
        in_memory._LEAD_CONTACTS,
    ):
        depo.clear()
    yield
    for depo in (
        in_memory._LEAD_SCANS,
        in_memory._LEAD_QUEUE_ENTRIES,
        in_memory._LEAD_CONTACTS,
    ):
        depo.clear()
    reset_repositories()


@pytest.fixture
def otonom_kullanici(monkeypatch):
    """Atil bakiyesi BSD esiginin ALTINDA - otonom (mail) kuyruguna gider."""
    monkeypatch.setattr(in_memory, "_USERS", [_kullanici(101, 300_000.0)])


@pytest.fixture
def mail_sonucu(monkeypatch):
    """`send_lead_email`'i stub'lar; donecek durumu test belirler."""

    durum = {"status": "SENT", "error": None}

    async def _sahte_gonder(to_email: str, first_name: str) -> dict:
        return {
            "status": durum["status"],
            "to_email": to_email,
            "subject": mailer.KONU,
            "error": durum["error"],
        }

    monkeypatch.setattr(mailer, "is_configured", lambda: True)
    monkeypatch.setattr(mailer, "send_lead_email", _sahte_gonder)
    return durum


def _temaslar(channel: str | None = None) -> list[dict]:
    return [c for c in in_memory._LEAD_CONTACTS if channel is None or c["channel"] == channel]


# --- motor anahtari ---------------------------------------------------------


async def test_motor_kapaliyken_force_ile_bile_tarama_calismaz(
    bellek_ici, otonom_kullanici, mail_sonucu, monkeypatch
):
    # Regresyon: `LEAD_ENGINE_ENABLED` eskiden yalnizca acilis gorevini
    # kapatiyordu; `POST /api/leads/scan` (force=true) yine tam tarama
    # yapip GERCEK mail gonderebiliyordu.
    monkeypatch.setattr(settings, "lead_engine_enabled", False)

    sonuc = await service.tarama_calistir(trigger="manual", force=True)

    assert sonuc["skipped"] is True
    assert in_memory._LEAD_SCANS == []
    assert _temaslar() == []


# --- mail gonderim yollari --------------------------------------------------


async def test_basarili_gonderim_sent_temasi_birakir(bellek_ici, otonom_kullanici, mail_sonucu):
    sonuc = await service.tarama_calistir(trigger="test", force=True)

    assert sonuc["autonomous_count"] == 1
    assert sonuc["emailed_count"] == 1
    temaslar = _temaslar("EMAIL")
    assert len(temaslar) == 1
    assert temaslar[0]["status"] == "SENT"


async def test_basarisiz_gonderim_sent_olarak_KALMAZ(bellek_ici, otonom_kullanici, mail_sonucu):
    # Claim, gonderimden ONCE `SENT` yazar. Gonderim patlarsa bu kayit
    # `FAILED`'a cevrilmeli; aksi halde kullanici hic mail almadigi halde
    # sogutma penceresine kilitlenirdi.
    mail_sonucu["status"] = "FAILED"
    mail_sonucu["error"] = "baglanti reddedildi"

    sonuc = await service.tarama_calistir(trigger="test", force=True)

    assert sonuc["emailed_count"] == 0
    temaslar = _temaslar("EMAIL")
    assert len(temaslar) == 1
    assert temaslar[0]["status"] == "FAILED"


async def test_gmail_yapilandirilmamissa_hic_temas_kaydi_acilmaz(
    bellek_ici, otonom_kullanici, monkeypatch
):
    # Regresyon: eskiden her kullanici icin bos yere claim acilip hemen
    # `SKIPPED`'e cevriliyordu. Artik tarama basinda bir kez kontrol edilir.
    monkeypatch.setattr(mailer, "is_configured", lambda: False)

    sonuc = await service.tarama_calistir(trigger="test", force=True)

    assert sonuc["autonomous_count"] == 1  # kuyruk yine dolar
    assert sonuc["emailed_count"] == 0
    assert _temaslar() == []


async def test_kimlik_alanlari_kuyruk_satirina_tasinir(
    bellek_ici, otonom_kullanici, mail_sonucu, monkeypatch
):
    # Telefon/dogum tarihi/TCKN son 4, danisman ekranindaki tabloda
    # gosterilir; repository katmani bunlari `users` kaydindan satira
    # tasimazsa ekran bos sutunlar gosterir.
    kullanici = _kullanici(101, 300_000.0)
    kullanici.update(
        {"phone_number": "+905321112233", "birth_date": "1985-04-12", "tckn_last4": "4821"}
    )
    monkeypatch.setattr(in_memory, "_USERS", [kullanici])

    await service.tarama_calistir(trigger="test", force=True)
    liste = await service.otonom_kuyruk_getir()

    satir = liste["items"][0]
    assert satir["phone_number"] == "+905321112233"
    assert satir["birth_date"] == "1985-04-12"
    assert satir["tckn_last4"] == "4821"


# --- BSD kuyrugu ------------------------------------------------------------


async def test_bsd_kuyruguna_dusen_icin_temas_kaydi_acilmaz(bellek_ici, mail_sonucu, monkeypatch):
    # Regresyon: BSD kuyruguna dusmek eskiden `SENT` temasi yaziyordu, yani
    # kimse aramasa bile kisi sogutmaya girip sonraki taramalarda kuyruktan
    # sessizce kayboluyordu. BSD kuyrugu bir ONERIDIR, temas degil.
    monkeypatch.setattr(in_memory, "_USERS", [_kullanici(102, 700_000.0)])

    sonuc = await service.tarama_calistir(trigger="test", force=True)

    assert sonuc["bsd_count"] == 1
    assert _temaslar() == []

    # Ikinci tarama: kisi HALA BSD kuyrugunda gorunmeli.
    ikinci = await service.tarama_calistir(trigger="test", force=True)

    assert ikinci["bsd_count"] == 1


async def test_mail_gonderilen_kullanici_sonraki_taramada_listede_kalir(
    bellek_ici, otonom_kullanici, mail_sonucu
):
    # Mail gidince kisi sogutmaya girer ve sonraki taramada EXCLUDED olur -
    # ama "kime mail gitti" listesi `lead_contacts`'tan okundugu icin
    # gorunmeye devam etmeli.
    await service.tarama_calistir(trigger="test", force=True)
    ikinci = await service.tarama_calistir(trigger="test", force=True)

    assert ikinci["excluded_count"] == 1  # sogutma dogru calisiyor
    assert ikinci["emailed_count"] == 0  # ikinci kez mail GITMEZ

    liste = await service.otonom_kuyruk_getir()
    assert [item["user_id"] for item in liste["items"]] == [101]
    assert liste["items"][0]["mail_gonderildi"] is True


async def test_mail_gitmeyen_otonom_kullanici_yine_de_listede_gorunur(
    bellek_ici, otonom_kullanici, monkeypatch
):
    # Regresyon: otonom liste yalnizca `lead_contacts`'tan okunsaydi, Gmail
    # kapaliyken (ya da kota/fren devredeyken) kisi otonom kuyruga girdigi
    # halde HICBIR listede gorunmezdi - ekranda sessiz bir bosluk.
    monkeypatch.setattr(mailer, "is_configured", lambda: False)

    sonuc = await service.tarama_calistir(trigger="test", force=True)
    assert sonuc["autonomous_count"] == 1
    assert sonuc["emailed_count"] == 0

    liste = await service.otonom_kuyruk_getir()

    assert [item["user_id"] for item in liste["items"]] == [101]
    assert liste["items"][0]["mail_gonderildi"] is False


# --- kota ve ardisik hata freni ---------------------------------------------


async def test_kota_basariyi_degil_DENEMEYI_sayar(bellek_ici, mail_sonucu, monkeypatch, caplog):
    # Regresyon: kota `emailed_count`'a bakiyordu; SMTP surekli hata
    # verdiginde sayac hic artmadigi icin sinir devreye girmezdi.
    monkeypatch.setattr(rules, "MAX_EMAILS_PER_SCAN", 2)
    monkeypatch.setattr(rules, "MAX_ARDISIK_MAIL_HATASI", 99)  # fren devrede olmasin
    monkeypatch.setattr(in_memory, "_USERS", [_kullanici(200 + i, 300_000.0) for i in range(5)])
    mail_sonucu["status"] = "FAILED"
    mail_sonucu["error"] = "smtp bozuk"

    sonuc = await service.tarama_calistir(trigger="test", force=True)

    assert sonuc["autonomous_count"] == 5  # hepsi kuyruga yazilir
    assert len(_temaslar("EMAIL")) == 2  # ama yalnizca 2 DENEME yapilir


async def test_ardisik_hata_sonrasi_gonderim_durur(bellek_ici, mail_sonucu, monkeypatch):
    monkeypatch.setattr(rules, "MAX_EMAILS_PER_SCAN", 99)  # kota devrede olmasin
    monkeypatch.setattr(rules, "MAX_ARDISIK_MAIL_HATASI", 3)
    monkeypatch.setattr(in_memory, "_USERS", [_kullanici(300 + i, 300_000.0) for i in range(10)])
    mail_sonucu["status"] = "FAILED"
    mail_sonucu["error"] = "smtp coktu"

    sonuc = await service.tarama_calistir(trigger="test", force=True)

    assert sonuc["autonomous_count"] == 10
    assert len(_temaslar("EMAIL")) == 3  # 3 hatadan sonra pes eder


# --- rol filtresi -----------------------------------------------------------


async def test_danisman_hesaplari_hic_taranmaz(bellek_ici, mail_sonucu, monkeypatch):
    # Regresyon: view'de rol filtresi yoktu; danisman hesabi da bir lead
    # gibi taranip mail alabiliyordu.
    danisman = _kullanici(400, 300_000.0)
    danisman["role"] = "advisor"
    monkeypatch.setattr(in_memory, "_USERS", [danisman])

    sonuc = await service.tarama_calistir(trigger="test", force=True)

    assert sonuc["scanned_count"] == 0
    assert _temaslar() == []
