"""Varlik sinifina gore adet kurallari - TEK KAYNAK.

NEDEN AYRI MODUL
----------------
Ayni kural iki yerde gerekiyor: otonom oneri adedi hesaplarken
(`services/recommendation.py`) ve manuel emir dogrularken
(`services/trading.py`). Iki yere kopyalanirsa zamanla ayrisirlar - oneri
1,18 adet INTC onerirken emir ucu bunu reddederse kullanici arayuzun
verdigi bir sayida hata alir.

BOLUNEBILIRLIK FIYATA GORE DEGIL SINIFA GORE BELIRLENIR
-------------------------------------------------------
Ilk surum "fiyat >= 1000 ise kusuratli" diyordu; bu YANLISTI. INTC 4.246 TL
oldugu icin kusuratli sayildi ve 1,18 adet onerildi - oysa hisse senedi
bolunemez. Dogru olcut enstrumanin kendisidir.

UC KOVA
-------
1. TAM ADET  - hisse, ETF, gram altin, emtia, tahvil.
   Gram altin "0,3871 gram" diye alinmaz; emtia sozlesmesi de bolunmez.
2. CEYREK ADIM - yalnizca doviz. 0,25'in katlari (0,25 / 0,50 / 1,75 ...).
3. SERBEST   - yalnizca kripto. Tam adet zorunlu olsaydi BTC (3,8 milyon TL)
   5.000 TL'lik tek islem limitiyle HIC alinamazdi; kripto gercek hayatta da
   bolunerek alinir.
"""

from __future__ import annotations

import math

#: Tam adet alinan siniflar - kusuratli islem gercek hayatta yok.
BOLUNMEZ_SINIFLAR = frozenset(
    {"STOCK", "USA_STOCK", "EU_STOCK", "ETF", "GOLD", "COMMODITY", "BOND"}
)

#: Yalnizca doviz: 0,25'in katlari.
CEYREK_ADIMLI_SINIFLAR = frozenset({"FOREX"})
CEYREK_ADIM = 0.25

#: Yalnizca kripto: serbest ondalik.
SERBEST_SINIFLAR = frozenset({"CRYPTO"})
KRIPTO_BASAMAK = 6

#: Kayan nokta karsilastirmasinda tolerans (0.75 gibi degerler ikilik
#: tabanda tam temsil edilmez).
_TOLERANS = 1e-9


def _asset_class(asset_class: str | None) -> str:
    return (asset_class or "").upper()


def is_indivisible(asset_class: str | None) -> bool:
    return _asset_class(asset_class) in BOLUNMEZ_SINIFLAR


def is_quarter_step(asset_class: str | None) -> bool:
    return _asset_class(asset_class) in CEYREK_ADIMLI_SINIFLAR


def round_quantity(ham: float, asset_class: str | None) -> float:
    """Ham adedi sinifa gore ASAGI yuvarlar.

    Asagi yuvarlanir cunku adet bir BUTCEDEN turetilir; yukari yuvarlamak
    kullanicinin limitini ya da nakdini asardi.

    Sonuc 0 cikabilir (orn. tek islem limiti 5.000 TL iken LLY 57.222 TL).
    Bu bir hata degildir: cagiran 0'i "bu varlik bu butceyle alinamaz"
    olarak yorumlamalidir.
    """
    if ham <= 0:
        return 0.0
    if is_indivisible(asset_class):
        return float(math.floor(ham + _TOLERANS))
    if is_quarter_step(asset_class):
        return math.floor(ham / CEYREK_ADIM + _TOLERANS) * CEYREK_ADIM
    if _asset_class(asset_class) in SERBEST_SINIFLAR:
        carpan = 10**KRIPTO_BASAMAK
        return math.floor(ham * carpan) / carpan
    # Tanimsiz bir sinif gelirse EN KISITLAYICI kural uygulanir: tam adet.
    return float(math.floor(ham + _TOLERANS))


def is_valid_quantity(adet: float, asset_class: str | None) -> bool:
    """Kullanicinin girdigi adet bu sinif icin gecerli mi?"""
    if adet <= 0:
        return False
    if is_quarter_step(asset_class):
        return abs(adet / CEYREK_ADIM - round(adet / CEYREK_ADIM)) < 1e-6
    if _asset_class(asset_class) in SERBEST_SINIFLAR:
        return True
    return abs(adet - round(adet)) < 1e-9


def invalid_quantity_message(asset_class: str | None) -> str:
    """Kullaniciya gosterilecek hata metni (frontend cevirisiyle eslesir)."""
    if is_quarter_step(asset_class):
        return "Doviz emirleri 0,25'in katlari olmalidir."
    return "Bu varlik tam adet alinip satilir."
