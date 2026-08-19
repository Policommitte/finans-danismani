"""Yahoo Finance canli fiyat istemcisi (mimari v4 bolum 8).

Bu modul YALNIZCA fiyat ceker; veritabanini, zamanlayiciyi ve `assets`
tablosunu BILMEZ. Yazma isi `ApiMarketProvider` -> `MarketRepository`
zincirindedir.

CAGRI SAYISI: SEMBOL BASINA BIR ISTEK
    `yf.download` disaridan TEK bir cagri gibi gorunur ama iceride ticker
    listesi uzerinde DONER ve her ticker icin ayri bir HTTP istegi atar
    (yfinance/multi.py: `_download_one` -> `Ticker.history`). `threads=True`
    bu istekleri yalnizca PARALELLESTIRIR, tek istege indirmez.

    Yani N sembol = N istek. Bu modulun sembol listesi 16 ticker uretir;
    15 dakikalik tick ile gunde ~1.536 istek eder. Kota sayaci bu yuzden
    tick basina 1 degil GERCEK ticker sayisi kadar islenmelidir - bkz.
    `ApiMarketProvider.next_prices`.

    Hacmi dusurmenin yolu tick araligini buyutmek veya sembol listesini
    kisaltmaktir; tek istege indirmek yfinance ile MUMKUN DEGILDIR.

BLOKLAMA
    yfinance SENKRON bir kutuphanedir. Dogrudan cagrilirsa `asyncio` olay
    dongusunu (event loop) bloklar ve tum API istekleri fiyat cekilirken
    donar. Bu yuzden cagri `asyncio.to_thread` ile ayri bir is parcacigina
    tasinir.

TURETILMIS FIYATLAR
    Yahoo'da "TRY cinsinden gram altin" diye bir sembol YOKTUR:

        gram_TRY = (ons_USD / 31.1034768) * USDTRY

    Bu saf maden degeridir; kuyumcu isciligi ve makasi ICERMEZ.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

#: 1 troy ons = 31.1034768 gram (kiymetli maden standardi).
TROY_ONS_GRAM = 31.1034768

#: Altin/gumus turetmesi icin gereken kur sembolu.
USDTRY_TICKER = "USDTRY=X"

#: `assets.symbol` -> Yahoo ticker.
#:
#: AYNI ESLEME IKI YERDE DURUR: `borsa-verisi/symbols.py` bagimsiz bir
#: betiktir, backend'i import ETMEZ ve tabloyu kendi bicimiyle tutar. Elle
#: senkron tutulurlar; ayrisirlarsa `tests/test_yahoo_client.py` icindeki
#: senkron testi CI'da hata verir - yani sessizce bozulamazlar.
YAHOO_TICKERS: dict[str, str] = {
    # BIST hisseleri - Yahoo'da ".IS" eki ile
    "THYAO": "THYAO.IS",
    "GARAN": "GARAN.IS",
    "TCELL": "TCELL.IS",
    "SASA": "SASA.IS",
    "ASELS": "ASELS.IS",
    "EREGL": "EREGL.IS",
    # Doviz - "=X" eki ile
    "USD/TRY": USDTRY_TICKER,
    "EUR/TRY": "EURTRY=X",
    # ABD hisseleri - dogrudan
    "AAPL": "AAPL",
    "TSLA": "TSLA",
    "NVDA": "NVDA",
    # Kripto - USD cinsinden
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
}

#: Dogrudan cekilemeyen, ons/USD fiyatindan gram/TRY'ye cevrilen varliklar.
#: `assets.symbol` -> kaynak Yahoo ticker (vadeli sozlesme).
TURETILMIS_GRAM_TRY: dict[str, str] = {
    "GRAM_ALTIN": "GC=F",  # COMEX altin vadeli
    "GUMUS": "SI=F",  # COMEX gumus vadeli
}

#: Yahoo cagrisi icin DIS ust sinir. Ag takilirsa fiyat gorevi sonsuza kadar
#: beklememelidir; saglayici bu surenin sonunda yedege duser.
ISTEK_TIMEOUT_SANIYE = 30

#: yfinance'e GECIRILEN istek basina timeout.
#:
#: NEDEN AYRICA GEREKLI: `asyncio.wait_for` bir is parcacigini IPTAL EDEMEZ.
#: Dis sure dolunca `to_thread` icindeki indirme calismaya DEVAM eder ve
#: yfinance kendi ic is parcaciklarini da actigi icin takilan cagrilar tick
#: tick birikir. Asil sinir bu yuzden ICERIDE olmali; dis sinir son caredir.
#: yfinance'in varsayilani 10 sn'dir, burada acikca verilir.
YFINANCE_TIMEOUT_SANIYE = 12


def desteklenen_semboller() -> set[str]:
    """Yahoo'dan fiyati alinabilen tum `assets.symbol` degerleri."""
    return set(YAHOO_TICKERS) | set(TURETILMIS_GRAM_TRY)


