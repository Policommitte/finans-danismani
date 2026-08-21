from decimal import Decimal

import pytest

from app.services import public_market


class _MarketRepository:
    async def list_assets(self):
        return [
            {
                "symbol": "BTC",
                "currency": "USD",
                "current_price": Decimal("76390.1256"),
                "daily_change_pct": Decimal("4.5962"),
            },
            {
                "symbol": "THYAO",
                "currency": "TRY",
                "current_price": Decimal("303.00"),
                "daily_change_pct": Decimal("0.4975"),
            },
        ]


@pytest.mark.asyncio
async def test_public_ticker_reads_database_prices(monkeypatch):
    monkeypatch.setattr(public_market, "get_market_repository", lambda: _MarketRepository())

    response = await public_market.get_public_market_ticker()

    assert [item.symbol for item in response.items] == ["BTC", "THYAO"]
    assert response.items[0].value == 76390.1256
    assert response.items[0].change_percent == 4.6
    assert all(item.source == "database" for item in response.items)
