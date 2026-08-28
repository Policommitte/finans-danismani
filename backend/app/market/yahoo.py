"""Yahoo Finance canli fiyat istemcisi (mimari v4 bolum 8).

Bu modul YALNIZCA fiyat ceker; veritabanini, zamanlayiciyi ve `assets`
tablosunu BILMEZ. Yazma isi `ApiMarketProvider` -> `MarketRepository`
zincirindedir.

CAGRI SAYISI: SEMBOL BASINA BIR ISTEK
    `yf.download` disaridan TEK bir cagri gibi gorunur ama iceride ticker
    listesi uzerinde DONER ve her ticker icin ayri bir HTTP istegi atar
    (yfinance/multi.py: `_download_one` -> `Ticker.history`). `threads=True`
    bu istekleri yalnizca PARALELLESTIRIR, tek istege indirmez.

    Yani N ticker = N istek. Kota sayaci bu yuzden tick basina 1 degil
    GERCEK ticker sayisi kadar islenmelidir - bkz. `ApiMarketProvider.next_prices`.

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
from datetime import datetime, timedelta, timezone
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
    # Endeksler
    "BIST100": "^XU100",
    # BIST hisseleri - Yahoo'da ".IS" eki ile
    "AKCNS": "AKCNS.IS",
    "BIMAS": "BIMAS.IS",
    "KCHOL": "KCHOL.IS",
    "KONTR": "KONTR.IS",
    "SISE": "SISE.IS",
    "THYAO": "THYAO.IS",
    "GARAN": "GARAN.IS",
    "TCELL": "TCELL.IS",
    "SASA": "SASA.IS",
    "ASELS": "ASELS.IS",
    "EREGL": "EREGL.IS",
    "TOASO": "TOASO.IS",
    "TUPRS": "TUPRS.IS",
    # Doviz - "=X" eki ile
    "USD/TRY": USDTRY_TICKER,
    "EUR/TRY": "EURTRY=X",
    # ABD hisseleri - dogrudan
    "AAPL": "AAPL",
    "AMZN": "AMZN",
    "BRK-B": "BRK-B",
    "GOOG": "GOOG",
    "INTC": "INTC",
    "JPM": "JPM",
    "KO": "KO",
    "LLY": "LLY",
    "META": "META",
    "MSFT": "MSFT",
    "TSLA": "TSLA",
    "NVDA": "NVDA",
    "T": "T",
    "WMT": "WMT",
    # ETF'ler
    "QQQ": "QQQ",
    "SPY": "SPY",
    "VTI": "VTI",
    # Emtia vadeli kontratlari
    "BAKIR": "HG=F",
    "BRENT": "BZ=F",
    "MISIR": "ZC=F",
    # ABD 10 yillik tahvil getirisi (yuzde puan)
    "US10Y": "^TNX",
    # Kripto - USD cinsinden
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "USDT": "USDT-USD",
}

# Canli 1dk paketinden uretilen saatlik mumlar, Yahoo'nun dogrudan 1h
# arsivindeki gercek seans baslangiciyla ayni kovaya yazilmalidir.
YARIM_SAAT_TICKERLARI = frozenset(
    ticker
    for symbol, ticker in YAHOO_TICKERS.items()
    if ticker.endswith(".IS")
    or symbol
    in {
        "BIST100", "US10Y", "AAPL", "AMZN", "BRK-B", "GOOG", "INTC",
        "JPM", "KO", "LLY", "META", "MSFT", "NVDA", "T", "TSLA", "WMT",
        "QQQ", "SPY", "VTI",
    }
)

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

# Son fiyat indirmesinin ayni cevabindan uretilen 5 dakikalik ve gunluk OHLCV mumlari.
# Scheduler, fiyatlar yazildiktan hemen sonra bu listeyi kalici depoya aktarir.
_SON_INDIRILEN_MUMLAR: list[dict] = []


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


def _ticker_ohlcv_frame(df: Any, ticker: str):
    """Tek ticker OHLCV kolonlarini Yahoo'nun duz/coklu biciminden ayirir."""
    import pandas as pd

    if isinstance(df.columns, pd.MultiIndex):
        return pd.DataFrame(
            {
                field: df[field][ticker]
                for field in ("Open", "High", "Low", "Close", "Volume")
            }
        )
    return df[["Open", "High", "Low", "Close", "Volume"]].copy()


