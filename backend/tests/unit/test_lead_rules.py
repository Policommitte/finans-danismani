"""`app.services.lead_rules` - lead uygunlugu, kuyruk secimi ve skor.

HEDEF KITLE hatirlatmasi: zaten yatirim yapmis musteriler DEGIL; bankada
120K-1M TL atil bakiyesi duran ama HIC yatirim yapmamis musteriler. Bu
yuzden esikler `total_value_try` (portfoy) uzerinden degil `likit_para`
(atil bakiye) uzerinden okunur.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.lead_rules import (
    BSD_ESIK_TRY,
    COOLDOWN_DAYS,
    MIN_ATIL_BAKIYE_TRY,
    MIN_INACTIVITY_DAYS,
    UST_SINIR_TRY,
    kuyruk_sec,
    potansiyel_skoru_hesapla,
    uygunluk_degerlendir,
)
from tests.helpers import lead_signal


def gun_once(gun: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=gun)


# --- Uygunluk -------------------------------------------------------------


def test_varsayilan_lead_uygundur():
    """Fabrika UYGUN bir lead uretir; asagidaki testler tek alani bozarak
    o kuralin tetiklendigini gosterir."""
    assert uygunluk_degerlendir(lead_signal(), None) is None


@pytest.mark.parametrize(
    "bozukluk,neden",
    [
        ({"marketing_consent": False}, "consent_missing"),
        ({"email": ""}, "email_missing"),
        ({"monthly_income": 0}, "income_below_threshold"),
        ({"total_value_try": 1.0}, "already_invested"),
        ({"likit_para": MIN_ATIL_BAKIYE_TRY - 1}, "balance_below_threshold"),
        ({"likit_para": UST_SINIR_TRY}, "above_upper_limit"),
        ({"days_since_activity": MIN_INACTIVITY_DAYS - 1}, "recently_active"),
    ],
)
def test_her_kural_kendi_nedenini_dondurur(bozukluk, neden):
    assert uygunluk_degerlendir(lead_signal(**bozukluk), None) == neden


def test_kurallar_sirayla_bakilir_ilk_basarisiz_kazanir():
    """Akis semasinda yukaridan asagiya: riza kontrolu gelirden ONCE."""
    kotu = lead_signal(marketing_consent=False, monthly_income=0, email="")
    assert uygunluk_degerlendir(kotu, None) == "consent_missing"


def test_esikler_kapsayicidir():
    """Alt esik DAHIL uygundur, ust esik DAHIL dislanir (SEG-03/SEG-04)."""
    assert uygunluk_degerlendir(lead_signal(likit_para=MIN_ATIL_BAKIYE_TRY), None) is None
    assert uygunluk_degerlendir(lead_signal(likit_para=UST_SINIR_TRY - 1), None) is None


def test_hic_aktivite_kaydi_olmayan_kullanici_hareketsizlik_kontrolunden_gecer():
    """ "Uzun suredir yatirim yapmamis ama atil bakiyesi olan" musteri tam
    da hedef kitledir."""
    assert uygunluk_degerlendir(lead_signal(days_since_activity=None), None) is None


def test_yatirimi_olan_kullanici_dislanir():
    """Kampanya hedefi HIC yatirim yapmamis musteri; portfoyu olan zaten
    yatirimci sayilir."""
    assert uygunluk_degerlendir(lead_signal(total_value_try=50_000), None) == "already_invested"


def test_sogutma_penceresi_icindeki_temas_engellenir():
    assert uygunluk_degerlendir(lead_signal(), gun_once(COOLDOWN_DAYS - 1)) == "cooldown_active"


def test_sogutma_penceresi_dolunca_yeniden_uygun_olur():
    assert uygunluk_degerlendir(lead_signal(), gun_once(COOLDOWN_DAYS + 1)) is None


def test_sogutma_penceresi_override_edilebilir():
    assert uygunluk_degerlendir(lead_signal(), gun_once(10), cooldown_days=5) is None
    assert uygunluk_degerlendir(lead_signal(), gun_once(10), cooldown_days=30) == "cooldown_active"


# --- Danisman gorusme sonucu ----------------------------------------------
#
# main'in `feature/danisman-ekrani` dali (PR #81) bu kurali `test_lead_rules.py`
# icine eklemisti; migrasyonda o duz dosya kaldirildigi icin testler BURAYA
# tasindi - kural kaybolmasin.


@pytest.mark.parametrize("sonuc", ["KABUL", "ISTEMIYOR"])
def test_danisman_dosyayi_kapattiysa_dislanir(sonuc):
    """Musteri oldu ya da acikca istemedi; kampanya onu tekrar hedeflememeli."""
    assert uygunluk_degerlendir(lead_signal(advisor_outcome=sonuc), None) == "advisor_closed"


@pytest.mark.parametrize(
    "sonuc",
    [
        # "ulasilamadi" bir KAPANIS DEGIL - kisi tekrar aranmali, kuyrukta kalir.
        "ULASILAMADI",
        # `ACIK` = "sonucu temizle"; kullanici hic isaretlenmemis sayilir.
        "ACIK",
    ],
)
def test_kapanis_olmayan_sonuclar_DISLAMAZ(sonuc):
    assert uygunluk_degerlendir(lead_signal(advisor_outcome=sonuc), None) is None


def test_danisman_karari_diger_tum_kurallardan_ONCE_gelir():
    """Rizasi da geliri de olmayan biri yine `advisor_closed` doner: danisman
    dosyayi kapattiysa daha SPESIFIK olan neden odur."""
    sinyal = lead_signal(advisor_outcome="ISTEMIYOR", marketing_consent=False, monthly_income=0)

    assert uygunluk_degerlendir(sinyal, None) == "advisor_closed"


# --- Kuyruk secimi (SEG-07/SEG-08) ---------------------------------------


@pytest.mark.parametrize(
    "bakiye,kuyruk",
    [
        (BSD_ESIK_TRY, "BSD"),  # esik DAHIL BSD'ye gider
        (BSD_ESIK_TRY + 1, "BSD"),
        (BSD_ESIK_TRY - 1, "AUTONOMOUS"),
        (MIN_ATIL_BAKIYE_TRY, "AUTONOMOUS"),
    ],
)
def test_kuyruk_atil_bakiyeye_gore_secilir(bakiye, kuyruk):
    assert kuyruk_sec(lead_signal(likit_para=bakiye)) == kuyruk


# --- Potansiyel skoru -----------------------------------------------------


def test_skor_bilesenleri_ust_sinirlarinda_kirpilir():
    yuksek = potansiyel_skoru_hesapla(
        lead_signal(likit_para=10_000_000, monthly_income=5_000_000, days_since_activity=9999)
    )
    assert yuksek["components"] == {"atil_bakiye": 45.0, "gelir": 30.0, "hareketsizlik": 15.0}
    assert yuksek["score"] == 90


def test_bos_sinyal_sifir_skor_verir():
    dusuk = potansiyel_skoru_hesapla(
        lead_signal(likit_para=0, monthly_income=0, days_since_activity=0)
    )
    assert dusuk["score"] == 0


def test_yuksek_bakiye_daha_yuksek_skor_alir():
    """Skor SIRALAMA icindir: BSD ekraninda kimi once aramali."""
    az = potansiyel_skoru_hesapla(lead_signal(likit_para=150_000))
    cok = potansiyel_skoru_hesapla(lead_signal(likit_para=900_000))
    assert cok["score"] > az["score"]


def test_bugun_aktif_kullaniciya_tavan_hareketsizlik_puani_verilmez():
    """Regresyon: `gun or 180` yazimi 0'i falsy sayip TAVAN puan verirdi.
    Bugun bu yola `recently_active` kurali yuzunden ulasilmiyor ama kural
    sirasi degisirse sessizce yanlis skor uretirdi."""
    aktif = potansiyel_skoru_hesapla(lead_signal(days_since_activity=0))
    kayitsiz = potansiyel_skoru_hesapla(lead_signal(days_since_activity=None))
    assert aktif["components"]["hareketsizlik"] == 0.0
    assert kayitsiz["components"]["hareketsizlik"] == 15.0


def test_skor_bilesenlerin_toplamina_esittir():
    sonuc = potansiyel_skoru_hesapla(lead_signal(likit_para=300_000, monthly_income=120_000))
    assert sonuc["score"] == round(sum(sonuc["components"].values()))


def test_gerekceler_turkce_ve_bos_degil():
    """BSD ekraninda insan danismana gosterilir."""
    gerekceler = potansiyel_skoru_hesapla(lead_signal(likit_para=BSD_ESIK_TRY))["reasons"]
    assert gerekceler
    assert any("BSD" in g for g in gerekceler)
    assert any("Hiç yatırım yapmamış" in g for g in gerekceler)


def test_aktivite_kaydi_yoksa_gerekce_bunu_soyler():
    gerekceler = potansiyel_skoru_hesapla(lead_signal(days_since_activity=None))["reasons"]
    assert any("Hiç işlem/sohbet aktivitesi kaydı yok" in g for g in gerekceler)


def test_skor_uygunlugu_etkilemez():
    """Skor yalnizca SIRALAMA icindir; uygunluk karari ayri kurallarda."""
    yuksek_skorlu_ama_uygunsuz = lead_signal(likit_para=900_000, marketing_consent=False)
    assert potansiyel_skoru_hesapla(yuksek_skorlu_ama_uygunsuz)["score"] > 0
    assert uygunluk_degerlendir(yuksek_skorlu_ama_uygunsuz, None) == "consent_missing"
