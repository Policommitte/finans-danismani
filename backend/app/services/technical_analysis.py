"""Gunluk mumlardan deterministik teknik gorunum.

LLM KULLANILMAZ: ayni mum serisi her zaman ayni sinifi uretir. Boylece
"neden Sat cikti?" sorusunun cevabi gosterge tablosunda tek tek durur
(bkz. app/signals/engine.py, ayni ilke).

Zaman araligi SABIT GUNLUKTUR; grafikteki aralik sekmesinden bagimsizdir.
Sebep: RSI(14), MACD(12,26,9) ve SMA200 gibi gostergelerin yerlesik
yorumu gunluk mum uzerinedir.
"""

from __future__ import annotations

import logging

import pandas as pd

from app.market.indicators import (
    INDICATOR_LABELS,
    MA_PERIODS,
    RANGE_DEPENDENT,
    indicator_values,
    moving_average_values,
)
from app.market.yahoo import gunluk_ohlc
from app.repositories.deps import get_market_repository
from app.schemas.market import (
    TechnicalIndicator,
    TechnicalMovingAverage,
    TechnicalResponse,
    TechnicalSummary,
)

logger = logging.getLogger(__name__)

#: Varsayilan takvim penceresi. SMA200'un dolmasi 200 ISLEM gunu ister;
#: hafta sonu/tatil payiyla ~300 takvim gunu gerekir.
DEFAULT_DAYS = 300

#: Altinda hicbir sinif uretilmeyen mum sayisi. MACD(12,26,9) icin gereken
#: en kucuk seri budur; daha azinda gosterge tablosu bosa cikar.
MIN_CANDLES = 35

BUY, SELL, NEUTRAL, NO_DATA = "AL", "SAT", "NOTR", "VERI_YOK"

#: Ozet skorundan sinif esikleri (buyukten kucuge taranir).
SUMMARY_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.5, "GUCLU_AL"),
    (0.15, "AL"),
    (-0.15, "NOTR"),
    (-0.5, "SAT"),
)
STRONG_SELL = "GUCLU_SAT"

_SIGNAL_SCORES = {BUY: 1, SELL: -1, NEUTRAL: 0}


async def technical_analysis(symbol: str, days: int = DEFAULT_DAYS) -> TechnicalResponse:
    """Bir varligin teknik gorunumu; veri yetersizse `sufficient=False`."""
    symbol = symbol.upper()
    candles, source = await _load_candles(symbol, days)

    if len(candles) < MIN_CANDLES:
        return TechnicalResponse(
            symbol=symbol,
            days=days,
            candle_count=len(candles),
            last_candle_ts=candles[-1]["ts"] if candles else None,
            source=source,
            sufficient=False,
            reason=(
                f"Teknik analiz icin en az {MIN_CANDLES} gunluk mum gerekiyor; "
                f"bu varlik icin {len(candles)} mum var."
            ),
        )

    frame = pd.DataFrame(candles)
    has_range = source != "price_history"

    values = indicator_values(frame, has_range=has_range)
    indicators = _build_indicators(values, has_range=has_range)

    price = float(frame["close"].iloc[-1])
    averages = _build_moving_averages(moving_average_values(frame["close"]), price)

    indicator_summary = _summarize(indicator.signal for indicator in indicators)
    ma_signals = [signal for ma in averages for signal in (ma.sma_signal, ma.ema_signal)]
    moving_average_summary = _summarize(ma_signals)

    return TechnicalResponse(
        symbol=symbol,
        days=days,
        candle_count=len(candles),
        last_candle_ts=candles[-1]["ts"],
        source=source,
        sufficient=True,
        price=round(price, 4),
        summary=_overall_summary(indicator_summary, moving_average_summary),
        indicator_summary=indicator_summary,
        moving_average_summary=moving_average_summary,
        indicators=indicators,
        moving_averages=averages,
    )