def _ohlcv_mumlari(
    df: Any,
    ticker_to_symbol: dict[str, str],
    *,
    interval: str,
    resample_rule: str | None,
    saatlik_piyasa_ofseti: bool = False,
) -> list[dict]:
    """Yahoo OHLCV serisini istenen kalici mum araligina toplar."""
    import pandas as pd

    if df is None or len(df) == 0:
        return []

    sonuc: list[dict] = []
    for ticker, symbol in ticker_to_symbol.items():
        try:
            frame = _ticker_ohlcv_frame(df, ticker)
        except (KeyError, TypeError):
            continue

        frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
        frame = frame[
            (frame["Open"] > 0) & (frame["High"] > 0) & (frame["Low"] > 0) & (frame["Close"] > 0)
        ]
        if frame.empty:
            continue

        if resample_rule is None:
            # Yahoo'nun dogrudan 1h serisindeki zaman damgasi mumun gercek
            # baslangicidir (BIST/ABD hisselerinde xx:30 olabilir). Yeniden
            # resample etmek bu damgayi xx:00'a cekip grafigi 30 dk kaydirir.
            grouped = frame
        else:
            offset = (
                timedelta(minutes=30)
                if saatlik_piyasa_ofseti
                and ticker in YARIM_SAAT_TICKERLARI
                else None
            )
            grouped = frame.resample(resample_rule, offset=offset).agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            )
        grouped = grouped.dropna(subset=["Open", "High", "Low", "Close"])
        for timestamp, row in grouped.iterrows():
            ts = timestamp.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            volume = row.get("Volume")
            open_price = float(row["Open"])
            close_price = float(row["Close"])
            # Yahoo ozellikle FX serilerinde cok kucuk yuvarlama farklariyla
            # close < low veya close > high donebiliyor. OHLC geometrisini
            # korumak icin govde uclarini fitile dahil et.
            high_price = max(float(row["High"]), open_price, close_price)
            low_price = min(float(row["Low"]), open_price, close_price)
            sonuc.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "ts": ts.isoformat(),
                    "open": round(open_price, 6),
                    "high": round(high_price, 6),
                    "low": round(low_price, 6),
                    "close": round(close_price, 6),
                    "volume": None if pd.isna(volume) else round(float(volume), 6),
                }
            )
    return sonuc


def _turetilmis_gram_frame(df: Any, metal_ticker: str):
    """Ons/USD metal ve USD/TRY mumlarini gram/TRY OHLCV serisine cevirir."""
    import pandas as pd

    try:
        metal = _ticker_ohlcv_frame(df, metal_ticker).add_suffix("_metal")
        kur = _ticker_ohlcv_frame(df, USDTRY_TICKER).add_suffix("_fx")
    except (KeyError, TypeError):
        return pd.DataFrame()

    joined = metal.join(kur, how="inner").dropna(
        subset=[
            "Open_metal",
            "High_metal",
            "Low_metal",
            "Close_metal",
            "Open_fx",
            "High_fx",
            "Low_fx",
            "Close_fx",
        ]
    )
    if joined.empty:
        return pd.DataFrame()

    return pd.DataFrame(
        {
            "Open": joined["Open_metal"] * joined["Open_fx"] / TROY_ONS_GRAM,
            "High": joined["High_metal"] * joined["High_fx"] / TROY_ONS_GRAM,
            "Low": joined["Low_metal"] * joined["Low_fx"] / TROY_ONS_GRAM,
            "Close": joined["Close_metal"] * joined["Close_fx"] / TROY_ONS_GRAM,
            "Volume": joined["Volume_metal"],
        },
        index=joined.index,
    )


def _turetilmis_gram_mumlari(
    df: Any,
    derived_symbols: dict[str, str],
    *,
    interval: str,
    resample_rule: str | None,
) -> list[dict]:
    """Gram altin/gumus icin kaynak paketle ayni aralikta mum uretir."""
    result: list[dict] = []
    for symbol, metal_ticker in derived_symbols.items():
        frame = _turetilmis_gram_frame(df, metal_ticker)
        if frame.empty:
            continue
        result.extend(
            _ohlcv_mumlari(
                frame,
                {symbol: symbol},
                interval=interval,
                resample_rule=resample_rule,
            )
        )
    return result


def _bes_dakikalik_mumlar(df: Any, ticker_to_symbol: dict[str, str]) -> list[dict]:
    """Yahoo'nun 1 dakikalik OHLCV serisini gercek 5 dakikalik mumlara toplar."""
    return _ohlcv_mumlari(
        df,
        ticker_to_symbol,
        interval="5m",
        resample_rule="5min",
    )


