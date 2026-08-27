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
bolunemez. Dogru olcut enstrumanin kendisidir: hisse ve ETF tam adet alinir,
kripto ve gram altin bolunebilir.
"""

from __future__ import annotations

import math

#: Tam adet alinan siniflar - kusuratli islem GERCEK HAYATTA YOK.
BOLUNMEZ_SINIFLAR = frozenset({"STOCK", "USA_STOCK", "EU_STOCK", "ETF"})

#: Bolunebilir siniflar ve gosterilecek ondalik basamak sayisi.
BOLUNEBILIR_BASAMAK: dict[str, int] = {
    "CRYPTO": 6,
    "GOLD": 4,
    "COMMODITY": 4,
    "BOND": 4,
    "FOREX": 2,
}
VARSAYILAN_BASAMAK = 4


def bolunmez_mi(asset_class: str | None) -> bool:
    return (asset_class or "").upper() in BOLUNMEZ_SINIFLAR


def adet_yuvarla(ham: float, asset_class: str | None) -> float:
    """Ham adedi sinifa gore ASAGI yuvarlar.

    Asagi yuvarlanir cunku adet bir BUTCEDEN turetilir; yukari yuvarlamak
    kullanicinin limitini ya da nakdini asardi.

    Bolunmez bir sinifta sonuc 0 cikabilir (orn. tek islem limiti 5.000 TL
    iken LLY 57.222 TL). Bu bir hata degildir: cagiran 0'i "bu varlik bu
    butceyle alinamaz" olarak yorumlamalidir.
    """
    if ham <= 0:
        return 0.0
    if bolunmez_mi(asset_class):
        return float(math.floor(ham))
    basamak = BOLUNEBILIR_BASAMAK.get((asset_class or "").upper(), VARSAYILAN_BASAMAK)
    return math.floor(ham * 10**basamak) / 10**basamak


def adet_gecerli_mi(adet: float, asset_class: str | None) -> bool:
    """Kullanicinin girdigi adet bu sinif icin gecerli mi?"""
    if adet <= 0:
        return False
    if bolunmez_mi(asset_class):
        return float(adet).is_integer()
    return True
