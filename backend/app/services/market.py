"""Piyasa sekmesi domain servisi."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.errors import NotFoundError
from app.market.yahoo import gunluk_ohlc
from app.repositories.deps import get_market_repository, get_rag_repository
from app.schemas.market import (
    Asset,
    AssetsResponse,
    Candle,
    CandlesResponse,
    HistoryResponse,
    MarketSearchResponse,
    OhlcCandle,
    OhlcResponse,
    PhotoResponse,
    PricePoint,
    SearchHit,
)
from app.services.pexels import cached_photo

#: Arama sonucunda gonderilen metin uzunlugu. Tam chunk gonderilmez: kart
#: arayuzunde okunmuyor ve yanit gövdesini gereksiz sisiriyor.
EXCERPT_LENGTH = 400

INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}
RANGE_DAYS = {"1d": 1, "5d": 5, "1m": 30, "3m": 90, "1y": 365}
#: Kaynak mum serisi basina ASGARI yukleme penceresi (gun). Grafik sola
#: kaydirilabilsin diye gorunen aralik kadar degil, daha fazlasi yuklenir.
#:
#: ⚠️ ESKIDEN "1h": 730 idi ve HER aralikta uygulaniyordu: market sayfasinin
#: varsayilan 1 aylik/saatlik grafigi icin iki yillik saatlik arsivin tamami
#: (binlerce satir, yuz kilobaytlarca JSON) cekiliyor, ustelik 60 sn'de bir
#: tazeleniyordu - ve bu istek sayfa gecis perdesinin bekledigi istekti.
#: Tampon artik gorunen aralikla OLCEKLENIR (bkz. `_history_day_count`);
#: yillik gorunum yine tam arsivi alir, aylik gorunum almaz.
HISTORY_BUFFER_DAYS = {"1m": 30, "5m": 60, "1h": 120, "1d": 730}
#: Depodaki en uzun arsiv (015_hourly_market_candles.sql: saatlik mumlar iki
#: yil tutulur). Hicbir istek bunun otesini istemez.
HISTORY_ARCHIVE_DAYS = 730
#: Sola kaydirma payi: gorunen aralik kadar daha eski veri.
HISTORY_SCROLL_FACTOR = 2
CHART_TIME_ZONE = ZoneInfo("Europe/Istanbul")


def _history_day_count(range_key: str, kaynak_interval: str) -> int:
    """Grafik icin depodan istenecek gun sayisi.

    Gorunen araligin `HISTORY_SCROLL_FACTOR` kati (sola kaydirma payi), kaynak
    serinin asgari tamponunun altina inmeden, arsiv sinirini asmadan:

        1m / 1h  -> max(60, 120)  = 120   (eskiden 730)
        3m / 1h  -> max(180, 120) = 180   (eskiden 730)
        1y / 1h  -> min(730, 730) = 730   (degismedi - tam arsiv)
        1d / 5m  -> max(2, 60)    = 60    (degismedi)
    """
    gorunen = RANGE_DAYS[range_key]
    return min(
        HISTORY_ARCHIVE_DAYS,
        max(gorunen * HISTORY_SCROLL_FACTOR, HISTORY_BUFFER_DAYS[kaynak_interval]),
    )


def _kaynak_mum_araligi(interval: str, range_key: str) -> str:
    """Istenen grafik icin depodaki en ayrintili uygun mum serisini secer."""
    if interval == "1m":
        return "1m"
    if interval in {"1h", "4h"}:
        return "1h"
    if interval == "1d":
        return "1d"
    return "5m"


async def list_assets(category: str | None = None) -> AssetsResponse:
    rows = await get_market_repository().list_assets(category)
    return AssetsResponse(items=[_asset(row) for row in rows])


#: `price_history` GUNLUK granulerlikte tutulur ve her satirin zaman damgasi
#: O GUNUN GECE YARISIDIR (bkz. sql.py close_out_day). Bu yuzden `days=1`
#: (1G sekmesi) ile sorgulanirsa `now() - 1 gun` siniri DUN'un kapanisini bile
#: DISLAR (dun 00:00, "simdi - 1 gun"den her zaman ONCE gelir) - sonuc HER
#: SEMBOLDE, HER ZAMAN bos doner ve 404 firlatilirdi. Sorgu penceresi burada
#: taban degerle genisletilir; DONEN `days` alani yine kullanicinin istedigi
#: deger olarak kalir (sadece veritabani sorgusu genisler).
_MIN_SORGU_GUN = 3


async def get_price_history(symbol: str, days: int = 30) -> HistoryResponse:
    """PriceChart icin HAM zaman serisi.

    MCP tool'undan (`market_get_history`) farkli olarak burada ozetleme yoktur:
    grafik tum noktalara ihtiyac duyar, LLM ise duymaz.
    """
    rows = await get_market_repository().get_history(symbol, days=max(days, _MIN_SORGU_GUN))
    if not rows:
        raise NotFoundError(f"'{symbol}' icin fiyat gecmisi bulunamadi.")

    return HistoryResponse(
        symbol=symbol.upper(),
        days=days,
        points=[PricePoint(ts=str(row["ts"]), price=round(float(row["price"]), 4)) for row in rows],
    )


async def ohlc_getir(symbol: str, days: int = 30) -> OhlcResponse:
    """Mum grafik icin GERCEK gunluk OHLC serisi (bkz. app/market/yahoo.py).

    Veri alinamazsa (turetilmis sembol, ag hatasi) bos `candles` doner -
    404 FIRLATILMAZ: frontend bunu "bu sembol icin mum grafigi yok, cizgiye
    duş" olarak yorumlar, bu beklenen/gecerli bir durumdur.
    """
    mumlar = await gunluk_ohlc(symbol.upper(), days)
    return OhlcResponse(
        symbol=symbol.upper(),
        days=days,
        candles=[OhlcCandle(**mum) for mum in (mumlar or [])],
    )


async def mumlar_getir(symbol: str, interval: str, range_key: str) -> CandlesResponse:
    """Dogrulanmis fiyat noktalarini OHLC zaman kovalarina toplar."""
    repository = get_market_repository()
    kaynak_interval = _kaynak_mum_araligi(interval, range_key)
    # Tarih secimi ilk gorunen pencereyi belirler. Daha eski mumlari da
    # yukleyerek grafigin sola kaydirilabilmesini saglariz - ama gorunen
    # aralikla orantili olarak (bkz. `_history_day_count`).
    days = _history_day_count(range_key, kaynak_interval)
    ohlcv_rows = await repository.get_candles(symbol, interval=kaynak_interval, days=days)
    if ohlcv_rows:
        if interval == "1h" and kaynak_interval == "1h":
            candles = _ohlcv_dogrudan(ohlcv_rows)
        elif interval == "4h" and kaynak_interval == "1h":
            candles = _dort_saatlik_mumlara_topla(ohlcv_rows)
        else:
            candles = _ohlcv_topla(ohlcv_rows, INTERVAL_SECONDS[interval])
        return CandlesResponse(
            symbol=symbol.upper(),
            interval=interval,
            range=range_key,
            candles=candles,
        )

    # OHLCV tablosu henuz dolmadiysa eski tekil fiyat serisine geri dus.
    rows = await repository.get_history(symbol, days=days)
    if not rows:
        raise NotFoundError(f"'{symbol}' icin fiyat gecmisi bulunamadi.")

    bucket_seconds = INTERVAL_SECONDS[interval]
    buckets: dict[int, dict[str, float]] = {}
    for row in rows:
        timestamp = _unix_seconds(row["ts"])
        bucket = _standart_mum_kovasi(timestamp, bucket_seconds)
        price = float(row["price"])
        candle = buckets.get(bucket)
        if candle is None:
            buckets[bucket] = {"open": price, "high": price, "low": price, "close": price}
            continue
        candle["high"] = max(candle["high"], price)
        candle["low"] = min(candle["low"], price)
        candle["close"] = price

    return CandlesResponse(
        symbol=symbol.upper(),
        interval=interval,
        range=range_key,
        candles=[
            Candle(
                time=bucket,
                open=round(values["open"], 4),
                high=round(values["high"], 4),
                low=round(values["low"], 4),
                close=round(values["close"], 4),
            )
            for bucket, values in sorted(buckets.items())
        ],
    )


def _ohlcv_topla(rows: list[dict], bucket_seconds: int) -> list[Candle]:
    buckets: dict[int, dict] = {}
    for row in rows:
        timestamp = _unix_seconds(row["ts"])
        bucket = _standart_mum_kovasi(timestamp, bucket_seconds)
        candle = buckets.get(bucket)
        volume = None if row.get("volume") is None else float(row["volume"])
        if candle is None:
            buckets[bucket] = {
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": volume,
            }
            continue
        candle["high"] = max(candle["high"], float(row["high"]))
        candle["low"] = min(candle["low"], float(row["low"]))
        candle["close"] = float(row["close"])
        if volume is not None:
            candle["volume"] = (candle["volume"] or 0) + volume

    return [
        Candle(
            time=bucket,
            open=round(values["open"], 4),
            high=round(values["high"], 4),
            low=round(values["low"], 4),
            close=round(values["close"], 4),
            volume=(round(values["volume"], 4) if values["volume"] is not None else None),
        )
        for bucket, values in sorted(buckets.items())
    ]


def _ohlcv_dogrudan(rows: list[dict]) -> list[Candle]:
    """Kaynak mum zamanini yeniden kovalamadan API modeline cevirir."""
    return [
        Candle(
            time=_unix_seconds(row["ts"]),
            open=round(float(row["open"]), 4),
            high=round(float(row["high"]), 4),
            low=round(float(row["low"]), 4),
            close=round(float(row["close"]), 4),
            volume=(round(float(row["volume"]), 4) if row.get("volume") is not None else None),
        )
        for row in rows
    ]


def _dort_saatlik_mumlara_topla(rows: list[dict]) -> list[Candle]:
    """Her piyasa gununun ilk gercek 1h mumundan baslayarak dorderli toplar."""
    by_day: dict[object, list[dict]] = {}
    for row in sorted(rows, key=lambda item: _unix_seconds(item["ts"])):
        timestamp = _unix_seconds(row["ts"])
        day = datetime.fromtimestamp(timestamp, tz=CHART_TIME_ZONE).date()
        by_day.setdefault(day, []).append(row)

    result: list[Candle] = []
    for day_rows in by_day.values():
        first = _unix_seconds(day_rows[0]["ts"])
        buckets: dict[int, list[dict]] = {}
        for row in day_rows:
            timestamp = _unix_seconds(row["ts"])
            offset = (timestamp - first) // INTERVAL_SECONDS["4h"]
            bucket = first + offset * INTERVAL_SECONDS["4h"]
            buckets.setdefault(bucket, []).append(row)
        for bucket, group in buckets.items():
            volumes = [float(row["volume"]) for row in group if row.get("volume") is not None]
            result.append(
                Candle(
                    time=bucket,
                    open=round(float(group[0]["open"]), 4),
                    high=round(max(float(row["high"]) for row in group), 4),
                    low=round(min(float(row["low"]) for row in group), 4),
                    close=round(float(group[-1]["close"]), 4),
                    volume=round(sum(volumes), 4) if volumes else None,
                )
            )
    return sorted(result, key=lambda candle: candle.time)


def _standart_mum_kovasi(timestamp: int, bucket_seconds: int) -> int:
    """Gun ici mumlari grafikte gosterilen Istanbul saatine hizalar."""
    if bucket_seconds >= INTERVAL_SECONDS["1d"]:
        return timestamp - timestamp % bucket_seconds

    local_time = datetime.fromtimestamp(timestamp, tz=CHART_TIME_ZONE)
    local_midnight = local_time.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = int((local_time - local_midnight).total_seconds())
    bucket_start = seconds_since_midnight - seconds_since_midnight % bucket_seconds
    return int((local_midnight + timedelta(seconds=bucket_start)).timestamp())


async def fotograf_getir(query: str) -> PhotoResponse:
    """Genel amacli Pexels fotograf aramasi (bkz. app/services/pexels.py).

    Portfoy varligi kapak gorseli (bulten "Portfoyden" karti) ve Yatirim
    Oyunu magaza karti gorselleri gibi, TEK bir habere/dokumana bagli
    OLMAYAN gorsel ihtiyaclari icin - `resolve_image` (news.py) haber
    basina DB'ye yazan bir onbellek kullanirken, bu fonksiyon sadece
    sorgu-anahtarli, process-ici bir onbellek kullanir (bkz. cached_photo).
    """
    url = await cached_photo(query)
    return PhotoResponse(query=query, url=url)


async def search_assets(
    query: str, top_k: int = 5, sirket: str | None = None, tip: str | None = None
) -> MarketSearchResponse:
    """RAG destekli piyasa aramasi.

    Ajan cagrisi DEGILDIR: kullanici piyasa sekmesinden dogrudan haber/rapor
    arar, LLM devreye girmez. Bu yuzden ucuz ve hizlidir.
    """
    rows = await get_rag_repository().hybrid_search(
        query=query, top_k=top_k, sirket=sirket, tip=tip
    )

    return MarketSearchResponse(
        query=query,
        items=[
            SearchHit(
                doc_id=str(row.get("doc_id") or row.get("chunk_id") or ""),
                baslik=row.get("baslik"),
                sirket=row.get("sirket"),
                symbol=row.get("symbol"),
                tarih=str(row.get("tarih") or "") or None,
                tip=row.get("tip"),
                excerpt=(row.get("content") or "")[:EXCERPT_LENGTH],
                score=_optional_float(row.get("score")),
            )
            for row in rows
        ],
    )


async def top_movers(limit: int = 5) -> list[Asset]:
    """Gun icinde mutlak degisimi en yuksek varliklar (dashboard karti)."""
    rows = await get_market_repository().list_assets()
    rows.sort(key=lambda r: abs(float(r.get("daily_change_pct") or 0)), reverse=True)
    return [_asset(row) for row in rows[:limit]]


def _asset(row: dict) -> Asset:
    return Asset(
        symbol=row["symbol"],
        name=row["name"],
        asset_class=row["asset_class"],
        currency=row["currency"],
        current_price=round(float(row["current_price"]), 4),
        daily_change_pct=_optional_float(row.get("daily_change_pct")),
        weekly_change_pct=_optional_float(row.get("weekly_change_pct")),
        yearly_change_pct=_optional_float(row.get("yearly_change_pct")),
    )


def _optional_float(value) -> float | None:
    return None if value is None else round(float(value), 4)


def _unix_seconds(value) -> int:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())
