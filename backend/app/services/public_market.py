"""Login oncesi ana sayfa icin public piyasa verisi."""

from __future__ import annotations

from typing import Any

import httpx

from app.repositories.deps import get_market_repository
from app.schemas.public import PublicMarketTickerItem, PublicMarketTickerResponse

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

LIVE_SYMBOLS = (
    ("XU100.IS", "BIST 100"),
    ("XU030.IS", "BIST 30"),
    ("USDTRY=X", "$/₺"),
    ("EURTRY=X", "€/₺"),
    ("GBPTRY=X", "£/₺"),
    ("GC=F", "XAU/USD"),
    ("SI=F", "XAG/USD"),
    ("BTC-USD", "BTC"),
    ("ETH-USD", "ETH"),
    ("GARAN.IS", "GARAN"),
    ("THYAO.IS", "THYAO"),
    ("ASELS.IS", "ASELS"),
    ("SASA.IS", "SASA"),
)


async def get_public_market_ticker() -> PublicMarketTickerResponse:
    """Piyasa seridini canli kaynaktan getirir; hata olursa demo veriye duser."""
    try:
        live_items = await _fetch_yahoo_ticker()
    except Exception:  # noqa: BLE001 - public landing sayfasi dis kaynakla kirilmamali
        live_items = []

    if live_items:
        return PublicMarketTickerResponse(items=live_items)

    return PublicMarketTickerResponse(items=await _fallback_items())


async def _fetch_yahoo_ticker() -> list[PublicMarketTickerItem]:
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(timeout=8, headers=headers) as client:
        responses = await _gather_quotes(client)

    items: list[PublicMarketTickerItem] = []
    for yahoo_symbol, label, payload in responses:
        quote = _parse_yahoo_payload(payload)
        if quote is None:
            continue
        items.append(
            PublicMarketTickerItem(
                symbol=yahoo_symbol,
                label=label,
                value=quote["value"],
                currency=quote["currency"],
                change_percent=quote["change_percent"],
                source="yahoo",
            )
        )
    return items


async def _gather_quotes(client: httpx.AsyncClient) -> list[tuple[str, str, dict[str, Any]]]:
    results: list[tuple[str, str, dict[str, Any]]] = []
    for symbol, label in LIVE_SYMBOLS:
        response = await client.get(
            YAHOO_CHART_URL.format(symbol=symbol),
            params={"range": "1d", "interval": "5m"},
        )
        response.raise_for_status()
        results.append((symbol, label, response.json()))
    return results


def _parse_yahoo_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        return None

    meta = result.get("meta") or {}
    regular_price = meta.get("regularMarketPrice")
    previous_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    if regular_price is None:
        return None

    change_percent = None
    if previous_close:
        change_percent = round((float(regular_price) - float(previous_close)) / float(previous_close) * 100, 2)

    return {
        "value": round(float(regular_price), 4),
        "currency": meta.get("currency") or "",
        "change_percent": change_percent,
    }


async def _fallback_items() -> list[PublicMarketTickerItem]:
    rows = await get_market_repository().list_assets()
    by_symbol = {row["symbol"]: row for row in rows}

    fallback_map = (
        ("BIST", "BIST Sepet", _stock_basket_value(rows), "TRY", _stock_basket_change(rows)),
        ("USD/TRY", "$/₺", None, "TRY", None),
        ("EUR/TRY", "€/₺", None, "TRY", None),
        ("GRAM_ALTIN", "GAU/₺", None, "TRY", None),
        ("BTC", "BTC", None, "USD", None),
    )

    items: list[PublicMarketTickerItem] = []
    for symbol, label, value_override, currency_override, change_override in fallback_map:
        row = by_symbol.get(symbol)
        value = value_override if value_override is not None else float((row or {}).get("current_price") or 0)
        change = change_override if change_override is not None else (row or {}).get("daily_change_pct")
        if value <= 0:
            continue
        items.append(
            PublicMarketTickerItem(
                symbol=symbol,
                label=label,
                value=round(float(value), 4),
                currency=currency_override or (row or {}).get("currency", ""),
                change_percent=round(float(change), 2) if change is not None else None,
                source="simulated",
            )
        )
    return items


def _stock_basket_value(rows: list[dict[str, Any]]) -> float:
    stocks = [float(row["current_price"]) for row in rows if row.get("asset_class") == "STOCK"]
    if not stocks:
        return 0
    return sum(stocks) / len(stocks) * 100


def _stock_basket_change(rows: list[dict[str, Any]]) -> float | None:
    changes = [
        float(row["daily_change_pct"])
        for row in rows
        if row.get("asset_class") == "STOCK" and row.get("daily_change_pct") is not None
    ]
    if not changes:
        return None
    return sum(changes) / len(changes)
