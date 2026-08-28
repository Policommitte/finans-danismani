"""Yahoo Finance'ten fiyat cekme ve `assets` metriklerini hesaplama.

Bu katman VERITABANINI BILMEZ - yalnizca Yahoo'dan seri ceker ve semanin
istedigi metrikleri uretir. Yazma isi `database.py` sorumlulugundadir.

METRIKLERIN SEMA ILE ILISKISI (db/v5_schema_and_data.sql bolum 2)
    current_price      -> serinin son kapanisi
    prev_close         -> bir onceki kapanis
    daily_change_pct   -> (current / prev_close - 1) * 100
    weekly_change_pct  -> 7 takvim gunu oncesine gore degisim
    yearly_change_pct  -> 365 takvim gunu oncesine gore degisim
    price_updated_at   -> yazma aninda now()

    Semadaki `prev_close = current_price / (1 + daily_change_pct/100)` bagi
    KORUNUR: iki deger de ayni seriden turedigi icin tutarlidir.

TAKVIM GUNU vs ISLEM GUNU
    Borsa hafta sonu ve tatilde kapalidir; "7 satir geriye git" demek yanlis
    sonuc verir. Bu yuzden haftalik/yillik degisim TAKVIM tarihine gore, o
    tarihteki veya ONCESINDEKI en yakin islem gunu kapanisiyla hesaplanir.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from symbols import (
    TROY_ONS_GRAM,
    TURETME_ONS_USD_GRAM_TRY,
    USDTRY_TICKER,
    VarlikEslesme,
)

logger = logging.getLogger(__name__)

#: Yahoo'yu yormamak icin cagrilar arasi bekleme (saniye). yfinance resmi bir
#: API degildir; art arda hizli istek atmak gecici engellemeye yol acabilir.
CAGRI_ARASI_BEKLEME = 0.4

#: Oynaklik (volatilite) hesabinda kullanilan son islem gunu sayisi.
#: `assets.sim_volatility` simulatorde tek adimlik sigma olarak kullanildigi
#: icin GUNLUK getiri standart sapmasi hesaplanir.
VOLATILITE_PENCERE = 90


@dataclass
class PiyasaVerisi:
    """Tek bir varligin Yahoo'dan uretilmis tam kaydi."""

    db_symbol: str
    kategori: str
    kaynak_ticker: str
    current_price: float
    prev_close: float | None = None
    daily_change_pct: float | None = None
    weekly_change_pct: float | None = None
    yearly_change_pct: float | None = None
    volatilite: float | None = None
    turetilmis: bool = False
    #: `price_history` icin (UTC zaman damgasi, fiyat) ikilileri.
    gecmis: list[tuple[datetime, float]] = field(default_factory=list)


@dataclass
class ToplamaSonucu:
    """Bir toplama turunun ciktisi."""

    veriler: list[PiyasaVerisi] = field(default_factory=list)
    hatalar: list[tuple[str, str]] = field(default_factory=list)
    cagri_sayisi: int = 0


class YahooHatasi(RuntimeError):
    """Yahoo'dan kullanilabilir veri alinamadi."""


# ---------------------------------------------------------------------------
# Seri getirme
# ---------------------------------------------------------------------------


