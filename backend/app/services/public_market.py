"""Login oncesi ana sayfa icin veritabanindan piyasa seridi."""

from __future__ import annotations

from typing import Any

from app.repositories.deps import get_market_repository
from app.schemas.public import PublicMarketTickerItem, PublicMarketTickerResponse

# Fiyat scheduler'i bu varliklari Yahoo'dan alip `assets` tablosuna yazar.
# Public ust bar da ayni satirlari okuyarak portfoy hesaplariyla tek kaynaktan
# beslenir. BIST 100/30 veritabaninda varlik olarak bulunmadigi icin bu listeye
# ancak semaya eklendiklerinde alinabilir.
TICKER_SYMBOLS = (
    ("USD/TRY", "$/₺"),
    ("EUR/TRY", "€/₺"),
    ("GRAM_ALTIN", "GRAM ALTIN"),
    ("GUMUS", "GRAM GÜMÜŞ"),
    ("BTC", "BTC"),
    ("ETH", "ETH"),
    ("GARAN", "GARAN"),
    ("THYAO", "THYAO"),
    ("ASELS", "ASELS"),
    ("SASA", "SASA"),
)


async def get_public_market_ticker() -> PublicMarketTickerResponse:
    """Scheduler'in guncelledigi veritabani fiyatlarini dondurur."""
    rows = await get_market_repository().list_assets()
    by_symbol = {str(row["symbol"]).upper(): row for row in rows}

    items: list[PublicMarketTickerItem] = []
    for symbol, label in TICKER_SYMBOLS:
        row = by_symbol.get(symbol)
        if row is None:
            continue

        value = float(row.get("current_price") or 0)
        if value <= 0:
            continue

        change = _optional_float(row.get("daily_change_pct"))
        items.append(
            PublicMarketTickerItem(
                symbol=symbol,
                label=label,
                value=round(value, 4),
                currency=str(row.get("currency") or ""),
                change_percent=round(change, 2) if change is not None else None,
                source="database",
            )
        )

    return PublicMarketTickerResponse(items=items)


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None
