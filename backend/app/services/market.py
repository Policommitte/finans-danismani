"""Piyasa sekmesi domain servisi."""

from __future__ import annotations

from app.core.errors import NotFoundError
from app.market.yahoo import gunluk_ohlc
from app.repositories.deps import get_market_repository, get_rag_repository
from app.schemas.market import (
    Asset,
    AssetsResponse,
    HistoryResponse,
    MarketSearchResponse,
    OhlcCandle,
    OhlcResponse,
    PricePoint,
    SearchHit,
)

#: Arama sonucunda gonderilen metin uzunlugu. Tam chunk gonderilmez: kart
#: arayuzunde okunmuyor ve yanit gövdesini gereksiz sisiriyor.
EXCERPT_LENGTH = 400


async def varliklar_getir(category: str | None = None) -> AssetsResponse:
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


async def gecmis_getir(symbol: str, days: int = 30) -> HistoryResponse:
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


async def arama_yap(
    query: str, top_k: int = 5, sirket: str | None = None, tip: str | None = None
) -> MarketSearchResponse:
    """RAG destekli piyasa aramasi.

    Ajan cagrisi DEGILDIR: kullanici piyasa sekmesinden dogrudan haber/rapor
    arar, LLM devreye girmez. Bu yuzden ucuz ve hizlidir.
    """
    rows = await get_rag_repository().search(query=query, top_k=top_k, sirket=sirket, tip=tip)

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
                score=_f_opt(row.get("score")),
            )
            for row in rows
        ],
    )


async def en_cok_hareket_edenler(limit: int = 5) -> list[Asset]:
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
        daily_change_pct=_f_opt(row.get("daily_change_pct")),
        weekly_change_pct=_f_opt(row.get("weekly_change_pct")),
        yearly_change_pct=_f_opt(row.get("yearly_change_pct")),
    )


def _f_opt(value) -> float | None:
    return None if value is None else round(float(value), 4)