def _utc_indeksle(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame indeksini UTC'ye normalize eder.

    yfinance ticker'a gore bazen zaman dilimi bilgili (BIST icin
    Europe/Istanbul), bazen bilgisiz indeks doner. Farkli varliklari
    hizalayabilmek icin hepsi UTC'ye cevrilir.
    """
    indeks = pd.DatetimeIndex(df.index)
    if indeks.tz is None:
        indeks = indeks.tz_localize("UTC")
    else:
        indeks = indeks.tz_convert("UTC")
    df = df.copy()
    df.index = indeks
    return df.sort_index()


def kapanis_serisi(ticker: str, period: str = "1y") -> pd.Series:
    """Bir ticker icin gunluk kapanis serisi ceker.

    Raises:
        YahooHatasi: Yahoo bos sonuc dondururse (gecersiz sembol, ag hatasi
            veya gecici engelleme).
    """
    ham = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)

    if ham is None or ham.empty or "Close" not in ham:
        raise YahooHatasi(f"'{ticker}' icin Yahoo bos veri dondurdu.")

    seri = _utc_indeksle(ham)["Close"].dropna()
    seri = seri[seri > 0]

    if seri.empty:
        raise YahooHatasi(f"'{ticker}' icin gecerli kapanis fiyati yok.")

    return seri


# ---------------------------------------------------------------------------
# Metrik hesaplama
# ---------------------------------------------------------------------------


def _gecmis_deger(seri: pd.Series, gun_once: int) -> float | None:
    """`gun_once` takvim gunu onceki (veya ondan ONCEKI en yakin) kapanis.

    Seri o tarihe kadar geriye gitmiyorsa `None` doner - uydurma yapilmaz.
    """
    hedef = seri.index[-1] - timedelta(days=gun_once)
    oncekiler = seri[seri.index <= hedef]
    if oncekiler.empty:
        return None
    return float(oncekiler.iloc[-1])


def _degisim_yuzdesi(guncel: float, referans: float | None) -> float | None:
    """Yuzde degisim; referans yoksa veya sifirsa `None`."""
    if referans is None or referans <= 0:
        return None
    return round((guncel / referans - 1) * 100, 2)


def _volatilite(seri: pd.Series) -> float | None:
    """Gunluk getirilerin standart sapmasi (`sim_volatility` karsiligi)."""
    getiriler = seri.tail(VOLATILITE_PENCERE).pct_change().dropna()
    if len(getiriler) < 5:
        return None
    return round(float(getiriler.std()), 6)


def metrikleri_hesapla(
    eslesme: VarlikEslesme, seri: pd.Series, turetilmis: bool = False
) -> PiyasaVerisi:
    """Kapanis serisinden semanin bekledigi tum alanlari uretir."""
    guncel = float(seri.iloc[-1])
    onceki = float(seri.iloc[-2]) if len(seri) >= 2 else None

    return PiyasaVerisi(
        db_symbol=eslesme.db_symbol,
        kategori=eslesme.kategori,
        kaynak_ticker=eslesme.yahoo_ticker,
        current_price=round(guncel, 4),
        prev_close=round(onceki, 4) if onceki else None,
        daily_change_pct=_degisim_yuzdesi(guncel, onceki),
        weekly_change_pct=_degisim_yuzdesi(guncel, _gecmis_deger(seri, 7)),
        yearly_change_pct=_degisim_yuzdesi(guncel, _gecmis_deger(seri, 365)),
        volatilite=_volatilite(seri),
        turetilmis=turetilmis,
        gecmis=[(ts.to_pydatetime(), round(float(fiyat), 4)) for ts, fiyat in seri.items()],
    )


# ---------------------------------------------------------------------------
# Turetme: ons/USD -> gram/TRY
# ---------------------------------------------------------------------------


def gram_try_serisi(ons_usd: pd.Series, usdtry: pd.Series) -> pd.Series:
    """Ons/USD serisini gram/TRY serisine cevirir.

    Iki seri farkli gunlerde islem gorebilir (vadeli piyasa Pazar aksami
    acilir, doviz neredeyse kesintisizdir). Bu yuzden kur serisi altin
    tarihlerine hizalanir ve bosluklar bir onceki gecerli kurla doldurulur
    (`ffill`) - kur uydurulmaz, en son bilinen deger kullanilir.
    """
    altin = ons_usd.copy()
    kur = usdtry.copy()
    altin.index = pd.DatetimeIndex(altin.index).normalize()
    kur.index = pd.DatetimeIndex(kur.index).normalize()

    altin = altin[~altin.index.duplicated(keep="last")].sort_index()
    kur = kur[~kur.index.duplicated(keep="last")].sort_index()

    hizali_kur = kur.reindex(altin.index, method="ffill")
    gram = (altin / TROY_ONS_GRAM) * hizali_kur
    return gram.dropna()


# ---------------------------------------------------------------------------
# Toplama
# ---------------------------------------------------------------------------


def varliklari_topla(
    eslesmeler: list[VarlikEslesme], period: str = "1y", bekleme: float = CAGRI_ARASI_BEKLEME
) -> ToplamaSonucu:
    """Verilen eslesmeler icin Yahoo'dan veri ceker.

    Bir varlik cekilemezse akis DURMAZ: hata listeye yazilir ve digerlerine
    devam edilir (kismi basari). Boylece tek bir sembolun bozulmasi tum
    toplamayi dusurmez.
    """
    sonuc = ToplamaSonucu()
    usdtry_seri: pd.Series | None = None

    # Turetilmis varlik varsa kur serisi BIR KEZ cekilir ve yeniden kullanilir.
    turetme_var = any(e.turetilmis for e in eslesmeler)
    if turetme_var:
        try:
            usdtry_seri = kapanis_serisi(USDTRY_TICKER, period)
            sonuc.cagri_sayisi += 1
            logger.info("USD/TRY kur serisi alindi (turetme icin)")
        except YahooHatasi as exc:
            sonuc.hatalar.append((USDTRY_TICKER, f"Turetme kuru alinamadi: {exc}"))

    for eslesme in eslesmeler:
        try:
            seri = kapanis_serisi(eslesme.yahoo_ticker, period)
            sonuc.cagri_sayisi += 1

            if eslesme.turetme == TURETME_ONS_USD_GRAM_TRY:
                if usdtry_seri is None:
                    raise YahooHatasi("USD/TRY kuru olmadan gram fiyati hesaplanamaz.")
                seri = gram_try_serisi(seri, usdtry_seri)
                if seri.empty:
                    raise YahooHatasi("Turetme sonrasi ortak tarih kalmadi.")

            sonuc.veriler.append(metrikleri_hesapla(eslesme, seri, turetilmis=eslesme.turetilmis))
            logger.info(
                "veri alindi",
                extra={"sembol": eslesme.db_symbol, "ticker": eslesme.yahoo_ticker},
            )

        except Exception as exc:  # noqa: BLE001 - tek varlik toplamayi dusurmemeli
            sonuc.hatalar.append((eslesme.db_symbol, str(exc)))
            logger.warning(
                "veri alinamadi",
                extra={"sembol": eslesme.db_symbol, "hata": str(exc)},
            )

        if bekleme:
            time.sleep(bekleme)

    return sonuc