def _bir_dakikalik_mumlar(df: Any, ticker_to_symbol: dict[str, str]) -> list[dict]:
    """Yahoo'nun ham 1 dakikalik OHLCV satirlarini normalize eder."""
    return _ohlcv_mumlari(
        df,
        ticker_to_symbol,
        interval="1m",
        resample_rule="1min",
    )


def _saatlik_mumlar(df: Any, ticker_to_symbol: dict[str, str]) -> list[dict]:
    """Canli 1dk serisini piyasanin gercek saat baslangicina toplar."""
    return _ohlcv_mumlari(
        df,
        ticker_to_symbol,
        interval="1h",
        resample_rule="1h",
        saatlik_piyasa_ofseti=True,
    )


def _gunluk_mumlar(df: Any, ticker_to_symbol: dict[str, str]) -> list[dict]:
    """Yahoo OHLCV serisini gunluk mumlara toplar."""
    return _ohlcv_mumlari(
        df,
        ticker_to_symbol,
        interval="1d",
        resample_rule="1D",
    )


def _indir_paket(
    tickerlar: list[str],
    ticker_to_symbol: dict[str, str],
    derived_symbols: dict[str, str] | None = None,
) -> tuple[dict[str, dict[str, float | None]], list[dict]]:
    """SENKRON fiyat + OHLCV indirme; tek Yahoo cevabini iki kez kullanir."""
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
    derived_symbols = derived_symbols or {}
    mumlar = _bir_dakikalik_mumlar(df, ticker_to_symbol)
    mumlar.extend(
        _turetilmis_gram_mumlari(
            df, derived_symbols, interval="1m", resample_rule="1min"
        )
    )
    mumlar.extend(_bes_dakikalik_mumlar(df, ticker_to_symbol))
    mumlar.extend(
        _turetilmis_gram_mumlari(
            df, derived_symbols, interval="5m", resample_rule="5min"
        )
    )
    mumlar.extend(_saatlik_mumlar(df, ticker_to_symbol))
    mumlar.extend(
        _turetilmis_gram_mumlari(
            df, derived_symbols, interval="1h", resample_rule="1h"
        )
    )
    mumlar.extend(_gunluk_mumlar(df, ticker_to_symbol))
    mumlar.extend(
        _turetilmis_gram_mumlari(
            df, derived_symbols, interval="1d", resample_rule="1D"
        )
    )
    return _son_kotasyonlar(df, tickerlar), mumlar


def _gecmis_mum_paketi(
    ticker_to_symbol: dict[str, str],
    period: str | None,
    interval: str,
    start: Any = None,
    end: Any = None,
    derived_symbols: dict[str, str] | None = None,
) -> list[dict]:
    """SENKRON tarihsel OHLCV indirme; yalnizca manuel backfill kullanir."""
    import yfinance as yf

    derived_symbols = derived_symbols or {}
    tickerlar = sorted(
        set(ticker_to_symbol)
        | set(derived_symbols.values())
        | ({USDTRY_TICKER} if derived_symbols else set())
    )
    if not tickerlar:
        return []
    options = {
        "interval": interval,
        "progress": False,
        "auto_adjust": False,
        "threads": True,
        "timeout": YFINANCE_TIMEOUT_SANIYE,
    }
    if start is not None and end is not None:
        options.update({"start": start, "end": end})
    else:
        options["period"] = period
    df = yf.download(" ".join(tickerlar), **options)
    if interval == "1m":
        result = _ohlcv_mumlari(
            df, ticker_to_symbol, interval="1m", resample_rule="1min"
        )
        result.extend(
            _turetilmis_gram_mumlari(
                df, derived_symbols, interval="1m", resample_rule="1min"
            )
        )
        return result
    if interval == "5m":
        result = _ohlcv_mumlari(
            df, ticker_to_symbol, interval="5m", resample_rule="5min"
        )
        result.extend(
            _turetilmis_gram_mumlari(
                df, derived_symbols, interval="5m", resample_rule="5min"
            )
        )
        return result
    if interval == "1h":
        result = _ohlcv_mumlari(
            df, ticker_to_symbol, interval="1h", resample_rule=None
        )
        result.extend(
            _turetilmis_gram_mumlari(
                df, derived_symbols, interval="1h", resample_rule=None
            )
        )
        return result
    if interval == "1d":
        result = _ohlcv_mumlari(
            df, ticker_to_symbol, interval="1d", resample_rule="1D"
        )
        result.extend(
            _turetilmis_gram_mumlari(
                df, derived_symbols, interval="1d", resample_rule="1D"
            )
        )
        return result
    raise ValueError(f"desteklenmeyen gecmis mum araligi: {interval}")


