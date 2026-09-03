"""Lead uygunluk kurallari ve potansiyel skoru testleri.

Veritabani GEREKTIRMEZ: `lead_rules.py` saf ve deterministiktir - ayni
girdi her zaman ayni sonucu verir. Bu yuzden `db` isareti yoktur.
"""

from datetime import datetime, timedelta, timezone

from app.services import lead_rules as rules


def _signal(**overrides) -> dict:
    """Tum kurallardan GECEN bir sinyal; testler tek tek bozar."""
    signal = {
        "user_id": 1,
        "first_name": "Test",
        "last_name": "Kullanici",
        "email": "test@example.com",
        "marketing_consent": True,
        "monthly_income": 25_000.0,
        "total_value_try": 0.0,
        "likit_para": 300_000.0,
        "days_since_activity": None,
    }
    signal.update(overrides)
    return signal


# --- uygunluk_degerlendir ---------------------------------------------------


def test_tum_kurallardan_gecen_kullanici_uygundur():
    assert rules.uygunluk_degerlendir(_signal(), None) is None


def test_danisman_kabul_isaretlediyse_dislanir():
    # Musteri oldu; kampanya onu tekrar hedeflememeli.
    assert rules.uygunluk_degerlendir(_signal(advisor_outcome="KABUL"), None) == "advisor_closed"


def test_danisman_istemiyor_isaretlediyse_dislanir():
    assert (
        rules.uygunluk_degerlendir(_signal(advisor_outcome="ISTEMIYOR"), None) == "advisor_closed"
    )


def test_ulasilamadi_DISLAMAZ():
    # Regresyon: "ulasilamadi" bir kapanis DEGIL - kisi tekrar aranmali,
    # yani kuyrukta kalmali.
    assert rules.uygunluk_degerlendir(_signal(advisor_outcome="ULASILAMADI"), None) is None


def test_temizlenmis_sonuc_DISLAMAZ():
    # `ACIK` = "sonucu temizle"; kullanici hic isaretlenmemis sayilir.
    assert rules.uygunluk_degerlendir(_signal(advisor_outcome="ACIK"), None) is None


def test_danisman_karari_diger_tum_kurallardan_ONCE_gelir():
    # Rizasi da olmayan, geliri de olmayan biri "advisor_closed" doner:
    # danisman dosyayi kapattiysa daha spesifik olan neden odur.
    signal = _signal(advisor_outcome="ISTEMIYOR", marketing_consent=False, monthly_income=0)

    assert rules.uygunluk_degerlendir(signal, None) == "advisor_closed"


def test_riza_yoksa_dislanir():
    assert rules.uygunluk_degerlendir(_signal(marketing_consent=False), None) == "consent_missing"


def test_email_yoksa_dislanir():
    assert rules.uygunluk_degerlendir(_signal(email=""), None) == "email_missing"


def test_gelir_beyani_yoksa_dislanir():
    assert rules.uygunluk_degerlendir(_signal(monthly_income=0), None) == "income_below_threshold"


def test_zaten_yatirim_yapmis_kullanici_dislanir():
    # Hedef kitle "hic yatirim yapmamis" musteri; en kucuk bir portfoy bile
    # kullaniciyi kampanya disi birakir.
    assert rules.uygunluk_degerlendir(_signal(total_value_try=1.0), None) == "already_invested"


def test_atil_bakiye_alt_esigin_altindaysa_dislanir():
    signal = _signal(likit_para=rules.MIN_ATIL_BAKIYE_TRY - 1)

    assert rules.uygunluk_degerlendir(signal, None) == "balance_below_threshold"


def test_atil_bakiye_tam_alt_esikte_uygundur():
    signal = _signal(likit_para=rules.MIN_ATIL_BAKIYE_TRY)

    assert rules.uygunluk_degerlendir(signal, None) is None


def test_atil_bakiye_ust_sinirda_dislanir():
    # Ust sinir DAHILDIR: bu tutar ve uzeri "zaten ozel bankacilik musterisi".
    signal = _signal(likit_para=rules.UST_SINIR_TRY)

    assert rules.uygunluk_degerlendir(signal, None) == "above_upper_limit"


def test_atil_bakiye_ust_sinirin_hemen_altinda_uygundur():
    signal = _signal(likit_para=rules.UST_SINIR_TRY - 1)

    assert rules.uygunluk_degerlendir(signal, None) is None


