"""Tahmin servisi: veri cekme, onbellek ve portfoy toplama.

ONBELLEK NEDEN GEREKLI
----------------------
Tek tahmin CPU'da ~250 ms surer. Onbelleksiz, market sayfasini acan her
kullanici her varlik icin bu bedeli oder; 42 varlikli bir liste ~10 saniye
CPU yakar. Ustelik SONUC AYNIDIR: model gunluk mumla calisir, gun icinde
tekrar hesaplamak ayni cikti icin bosuna is demektir.

`forecast_cache_hours` (varsayilan 12) bu yuzden var. Onbellek SURECE
AITTIR (bellek ici) - `report_cache` ile ayni sinirlama: sunucu yeniden
baslayinca bosalir, coklu worker'da her worker kendi kopyasini tutar.
Tahmin icin bu KABUL EDILEBILIR (rapor PDF'inden farkli olarak yeniden
uretilebilir, kaybi kullaniciya bir sey kaybettirmez).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import date, datetime

from app.config import settings
from app.forecast import engine
from app.forecast import model as tahmin_modeli
from app.forecast.types import Tahmin
from app.repositories.deps import get_market_repository, get_portfolio_repository

logger = logging.getLogger(__name__)

#: {sembol: (uretim_zamani_monotonic, Tahmin)}
_onbellek: dict[str, tuple[float, Tahmin]] = {}
_onbellek_kilidi = threading.Lock()

#: Modelin gecmis penceresini doldurmak icin cekilecek takvim gunu.
#: 512 IS gunu ~ 730 takvim gunu; bolme degil carpma ile guvenli paya
#: aliniyor (tatiller, veri bosluklari).
_GECMIS_TAKVIM_GUNU = 900


def acik_mi() -> bool:
    """Tahmin ozelligi kullanilabilir mi? (API katmani bunu sorar)"""
    return tahmin_modeli.yuklu_mu()


def _onbellekten(sembol: str) -> Tahmin | None:
    with _onbellek_kilidi:
        kayit = _onbellek.get(sembol)
        if kayit is None:
            return None
        uretim, tahmin = kayit
        if time.monotonic() - uretim > settings.forecast_cache_hours * 3600:
            _onbellek.pop(sembol, None)
            return None
        return tahmin


def _onbellege_yaz(sembol: str, tahmin: Tahmin) -> None:
    with _onbellek_kilidi:
        _onbellek[sembol] = (time.monotonic(), tahmin)


def _tarihe_cevir(deger) -> date | None:
    """Repo'dan gelen `ts` alanini `date`'e cevirir (tip degisken olabilir)."""
    if isinstance(deger, datetime):
        return deger.date()
    if isinstance(deger, date):
        return deger
    try:
        return datetime.fromisoformat(str(deger)[:19]).date()
    except (TypeError, ValueError):
        return None


async def varlik_tahmini(sembol: str, kategori: str = "") -> Tahmin | None:
    """Tek varlik icin tahmin; kapaliysa/veri yetersizse `None`."""
    if not acik_mi():
        return None

    onbellekli = _onbellekten(sembol)
    if onbellekli is not None:
        return onbellekli

    mumlar = await get_market_repository().get_candles(
        symbol=sembol, interval="1d", days=_GECMIS_TAKVIM_GUNU
    )
    if not mumlar:
        return None

    kapanislar = [float(m["close"]) for m in mumlar if m.get("close")]
    son_tarih = _tarihe_cevir(mumlar[-1].get("ts"))
    if son_tarih is None or not kapanislar:
        return None

    # Model cagrisi CPU-YOGUN ve SENKRON: event loop'u bloklamak, ayni anda
    # akan sohbet token'larini da durdurur (belge ajaninda ayni desen).
    tahmin = await asyncio.to_thread(engine.tahmin_uret, sembol, kapanislar, son_tarih, kategori)
    if tahmin is not None:
        _onbellege_yaz(sembol, tahmin)
    return tahmin


#: Para birimi -> o birimin TL karsiligini tutan varlik sembolu.
#: Portfoy TL BAZLI gosterildigi icin yabanci varliklarin tahmini kurla
#: carpilmalidir (bkz. `portfoy_tahmini` docstring'i).
_KUR_SEMBOLLERI = {"USD": "USD/TRY", "EUR": "EUR/TRY"}


async def _kur_carpani(para_birimi: str, adim: int, ufuk: int) -> float:
    """`adim`. gunde 1 birim yabanci paranin TL karsiliginin BUYUME orani.

    TRY icin her zaman 1.0. Kur varliginin kendi tahmini yoksa 1.0 doner
    (yani kur sabit varsayilir) - bu, tahmini oldugundan KUCUK gosterir
    ama uydurmaktan iyidir.
    """
    if para_birimi == "TRY":
        return 1.0

    sembol = _KUR_SEMBOLLERI.get(para_birimi)
    if not sembol:
        return 1.0

    kur = await varlik_tahmini(sembol, "Döviz (Fiat)")
    if kur is None or adim >= len(kur.noktalar) or kur.son_fiyat <= 0:
        return 1.0
    return kur.noktalar[adim].deger / kur.son_fiyat


async def _tl_bazina_cevir(
    tahmin: Tahmin, holding: dict, adet: float, para_birimi: str
) -> Tahmin | None:
    """Yabanci para cinsi bir varligin tahminini TL bazina cevirir.

    Model YEREL para biriminde tahmin uretir (AAPL -> USD). Portfoy grafigi
    TL bazlidir. Cevirim iki carpandan olusur:

        TL_deger(i) = bugunku_TL_birim_fiyat
                      × yerel_buyume(i)     (modelden: nokta / son_fiyat)
                      × kur_buyume(i)       (USD/TRY tahmininden)

    `yerel_buyume` bir ORANDIR, para biriminden bagimsizdir - bu yuzden
    modelin yerel cikitisi dogrudan kullanilabilir. Bugunku TL birim fiyat
    `market_value_try / adet` ile bulunur (kur zaten icinde).
    """
    tl_birim = float(holding.get("market_value_try") or 0) / adet if adet else 0.0
    if tl_birim <= 0 or tahmin.son_fiyat <= 0:
        logger.info(
            "TL cevirimi yapilamadi, portfoy tahmini iptal",
            extra={"sembol": tahmin.sembol},
        )
        return None

    yeni_noktalar = []
    for i, n in enumerate(tahmin.noktalar):
        kur = await _kur_carpani(para_birimi, i, len(tahmin.noktalar))
        yeni_noktalar.append(
            n.model_copy(
                update={
                    "deger": tl_birim * (n.deger / tahmin.son_fiyat) * kur,
                    "alt": tl_birim * (n.alt / tahmin.son_fiyat) * kur,
                    "ust": tl_birim * (n.ust / tahmin.son_fiyat) * kur,
                }
            )
        )

    return tahmin.model_copy(update={"noktalar": yeni_noktalar, "son_fiyat": tl_birim})


async def portfoy_tahmini(user_id: int) -> Tahmin | None:
    """Kullanicinin TUM varliklarini + nakdini tek TL tahmininde toplar.

    ⚠️ PARA BIRIMI DONUSUMU ZORUNLU. Portfoy grafigi TL BAZLIDIR ama
    varliklarin 24'u USD cinsindendir - AAPL'in tahmini dolar fiyatini
    adetle carpip toplamak DOLAR uretir, lira degil. Ustelik kuru SABIT
    saymak da yanlis olurdu: olculdu ki TL'nin deger kaybi gercek ve
    guclu bir trend (dovizde drift, naive hatasini %1,54'ten %0,79'a
    indiriyordu). Kuru sabit varsaymak, yabanci varliklarin TL degerini
    SISTEMATIK OLARAK dusuk gosterirdi.

    Bu yuzden her yabanci varlik icin ilgili kur varliginin (USD/TRY,
    EUR/TRY) TAHMINI de uretilir ve buyume orani carpan olarak uygulanir.

    Nakit tahmin EDILMEZ: TL'nin kendisi referans birimdir, sabit eklenir.
    """
    if not acik_mi():
        return None

    portfoy = get_portfolio_repository()
    holdings = await portfoy.get_holdings(user_id)
    if not holdings:
        return None

    ozet = await portfoy.get_summary(user_id)
    nakit = float((ozet or {}).get("cash_balance_try") or 0.0)

    varlik_tahminleri: list[tuple[Tahmin, float]] = []
    son_tarih: date | None = None

    for h in holdings:
        sembol = h.get("symbol")
        adet = float(h.get("quantity") or 0)
        if not sembol or adet <= 0:
            continue

        tahmin = await varlik_tahmini(sembol, str(h.get("asset_class") or ""))
        if tahmin is None:
            # Tek varligin tahmini uretilemezse portfoy tahmini YAPILMAZ:
            # eksik varlikla toplamak, kullaniciya portfoyun oldugundan
            # KUCUK gorunmesine yol acar - sessiz ve yaniltici bir hata.
            logger.info(
                "portfoy tahmini iptal: bir varlik tahmin edilemedi",
                extra={"sembol": sembol},
            )
            return None

        para_birimi = str(h.get("currency") or "TRY").upper()
        if para_birimi != "TRY":
            tahmin = await _tl_bazina_cevir(tahmin, h, adet, para_birimi)
            if tahmin is None:
                return None

        varlik_tahminleri.append((tahmin, adet))
        bu_tarih = date.fromisoformat(tahmin.son_tarih)
        son_tarih = bu_tarih if son_tarih is None else min(son_tarih, bu_tarih)

    if not varlik_tahminleri or son_tarih is None:
        return None

    return engine.portfoy_tahmini_birlestir(varlik_tahminleri, nakit, son_tarih)