async def _load_candles(symbol: str, days: int) -> tuple[list[dict], str]:
    """Gunluk mumlar: once depo, sonra canli Yahoo, en son kapanis serisi.

    Ucuncu kaynakta high/low YOKTUR; `source` bunu soyler ve o durumda
    aralik gerektiren gostergeler hesaplanmaz.
    """
    repository = get_market_repository()

    try:
        rows = await repository.get_candles(symbol, interval="1d", days=days)
    except Exception:  # noqa: BLE001 - depo hatasi yedek kaynaklari kapatmamali
        logger.warning("gunluk mumlar depodan alinamadi", extra={"symbol": symbol})
        rows = []
    if rows:
        return [
            {
                "ts": str(row["ts"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            for row in rows
        ], "market_candles"

    yahoo_candles = await gunluk_ohlc(symbol, days)
    if yahoo_candles:
        return [
            {
                "ts": str(candle["ts"]),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            }
            for candle in yahoo_candles
        ], "yahoo"

    history = await repository.get_history(symbol, days=days)
    if history:
        return [
            {"ts": str(row["ts"]), "close": float(row["price"])} for row in history
        ], "price_history"

    return [], "yok"


def _build_indicators(
    values: dict[str, float | None], *, has_range: bool
) -> list[TechnicalIndicator]:
    signals = {
        "rsi_14": _threshold_signal(values["rsi_14"], buy_below=30, sell_above=70),
        "stoch_k_9_6": _threshold_signal(values["stoch_k_9_6"], buy_below=20, sell_above=80),
        "macd_12_26_9": _sign_signal(values["macd_12_26_9"]),
        "adx_14": _adx_signal(values),
        "cci_20": _threshold_signal(values["cci_20"], buy_above=100, sell_below=-100),
        "willr_14": _threshold_signal(values["willr_14"], buy_below=-80, sell_above=-20),
        "roc_10": _sign_signal(values["roc_10"]),
    }

    result: list[TechnicalIndicator] = []
    for key, label in INDICATOR_LABELS.items():
        value = values.get(key)
        signal = signals[key]
        if value is None:
            signal = NO_DATA
        elif not has_range and key in RANGE_DEPENDENT:
            value, signal = None, NO_DATA
        result.append(
            TechnicalIndicator(
                key=key,
                label=label,
                value=None if value is None else round(value, 3),
                signal=signal,
            )
        )
    return result


def _build_moving_averages(
    values: dict[int, dict[str, float | None]], price: float
) -> list[TechnicalMovingAverage]:
    """Fiyat ortalamanin ustundeyse Al, altindaysa Sat."""
    return [
        TechnicalMovingAverage(
            period=period,
            sma=_rounded(values[period]["sma"]),
            sma_signal=_price_vs_average(price, values[period]["sma"]),
            ema=_rounded(values[period]["ema"]),
            ema_signal=_price_vs_average(price, values[period]["ema"]),
        )
        for period in MA_PERIODS
    ]


def _price_vs_average(price: float, average: float | None) -> str:
    if average is None:
        return NO_DATA
    if price > average:
        return BUY
    if price < average:
        return SELL
    return NEUTRAL


def _threshold_signal(
    value: float | None,
    *,
    buy_below: float | None = None,
    sell_above: float | None = None,
    buy_above: float | None = None,
    sell_below: float | None = None,
) -> str:
    if value is None:
        return NO_DATA
    if buy_below is not None and value < buy_below:
        return BUY
    if sell_above is not None and value > sell_above:
        return SELL
    if buy_above is not None and value > buy_above:
        return BUY
    if sell_below is not None and value < sell_below:
        return SELL
    return NEUTRAL


def _sign_signal(value: float | None) -> str:
    if value is None:
        return NO_DATA
    if value > 0:
        return BUY
    if value < 0:
        return SELL
    return NEUTRAL


def _adx_signal(values: dict[str, float | None]) -> str:
    """ADX trendin GUCUNU olcer; yon DI+ / DI- farkindan gelir.

    20 altinda trend yok sayilir - yatay piyasada yon okumak gurultudur.
    """
    adx, dmp, dmn = values.get("adx_14"), values.get("_dmp_14"), values.get("_dmn_14")
    if adx is None or dmp is None or dmn is None:
        return NO_DATA
    if adx < 20:
        return NEUTRAL
    if dmp > dmn:
        return BUY
    if dmn > dmp:
        return SELL
    return NEUTRAL


def _summarize(signals) -> TechnicalSummary | None:
    """Sinyalleri tek sinifa toplar; `VERI_YOK` skora GIRMEZ."""
    scored = [_SIGNAL_SCORES[signal] for signal in signals if signal in _SIGNAL_SCORES]
    if not scored:
        return None

    score = sum(scored) / len(scored)
    return TechnicalSummary(
        label=_label(score),
        score=round(score, 3),
        buy=scored.count(1),
        neutral=scored.count(0),
        sell=scored.count(-1),
    )


def _overall_summary(
    indicator_summary: TechnicalSummary | None, ma_summary: TechnicalSummary | None
) -> TechnicalSummary | None:
    """Iki alt ozetin ESIT agirlikli ortalamasi; biri yoksa digeri gecerlidir."""
    parts = [summary for summary in (indicator_summary, ma_summary) if summary is not None]
    if not parts:
        return None

    score = sum(part.score for part in parts) / len(parts)
    return TechnicalSummary(
        label=_label(score),
        score=round(score, 3),
        buy=sum(part.buy for part in parts),
        neutral=sum(part.neutral for part in parts),
        sell=sum(part.sell for part in parts),
    )


def _label(score: float) -> str:
    for threshold, label in SUMMARY_THRESHOLDS:
        if score >= threshold:
            return label
    return STRONG_SELL


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)