def test_yakin_zamanda_aktif_kullanici_dislanir():
    signal = _signal(days_since_activity=rules.MIN_INACTIVITY_DAYS - 1)

    assert rules.uygunluk_degerlendir(signal, None) == "recently_active"


def test_hareketsizlik_tam_esikte_uygundur():
    signal = _signal(days_since_activity=rules.MIN_INACTIVITY_DAYS)

    assert rules.uygunluk_degerlendir(signal, None) is None


def test_hic_aktivite_kaydi_olmayan_kullanici_uygundur():
    # `days_since_activity=None` = hic islem/sohbet yok. "Uzun suredir
    # yatirim yapmamis ama atil bakiyesi olan" musteri tam da budur.
    assert rules.uygunluk_degerlendir(_signal(days_since_activity=None), None) is None


def test_sogutma_penceresi_icinde_dislanir():
    son_temas = datetime.now(timezone.utc) - timedelta(days=rules.COOLDOWN_DAYS - 1)

    assert rules.uygunluk_degerlendir(_signal(), son_temas) == "cooldown_active"


def test_sogutma_penceresi_disinda_uygundur():
    son_temas = datetime.now(timezone.utc) - timedelta(days=rules.COOLDOWN_DAYS + 1)

    assert rules.uygunluk_degerlendir(_signal(), son_temas) is None


def test_kurallar_sirayla_degerlendirilir_ilk_basarisiz_kazanir():
    # Hem riza yok hem bakiye dusuk: akis semasindaki sira geregi riza
    # kurali once gelir.
    signal = _signal(marketing_consent=False, likit_para=0)

    assert rules.uygunluk_degerlendir(signal, None) == "consent_missing"


# --- kuyruk_sec -------------------------------------------------------------


def test_bsd_esiginin_altindaki_bakiye_otonom_kuyruga_gider():
    assert rules.kuyruk_sec(_signal(likit_para=rules.BSD_ESIK_TRY - 1)) == "AUTONOMOUS"


def test_bsd_esigi_dahildir():
    assert rules.kuyruk_sec(_signal(likit_para=rules.BSD_ESIK_TRY)) == "BSD"


def test_bsd_esiginin_ustundeki_bakiye_bsd_kuyruguna_gider():
    assert rules.kuyruk_sec(_signal(likit_para=rules.BSD_ESIK_TRY + 100_000)) == "BSD"


# --- potansiyel_skoru_hesapla -----------------------------------------------


def test_skor_gecerli_aralikta_kalir():
    # Tavani zorlayan girdiler bile ust siniri asmamali.
    sonuc = rules.potansiyel_skoru_hesapla(
        _signal(likit_para=10_000_000, monthly_income=5_000_000, days_since_activity=9999)
    )

    assert 0 <= sonuc["score"] <= 90


def test_skor_deterministiktir():
    signal = _signal(likit_para=450_000, monthly_income=40_000, days_since_activity=120)

    assert rules.potansiyel_skoru_hesapla(signal) == rules.potansiyel_skoru_hesapla(signal)


def test_skor_bilesenleri_donulur():
    sonuc = rules.potansiyel_skoru_hesapla(_signal())

    assert set(sonuc["components"]) == {"atil_bakiye", "gelir", "hareketsizlik"}
    assert sonuc["reasons"]


def test_yuksek_bakiye_daha_yuksek_skor_uretir():
    dusuk = rules.potansiyel_skoru_hesapla(_signal(likit_para=150_000))
    yuksek = rules.potansiyel_skoru_hesapla(_signal(likit_para=900_000))

    assert yuksek["score"] > dusuk["score"]


def test_bugun_aktif_kullanici_tavan_hareketsizlik_puani_ALMAZ():
    # Regresyon: `days_since_activity or 180` yaziminda 0 falsy oldugu icin
    # bugun aktif olan kullanici "hic aktivite yok" sayilip TAVAN puan
    # aliyordu. Dogrusu: 0 gun hareketsizlik = 0 puan.
    sonuc = rules.potansiyel_skoru_hesapla(_signal(days_since_activity=0))

    assert sonuc["components"]["hareketsizlik"] == 0


def test_hic_aktivite_kaydi_yoksa_tavan_hareketsizlik_puani_alinir():
    sonuc = rules.potansiyel_skoru_hesapla(_signal(days_since_activity=None))

    assert sonuc["components"]["hareketsizlik"] == 15
