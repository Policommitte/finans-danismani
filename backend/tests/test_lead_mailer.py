"""Gmail gonderim katmani testleri.

Veritabani ve AG GEREKTIRMEZ: `smtplib.SMTP_SSL` sahte bir sinifla
degistirilir, hicbir gercek mail gonderilmez.
"""

import pytest

from app.leads import mailer


class SahteSmtp:
    """`smtplib.SMTP_SSL` yerine gecer; gonderilenleri kaydeder."""

    #: Butun ornekler tarafindan paylasilan cagri kaydi.
    cagrilar: list[dict] = []
    #: Doluysa `send_message` bu istisnayi firlatir (hata yolu testi).
    hata: Exception | None = None

    def __init__(self, host, port, context=None, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._giris: tuple[str, str] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, kullanici, sifre):
        self._giris = (kullanici, sifre)

    def send_message(self, mesaj):
        if SahteSmtp.hata is not None:
            raise SahteSmtp.hata
        SahteSmtp.cagrilar.append(
            {
                "host": self.host,
                "port": self.port,
                "timeout": self.timeout,
                "giris": self._giris,
                "to": mesaj["To"],
                "from": mesaj["From"],
                "subject": mesaj["Subject"],
                "govde": mesaj.get_content(),
            }
        )


@pytest.fixture
def sahte_smtp(monkeypatch):
    SahteSmtp.cagrilar = []
    SahteSmtp.hata = None
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", SahteSmtp)
    return SahteSmtp


@pytest.fixture
def gmail_ayarli(override_settings):
    override_settings(
        gmail_sender_email="gonderen@example.com",
        gmail_app_password="app-sifresi",
        gmail_smtp_host="smtp.example.com",
        gmail_smtp_port=465,
        gmail_timeout_seconds=15,
        lead_email_redirect_to="",
    )


# --- is_configured ----------------------------------------------------------


def test_iki_alan_da_doluysa_yapilandirilmistir(gmail_ayarli):
    assert mailer.is_configured() is True


def test_sifre_bossa_yapilandirilmamistir(override_settings):
    override_settings(gmail_sender_email="gonderen@example.com", gmail_app_password="")

    assert mailer.is_configured() is False


def test_adres_bossa_yapilandirilmamistir(override_settings):
    override_settings(gmail_sender_email="", gmail_app_password="app-sifresi")

    assert mailer.is_configured() is False


# --- send_lead_email --------------------------------------------------------


async def test_yapilandirilmamissa_skipped_doner_ve_smtp_hic_cagrilmaz(
    override_settings, sahte_smtp
):
    override_settings(gmail_sender_email="", gmail_app_password="")

    sonuc = await mailer.send_lead_email("alici@example.com", "Test")

    assert sonuc["status"] == "SKIPPED"
    assert sonuc["error"] is None
    assert sahte_smtp.cagrilar == []


async def test_yapilandirilmissa_dogru_sunucu_ve_kimlikle_gonderilir(gmail_ayarli, sahte_smtp):
    sonuc = await mailer.send_lead_email("alici@example.com", "Test")

    assert sonuc["status"] == "SENT"
    assert len(sahte_smtp.cagrilar) == 1
    cagri = sahte_smtp.cagrilar[0]
    assert (cagri["host"], cagri["port"], cagri["timeout"]) == ("smtp.example.com", 465, 15)
    assert cagri["giris"] == ("gonderen@example.com", "app-sifresi")
    assert cagri["to"] == "alici@example.com"


async def test_redirect_ayarliyken_gercek_alici_redirect_adresidir(
    gmail_ayarli, override_settings, sahte_smtp
):
    # Demo guvenligi: seed adresleri teslim edilemez oldugu icin tum mailler
    # tek bir test adresine yonlendirilir, asil alici govdeye yazilir.
    override_settings(lead_email_redirect_to="test@example.com")

    sonuc = await mailer.send_lead_email("gercek@example.com", "Test")

    assert sonuc["to_email"] == "test@example.com"
    cagri = sahte_smtp.cagrilar[0]
    assert cagri["to"] == "test@example.com"
    assert "gercek@example.com" in cagri["govde"]


async def test_redirect_bosken_kullanicinin_kendi_adresine_gonderilir(gmail_ayarli, sahte_smtp):
    sonuc = await mailer.send_lead_email("gercek@example.com", "Test")

    assert sonuc["to_email"] == "gercek@example.com"
    assert sahte_smtp.cagrilar[0]["to"] == "gercek@example.com"


async def test_smtp_hata_firlatirsa_failed_doner_ve_istisna_sizmaz(gmail_ayarli, sahte_smtp):
    sahte_smtp.hata = OSError("baglanti reddedildi")

    sonuc = await mailer.send_lead_email("alici@example.com", "Test")

    assert sonuc["status"] == "FAILED"
    assert "baglanti reddedildi" in sonuc["error"]


async def test_mail_govdesi_portfoye_atif_YAPMAZ(gmail_ayarli, sahte_smtp):
    # Hedef kitle tanimi geregi HIC yatirim yapmamistir; "portfoyunuz"
    # demek var olmayan bir seye atif olurdu.
    await mailer.send_lead_email("alici@example.com", "Test")

    govde = sahte_smtp.cagrilar[0]["govde"].lower()
    assert "portföy" not in govde
    assert "Test" in sahte_smtp.cagrilar[0]["govde"]
