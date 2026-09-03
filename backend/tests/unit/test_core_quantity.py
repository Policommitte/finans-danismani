"""`app.core.quantity` - adet kurallari.

Bu modulun VAROLUS SEBEBI iki cagiranin (oneri motoru ve emir dogrulama)
AYNI kurali kullanmasi. Testler bu yuzden yalnizca yuvarlamayi degil,
`adet_yuvarla` ciktisinin `adet_gecerli_mi`'den GECTIGINI de dogrular -
ikisi ayrisirsa oneri kendi onerdigi adedi reddettirir.
"""

from __future__ import annotations

import pytest

from app.core.quantity import (
    CEYREK_ADIM,
    adet_gecerli_mi,
    adet_yuvarla,
    bolunmez_mi,
    ceyrek_adimli_mi,
    gecersiz_adet_mesaji,
)

BOLUNMEZ = ["STOCK", "USA_STOCK", "EU_STOCK", "ETF", "GOLD", "COMMODITY", "BOND"]


@pytest.mark.parametrize("sinif", BOLUNMEZ)
def test_bolunmez_siniflar_tam_adete_yuvarlanir(sinif):
    assert adet_yuvarla(1.99, sinif) == 1.0
    assert bolunmez_mi(sinif)


def test_sinif_buyuk_kucuk_harften_bagimsizdir():
    """Repo satirlari 'stock', tool ciktilari 'STOCK' donebiliyor."""
    assert adet_yuvarla(2.7, "stock") == adet_yuvarla(2.7, "STOCK") == 2.0


def test_hisse_kusuratli_onerilmez():
    """Regresyon: INTC 4.246 TL oldugu icin 'ucuz' sayilip 1,18 adet
    onerilmisti. Bolunebilirlik FIYATA gore degil SINIFA gore belirlenir."""
    assert adet_yuvarla(1.18, "USA_STOCK") == 1.0


def test_doviz_ceyrek_adimlara_yuvarlanir():
    assert ceyrek_adimli_mi("FOREX")
    assert adet_yuvarla(1.80, "FOREX") == 1.75
    assert adet_yuvarla(0.99, "FOREX") == 0.75
    assert adet_yuvarla(2.00, "FOREX") == 2.00


def test_kripto_serbest_ondalik_alir():
    """BTC 3,8 milyon TL; tam adet zorunlu olsaydi 5.000 TL'lik limitle
    HIC alinamazdi."""
    assert adet_yuvarla(0.0013157894, "CRYPTO") == pytest.approx(0.001315, abs=1e-9)
    assert adet_yuvarla(0.0000001, "CRYPTO") == 0.0


def test_tanimsiz_sinif_en_kisitlayici_kurala_duser():
    """Yeni bir varlik sinifi eklenip buraya yazilmazsa, sistem kusuratli
    islem uretmek yerine tam adete duser - guvenli taraf."""
    assert adet_yuvarla(3.9, "YENI_SINIF") == 3.0
    assert adet_yuvarla(3.9, None) == 3.0


@pytest.mark.parametrize("ham", [0.0, -1.0, -0.0001])
def test_pozitif_olmayan_adet_sifira_duser(ham):
    assert adet_yuvarla(ham, "STOCK") == 0.0


def test_sifir_sonuc_hata_degil_alinamaz_demektir():
    """LLY 57.222 TL iken 5.000 TL limitle 0 adet cikar; cagiran bunu
    'bu butceyle alinamaz' diye yorumlar."""
    assert adet_yuvarla(5_000 / 57_222, "USA_STOCK") == 0.0


def test_kayan_nokta_toleransi_tam_adedi_asagi_dusurmez():
    """0.75 gibi degerler ikilik tabanda tam temsil edilmez; tolerans
    olmadan `floor(3.0000000001)` yerine `floor(2.9999999999)` riski var."""
    assert adet_yuvarla(3.0, "STOCK") == 3.0
    assert adet_yuvarla(1.5 / CEYREK_ADIM * CEYREK_ADIM, "FOREX") == 1.5


# --- Dogrulama tarafi: yuvarlama ile TUTARLI olmak zorunda ----------------


@pytest.mark.parametrize(
    "sinif,ham",
    [(s, h) for s in [*BOLUNMEZ, "FOREX", "CRYPTO"] for h in (1.18, 3.7, 12.34, 0.9)],
)
def test_yuvarlanan_adet_dogrulamadan_gecer(sinif, ham):
    """Sozlesme: oneri motorunun urettigi adedi emir ucu REDDEDEMEZ."""
    adet = adet_yuvarla(ham, sinif)
    if adet > 0:
        assert adet_gecerli_mi(adet, sinif), f"{sinif} icin {adet} reddedildi"


@pytest.mark.parametrize("adet", [0, -1, -0.5])
def test_pozitif_olmayan_adet_gecersizdir(adet):
    assert not adet_gecerli_mi(adet, "STOCK")


def test_doviz_ceyrek_disi_adet_reddedilir():
    assert adet_gecerli_mi(1.75, "FOREX")
    assert not adet_gecerli_mi(1.80, "FOREX")


def test_kripto_her_pozitif_adedi_kabul_eder():
    assert adet_gecerli_mi(0.000001, "CRYPTO")
    assert adet_gecerli_mi(1.23456789, "CRYPTO")


def test_hisse_kusuratli_adedi_reddeder():
    assert adet_gecerli_mi(5, "STOCK")
    assert not adet_gecerli_mi(5.5, "STOCK")


def test_hata_mesaji_sinifa_gore_degisir():
    """Frontend ceviri metniyle eslesmesi gereken tek yer burasi."""
    assert "0,25" in gecersiz_adet_mesaji("FOREX")
    assert "tam adet" in gecersiz_adet_mesaji("STOCK")
