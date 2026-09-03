"""`app.core.quantity` - adet kurallari.

Bu modulun VAROLUS SEBEBI iki cagiranin (oneri motoru ve emir dogrulama)
AYNI kurali kullanmasi. Testler bu yuzden yalnizca yuvarlamayi degil,
`round_quantity` ciktisinin `is_valid_quantity`'den GECTIGINI de dogrular -
ikisi ayrisirsa oneri kendi onerdigi adedi reddettirir.
"""

from __future__ import annotations

import pytest

from app.core.quantity import (
    CEYREK_ADIM,
    invalid_quantity_message,
    is_indivisible,
    is_quarter_step,
    is_valid_quantity,
    round_quantity,
)

BOLUNMEZ = ["STOCK", "USA_STOCK", "EU_STOCK", "ETF", "GOLD", "COMMODITY", "BOND"]


@pytest.mark.parametrize("sinif", BOLUNMEZ)
def test_bolunmez_siniflar_tam_adete_yuvarlanir(sinif):
    assert round_quantity(1.99, sinif) == 1.0
    assert is_indivisible(sinif)


def test_sinif_buyuk_kucuk_harften_bagimsizdir():
    """Repo satirlari 'stock', tool ciktilari 'STOCK' donebiliyor."""
    assert round_quantity(2.7, "stock") == round_quantity(2.7, "STOCK") == 2.0


def test_hisse_kusuratli_onerilmez():
    """Regresyon: INTC 4.246 TL oldugu icin 'ucuz' sayilip 1,18 adet
    onerilmisti. Bolunebilirlik FIYATA gore degil SINIFA gore belirlenir."""
    assert round_quantity(1.18, "USA_STOCK") == 1.0


def test_doviz_ceyrek_adimlara_yuvarlanir():
    assert is_quarter_step("FOREX")
    assert round_quantity(1.80, "FOREX") == 1.75
    assert round_quantity(0.99, "FOREX") == 0.75
    assert round_quantity(2.00, "FOREX") == 2.00


def test_kripto_serbest_ondalik_alir():
    """BTC 3,8 milyon TL; tam adet zorunlu olsaydi 5.000 TL'lik limitle
    HIC alinamazdi."""
    assert round_quantity(0.0013157894, "CRYPTO") == pytest.approx(0.001315, abs=1e-9)
    assert round_quantity(0.0000001, "CRYPTO") == 0.0


def test_tanimsiz_sinif_en_kisitlayici_kurala_duser():
    """Yeni bir varlik sinifi eklenip buraya yazilmazsa, sistem kusuratli
    islem uretmek yerine tam adete duser - guvenli taraf."""
    assert round_quantity(3.9, "YENI_SINIF") == 3.0
    assert round_quantity(3.9, None) == 3.0


@pytest.mark.parametrize("ham", [0.0, -1.0, -0.0001])
def test_pozitif_olmayan_adet_sifira_duser(ham):
    assert round_quantity(ham, "STOCK") == 0.0


def test_sifir_sonuc_hata_degil_alinamaz_demektir():
    """LLY 57.222 TL iken 5.000 TL limitle 0 adet cikar; cagiran bunu
    'bu butceyle alinamaz' diye yorumlar."""
    assert round_quantity(5_000 / 57_222, "USA_STOCK") == 0.0


def test_kayan_nokta_toleransi_tam_adedi_asagi_dusurmez():
    """0.75 gibi degerler ikilik tabanda tam temsil edilmez; tolerans
    olmadan `floor(3.0000000001)` yerine `floor(2.9999999999)` riski var."""
    assert round_quantity(3.0, "STOCK") == 3.0
    assert round_quantity(1.5 / CEYREK_ADIM * CEYREK_ADIM, "FOREX") == 1.5


# --- Dogrulama tarafi: yuvarlama ile TUTARLI olmak zorunda ----------------


@pytest.mark.parametrize(
    "sinif,ham",
    [(s, h) for s in [*BOLUNMEZ, "FOREX", "CRYPTO"] for h in (1.18, 3.7, 12.34, 0.9)],
)
def test_yuvarlanan_adet_dogrulamadan_gecer(sinif, ham):
    """Sozlesme: oneri motorunun urettigi adedi emir ucu REDDEDEMEZ."""
    adet = round_quantity(ham, sinif)
    if adet > 0:
        assert is_valid_quantity(adet, sinif), f"{sinif} icin {adet} reddedildi"


@pytest.mark.parametrize("adet", [0, -1, -0.5])
def test_pozitif_olmayan_adet_gecersizdir(adet):
    assert not is_valid_quantity(adet, "STOCK")


def test_doviz_ceyrek_disi_adet_reddedilir():
    assert is_valid_quantity(1.75, "FOREX")
    assert not is_valid_quantity(1.80, "FOREX")


def test_kripto_her_pozitif_adedi_kabul_eder():
    assert is_valid_quantity(0.000001, "CRYPTO")
    assert is_valid_quantity(1.23456789, "CRYPTO")


def test_hisse_kusuratli_adedi_reddeder():
    assert is_valid_quantity(5, "STOCK")
    assert not is_valid_quantity(5.5, "STOCK")


def test_hata_mesaji_sinifa_gore_degisir():
    """Frontend ceviri metniyle eslesmesi gereken tek yer burasi."""
    assert "0,25" in invalid_quantity_message("FOREX")
    assert "tam adet" in invalid_quantity_message("STOCK")