async def gecmis_mumlari_indir(
    db_symbols: list[str],
    *,
    period: str | None = None,
    interval: str,
    start: Any = None,
    end: Any = None,
) -> list[dict]:
    """Tarihsel mumlari indirir; sayfa istekleri bu fonksiyonu cagiramaz."""
    ticker_to_symbol = {
        ticker: symbol for symbol, ticker in YAHOO_TICKERS.items() if symbol in db_symbols
    }
    derived_symbols = {
        symbol: ticker
        for symbol, ticker in TURETILMIS_GRAM_TRY.items()
        if symbol in db_symbols
    }
    return await asyncio.wait_for(
        asyncio.to_thread(
            _gecmis_mum_paketi,
            ticker_to_symbol,
            period,
            interval,
            start,
            end,
            derived_symbols,
        ),
        timeout=ISTEK_TIMEOUT_SANIYE * 2,
    )


def tamamlanmis_saatlik_mumlar(
    candles: list[dict], *, now: datetime | None = None
) -> list[dict]:
    """Devam eden saati uzlastirma paketinden cikarir.

    Yahoo son 1h satirini piyasa acikken guncelleyebilir. Gunluk uzlastirma
    yalniz kapanmis saatleri yazarsa canli 1dk cevabindan uretilen mevcut mum
    bir sonraki uzlastirmaya kadar geriye dogru degismez.
    """
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    result: list[dict] = []
    for candle in candles:
        timestamp = datetime.fromisoformat(str(candle["ts"]).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if timestamp + timedelta(hours=1) <= reference:
            result.append(candle)
    return result


def son_mumlari_daralt(candles: list[dict]) -> list[dict]:
    """Normal tick'te yalniz degisebilecek son mumlari DB'ye yollar.

    Provider'in ilk cagrisi tam 5 gunu yazar ve uygulama kapaliyken olusan
    kisa bosluklari kapatir. Sonraki tick'lerde ayni on binlerce satiri tekrar
    upsert etmek yerine her sembol/aralik icin son birkac satir yeterlidir.
    """
    limits = {"1m": 10, "5m": 3, "1h": 2, "1d": 2}
    grouped: dict[tuple[str, str], list[dict]] = {}
    for candle in candles:
        key = (str(candle["symbol"]), str(candle["interval"]))
        grouped.setdefault(key, []).append(candle)

    result: list[dict] = []
    for (_, interval), rows in grouped.items():
        rows.sort(key=lambda row: str(row["ts"]))
        result.extend(rows[-limits.get(interval, 1) :])
    return result


def ilk_mum_paketini_daralt(candles: list[dict]) -> list[dict]:
    """Ilk canli pakette arsivlik serileri korur, 1h gecmisini daraltir."""
    hourly = [row for row in candles if row.get("interval") == "1h"]
    others = [row for row in candles if row.get("interval") != "1h"]
    return others + son_mumlari_daralt(hourly)


def _indir(tickerlar: list[str]) -> dict[str, dict[str, float | None]]:
    """Geriye uyumlu yalnizca kotasyon indirme yardimcisi."""
    return _indir_paket(tickerlar, {})[0]


def son_indirilen_mumlar() -> list[dict]:
    """Son basarili fiyat isteginden cikan OHLCV mumlarinin kopyasi."""
    return [dict(row) for row in _SON_INDIRILEN_MUMLAR]


def mum_onbellegini_temizle() -> None:
    global _SON_INDIRILEN_MUMLAR
    _SON_INDIRILEN_MUMLAR = []


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

    global _SON_INDIRILEN_MUMLAR
    _SON_INDIRILEN_MUMLAR = []
    ters_esleme = {
        ticker: symbol for symbol, ticker in YAHOO_TICKERS.items() if symbol in db_symbols
    }
    turetilmis_esleme = {
        symbol: ticker
        for symbol, ticker in TURETILMIS_GRAM_TRY.items()
        if symbol in db_symbols
    }
    ham, mumlar = await asyncio.wait_for(
        asyncio.to_thread(_indir_paket, tickerlar, ters_esleme, turetilmis_esleme),
        timeout=ISTEK_TIMEOUT_SANIYE,
    )
    _SON_INDIRILEN_MUMLAR = mumlar
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
