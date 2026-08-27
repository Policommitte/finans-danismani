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
import time
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
#: beklememelidir; saglayici bu surenin sonunda son dogrulanmis fiyati korur.
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


def _son_kotasyonlar(df: Any, tickerlar: list[str]) -> dict[str, dict[str, float | None]]:
    """Son fiyatla birlikte bir onceki piyasa gununun kapanisini cozer.

    yfinance tek ticker'da duz, coklu ticker'da MultiIndex kolon dondurur;
    iki bicim de burada normalize edilir. ``previous_close`` uygulamanin
    onceki tick'i degil, Yahoo serisindeki onceki islem gununun son fiyatidir.
    """
    if df is None or len(df) == 0:
        return {}

    kapanis = df["Close"]
    # Tek ticker istendiginde `Close` bir Series'tir.
    if hasattr(kapanis, "to_frame") and getattr(kapanis, "ndim", 2) == 1:
        kapanis = kapanis.to_frame(name=tickerlar[0])

    sonuc: dict[str, dict[str, float | None]] = {}
    for ticker in kapanis.columns:
        seri = kapanis[ticker].dropna()
        if seri.empty or float(seri.iloc[-1]) <= 0:
            continue
        fiyat = float(seri.iloc[-1])
        son_gun = seri.index[-1].date()
        onceki_gun = seri[[ts.date() < son_gun for ts in seri.index]]
        onceki_gun = onceki_gun[onceki_gun > 0]
        onceki_kapanis = float(onceki_gun.iloc[-1]) if not onceki_gun.empty else None
        sonuc[str(ticker)] = {"price": fiyat, "previous_close": onceki_kapanis}

    return sonuc


def _son_fiyatlar(df: Any, tickerlar: list[str]) -> dict[str, float]:
    """Geriye uyumlu yalnizca-son-fiyat gorunumu."""
    return {
        ticker: float(quote["price"]) for ticker, quote in _son_kotasyonlar(df, tickerlar).items()
    }


def _indir(tickerlar: list[str]) -> dict[str, dict[str, float | None]]:
    """SENKRON indirme - `asyncio.to_thread` icinden cagrilir."""
    import yfinance as yf

    df = yf.download(
        " ".join(tickerlar),
        # Onceki kapanis icin hafta sonu ve tatilleri de kapsayan pencere.
        period="5d",
        interval="1m",
        progress=False,
        auto_adjust=False,
        threads=True,
        timeout=YFINANCE_TIMEOUT_SANIYE,
    )
    return _son_kotasyonlar(df, tickerlar)


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


def kotasyonlari_turet(
    ham: dict[str, dict[str, float | None]], db_symbols: list[str]
) -> dict[str, dict[str, float | None]]:
    """Fiyat ve gercek onceki kapanisi DB sembollerine cevirir."""
    usdtry = ham.get(USDTRY_TICKER)
    sonuc: dict[str, dict[str, float | None]] = {}

    for sembol in db_symbols:
        if sembol in YAHOO_TICKERS:
            quote = ham.get(YAHOO_TICKERS[sembol])
            if quote and quote.get("price"):
                sonuc[sembol] = {
                    "price": round(float(quote["price"]), 4),
                    "previous_close": (
                        round(float(quote["previous_close"]), 4)
                        if quote.get("previous_close")
                        else None
                    ),
                }
            continue

        if sembol in TURETILMIS_GRAM_TRY:
            metal = ham.get(TURETILMIS_GRAM_TRY[sembol])
            if not metal or not metal.get("price") or not usdtry or not usdtry.get("price"):
                continue

            current = float(metal["price"]) / TROY_ONS_GRAM * float(usdtry["price"])
            previous = None
            if metal.get("previous_close") and usdtry.get("previous_close"):
                previous = (
                    float(metal["previous_close"]) / TROY_ONS_GRAM * float(usdtry["previous_close"])
                )
            sonuc[sembol] = {
                "price": round(current, 4),
                "previous_close": round(previous, 4) if previous else None,
            }

    return sonuc


async def canli_kotasyonlar(
    db_symbols: list[str],
) -> dict[str, dict[str, float | None]]:
    """Guncel fiyatlari gercek onceki piyasa kapanislariyla doner."""
    tickerlar = gerekli_tickerlar(db_symbols)
    if not tickerlar:
        return {}

    ham = await asyncio.wait_for(asyncio.to_thread(_indir, tickerlar), timeout=ISTEK_TIMEOUT_SANIYE)
    kotasyonlar = kotasyonlari_turet(ham, db_symbols)
    logger.info(
        "yahoo canli kotasyon alindi",
        extra={"istenen": len(db_symbols), "alinan": len(kotasyonlar), "cagri": len(tickerlar)},
    )
    return kotasyonlar


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

    kotasyonlar = await canli_kotasyonlar(db_symbols)
    fiyatlar = {sembol: float(quote["price"]) for sembol, quote in kotasyonlar.items()}
    return fiyatlar


