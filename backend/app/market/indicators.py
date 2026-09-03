"""Teknik gosterge hesabi - `pandas-ta-classic` sarmalayicisi.

Tek isi konvansiyonlari SABITLEMEK: hangi periyot, hangi yumusatma, hangi
kolon. Kutuphane RSI/ADX icin Wilder yumusatmasi, stokastik icin varsayilan
`smooth_k=3` kullanir; ekranda gosterilen deger budur.

Yetersiz veride kutuphane `None` ya da NaN dondurur; her iki durum da burada
`None`'a normalize edilir - cagiran taraf "veri yok" olarak isaretler.
"""

from __future__ import annotations

import pandas as pd
import pandas_ta_classic as ta

#: Panelde gosterilen hareketli ortalama periyotlari (SMA ve EMA icin ayni).
MA_PERIODS: tuple[int, ...] = (5, 10, 20, 50, 100, 200)

#: Gosterge anahtari -> arayuzde gosterilecek ad.
INDICATOR_LABELS: dict[str, str] = {
    "rsi_14": "RSI(14)",
    "stoch_k_9_6": "STOCH(9,6)",
    "macd_12_26_9": "MACD(12,26,9)",
    "adx_14": "ADX(14)",
    "cci_20": "CCI(20)",
    "willr_14": "Williams %R(14)",
    "roc_10": "ROC(10)",
}

#: High/low gerektiren gostergeler. Yalnizca kapanis serisi olan kaynakta
#: (price_history) hesaplanmaz - kapanisi high/low yerine koymak uydurma olur.
RANGE_DEPENDENT: frozenset[str] = frozenset({"stoch_k_9_6", "adx_14", "cci_20", "willr_14"})


def _last(series) -> float | None:
    """Serinin son gecerli degeri; seri yoksa ya da NaN ise `None`."""
    if series is None or len(series) == 0:
        return None
    value = series.iloc[-1]
    return None if pd.isna(value) else float(value)


def indicator_values(frame: pd.DataFrame, *, has_range: bool) -> dict[str, float | None]:
    """Gosterge anahtari -> son deger.

    `has_range` False ise high/low gerektiren gostergeler hesaplanmaz.
    MACD icin dondurulen deger HISTOGRAM'dir (MACD - sinyal cizgisi); sinyal
    yonu bu farkin isaretinden okunur.
    """
    close = frame["close"]
    values: dict[str, float | None] = {key: None for key in INDICATOR_LABELS}

    values["rsi_14"] = _last(ta.rsi(close, length=14))
    values["roc_10"] = _last(ta.roc(close, length=10))

    macd = ta.macd(close, fast=12, slow=26, signal=9)
    if macd is not None:
        values["macd_12_26_9"] = _last(macd["MACDh_12_26_9"])

    if not has_range:
        return values

    high, low = frame["high"], frame["low"]

    stoch = ta.stoch(high, low, close, k=9, d=6)
    if stoch is not None:
        values["stoch_k_9_6"] = _last(stoch["STOCHk_9_6_3"])

    values["cci_20"] = _last(ta.cci(high, low, close, length=20))
    values["willr_14"] = _last(ta.willr(high, low, close, length=14))

    adx = ta.adx(high, low, close, length=14)
    if adx is not None:
        values["adx_14"] = _last(adx["ADX_14"])
        # Yon bilgisi ADX'te yok; DI+ / DI- farkindan gelir.
        values["_dmp_14"] = _last(adx["DMP_14"])
        values["_dmn_14"] = _last(adx["DMN_14"])

    return values


def moving_average_values(close: pd.Series) -> dict[int, dict[str, float | None]]:
    """Periyot -> {"sma": deger, "ema": deger}; mum sayisi yetmezse `None`."""
    return {
        period: {
            "sma": _last(ta.sma(close, length=period)),
            "ema": _last(ta.ema(close, length=period)),
        }
        for period in MA_PERIODS
    }