def gerekli_tickerlar(db_symbols: list[str]) -> list[str]:
    """Istenen semboller icin cekilmesi gereken Yahoo ticker listesi.

    Turetilmis bir varlik istendiginde kaynak sozlesmenin YANI SIRA USD/TRY
    kuru da gerekir; liste bunu otomatik ekler.
    """
    tickerlar: set[str] = set()
    turetme_var = False

    for sembol in db_symbols:
        if sembol in YAHOO_TICKERS:
            tickerlar.add(YAHOO_TICKERS[sembol])
        elif sembol in TURETILMIS_GRAM_TRY:
            tickerlar.add(TURETILMIS_GRAM_TRY[sembol])
            turetme_var = True

    if turetme_var:
        tickerlar.add(USDTRY_TICKER)

    return sorted(tickerlar)


def _son_fiyatlar(df: Any, tickerlar: list[str]) -> dict[str, float]:
    """`yf.download` ciktisindan ticker -> son gecerli kapanis sozlugu uretir.

    yfinance tek ticker'da duz, coklu ticker'da MultiIndex kolon dondurur;
    iki bicim de burada normalize edilir.
    """
    if df is None or len(df) == 0:
        return {}

    kapanis = df["Close"]
    # Tek ticker istendiginde `Close` bir Series'tir.
    if hasattr(kapanis, "to_frame") and getattr(kapanis, "ndim", 2) == 1:
        kapanis = kapanis.to_frame(name=tickerlar[0])

    sonuc: dict[str, float] = {}
    for ticker in kapanis.columns:
        seri = kapanis[ticker].dropna()
        if seri.empty:
            continue
        fiyat = float(seri.iloc[-1])
        if fiyat > 0:
            sonuc[str(ticker)] = fiyat

    return sonuc


def _indir(tickerlar: list[str]) -> dict[str, float]:
    """SENKRON indirme - `asyncio.to_thread` icinden cagrilir."""
    import yfinance as yf

    df = yf.download(
        " ".join(tickerlar),
        period="1d",
        interval="1m",
        progress=False,
        auto_adjust=False,
        threads=True,
        timeout=YFINANCE_TIMEOUT_SANIYE,
    )
    return _son_fiyatlar(df, tickerlar)


def fiyatlari_turet(ham: dict[str, float], db_symbols: list[str]) -> dict[str, float]:
    """Yahoo ticker fiyatlarini `assets.symbol` fiyatlarina cevirir.

    Turetilmis varliklar (gram altin/gumus) burada hesaplanir. Kur yoksa o
    varlik sonuca EKLENMEZ - yanlis fiyat yazmaktansa eski fiyat korunur.
    """
    usdtry = ham.get(USDTRY_TICKER)
    sonuc: dict[str, float] = {}

    for sembol in db_symbols:
        if sembol in YAHOO_TICKERS:
            fiyat = ham.get(YAHOO_TICKERS[sembol])
            if fiyat:
                sonuc[sembol] = round(fiyat, 4)
            continue

        if sembol in TURETILMIS_GRAM_TRY:
            ons_usd = ham.get(TURETILMIS_GRAM_TRY[sembol])
            if not ons_usd or not usdtry:
                logger.warning(
                    "turetilmis fiyat hesaplanamadi (kur veya ons fiyati yok)",
                    extra={"sembol": sembol},
                )
                continue
            sonuc[sembol] = round((ons_usd / TROY_ONS_GRAM) * usdtry, 4)

    return sonuc


async def canli_fiyatlar(db_symbols: list[str]) -> dict[str, float]:
    """Verilen `assets.symbol` listesi icin guncel fiyatlari doner.

    Bir cagrida kac HTTP istegi atildigini cagiran taraf `gerekli_tickerlar()`
    ile ogrenir (her ticker = bir istek; bkz. modul docstring'i).

    Returns:
        `{sembol: fiyat}`. Fiyati alinamayan sembol sozlukte YER ALMAZ;
        cagiran taraf eski fiyati korur.

    Raises:
        TimeoutError: Yahoo `ISTEK_TIMEOUT_SANIYE` icinde yanit vermezse.
    """
    tickerlar = gerekli_tickerlar(db_symbols)
    if not tickerlar:
        return {}

    ham = await asyncio.wait_for(asyncio.to_thread(_indir, tickerlar), timeout=ISTEK_TIMEOUT_SANIYE)

    fiyatlar = fiyatlari_turet(ham, db_symbols)
    logger.info(
        "yahoo canli fiyat alindi",
        extra={
            "istenen": len(db_symbols),
            "alinan": len(fiyatlar),
            # Her ticker ayri bir HTTP istegidir - "1" DEGIL.
            "cagri": len(tickerlar),
        },
    )
    return fiyatlar