# --- OHLC (mum grafik) -------------------------------------------------------
#
# `canli_fiyatlar`'in aksine burada GECMIS mumlar cekilir (Open/High/Low/
# Close). Yahoo'nun `yf.download`/`Ticker.history` cagrisi bu kolonlari zaten
# dondurur - sadece `_son_kotasyonlar` bugune kadar yalnizca `Close`'u
# kullaniyordu.
#
# GRANULERLIK: sabit "1d" yerine araliga gore secilir - Yahoo'nun gun-ici
# mumlari kisa donemlerde COK daha akici bir grafik verir:
#   <= 7 gun   -> 15 dakikalik mumlar (Yahoo'nun <=60 gunluk 15m siniri icinde)
#   <= 60 gun  -> saatlik mumlar      (Yahoo'nun <=730 gunluk 1h siniri icinde)
#   diger      -> gunluk mumlar       (uzun araliklarda binlerce gun-ici mum
#                                       hem gereksiz hem grafigi yavaslatirdi)
#
# TURETILMIS semboller (GRAM_ALTIN, GUMUS) DESTEKLENMEZ: bunlarin OHLC'si iki
# ayri seriden (metal + USDTRY) turetilmesi gerekir ve bir mumun ic-mum en
# yuksek/en dusuk noktalarinin ayni anda mi olustugu bilinmez - bu, gercek
# olmayan bir "gorunum" uretir. Bu yuzden bu semboller icin `None` donulur;
# frontend cizgi grafige duser.
#
# ONBELLEK: her (sembol, gun) kombinasyonu 5 dakika onbelleklenir - paylasilan
# gunluk API kotasini (MARKET_API_DAILY_QUOTA) modal her acildiginda/mum moduna
# gecildiginde tuketmemek icin. Sadece bu surec icindir, DB'ye yazilmaz.
_OHLC_ONBELLEK_SANIYE = 300
_ohlc_onbellek: dict[tuple[str, int], tuple[float, list[dict[str, float | str]]]] = {}


def _mum_araligi(gun: int) -> str:
    """Istenen gun sayisina gore Yahoo `interval` degeri secer."""
    if gun <= 7:
        return "15m"
    if gun <= 60:
        return "1h"
    return "1d"


def _indir_mumlar(ticker: str, gun: int) -> Any:
    """SENKRON OHLC indirme - `asyncio.to_thread` icinden cagrilir."""
    import yfinance as yf

    # En az birkac mum donsun diye alt sinir; ust sinirda Yahoo kendisi
    # mevcut en eski veriyle keser (hata vermez, kismi sonuc doner).
    period_gun = max(gun, 5)
    return yf.Ticker(ticker).history(
        period=f"{period_gun}d", interval=_mum_araligi(gun), timeout=YFINANCE_TIMEOUT_SANIYE
    )


async def gunluk_ohlc(sembol: str, gun: int) -> list[dict[str, float | str]] | None:
    """Verilen `assets.symbol` icin GERCEK OHLC mumlarini doner.

    Granulerlik `_mum_araligi()` ile araliga gore secilir (kisa araliklarda
    gun-ici mumlar). Sadece dogrudan bir Yahoo ticker'i olan semboller (bkz.
    `YAHOO_TICKERS`) desteklenir. Veri alinamazsa (ag hatasi, bilinmeyen
    sembol, bos seri) `None` doner - frontend bu durumda cizgi grafige duser,
    UYDURMA veri ASLA uretilmez.
    """
    ticker = YAHOO_TICKERS.get(sembol)
    if not ticker:
        return None

    onbellek_anahtari = (sembol, gun)
    simdi = time.monotonic()
    onbellenmis = _ohlc_onbellek.get(onbellek_anahtari)
    if onbellenmis and simdi - onbellenmis[0] < _OHLC_ONBELLEK_SANIYE:
        return onbellenmis[1]

    try:
        df = await asyncio.wait_for(
            asyncio.to_thread(_indir_mumlar, ticker, gun),
            timeout=ISTEK_TIMEOUT_SANIYE,
        )
    except Exception:  # noqa: BLE001 - ag/format hatasi grafik yerine bos donmeli
        logger.warning("OHLC alinamadi", extra={"sembol": sembol, "ticker": ticker})
        return None

    if df is None or df.empty:
        return None

    mumlar: list[dict[str, float | str]] = []
    for zaman_damgasi, satir in df.iterrows():
        kapanis = float(satir["Close"])
        if kapanis <= 0:
            continue
        mumlar.append(
            {
                "ts": zaman_damgasi.isoformat(),
                "open": round(float(satir["Open"]), 4),
                "high": round(float(satir["High"]), 4),
                "low": round(float(satir["Low"]), 4),
                "close": round(kapanis, 4),
            }
        )

    if not mumlar:
        return None

    _ohlc_onbellek[onbellek_anahtari] = (simdi, mumlar)
    return mumlar
