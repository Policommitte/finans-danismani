import pytest
from pydantic import ValidationError

from app.schemas.trading import PercentageBasketAllocation, PercentageBasketPreviewRequest
from app.services import trading


class BasketRepository:
    async def get_account(self, user_id: int):
        return {
            "portfolio_id": 1,
            "portfolio_name": "Ana Portfoy",
            "currency": "TRY",
            "available_balance": 10_215,
            "reserved_balance": 0,
        }

    async def get_order_context(self, user_id: int, symbol: str):
        contexts = {
            "THYAO": {
                "symbol": "THYAO",
                "asset_name": "Turk Hava Yollari",
                "asset_class": "STOCK",
                "currency": "TRY",
                "current_price": 100,
            },
            "AAPL": {
                "symbol": "AAPL",
                "asset_name": "Apple",
                "asset_class": "USA_STOCK",
                "currency": "USD",
                # Repository bu alani kur cevrimi uygulanmis TRY fiyati verir.
                "current_price": 1_000,
            },
            "BTC": {
                "symbol": "BTC",
                "asset_name": "Bitcoin",
                "asset_class": "CRYPTO",
                "currency": "USD",
                "current_price": 1_000_000,
            },
            "USD/TRY": {
                "symbol": "USD/TRY",
                "asset_name": "ABD Dolari",
                "asset_class": "FOREX",
                "currency": "TRY",
                "current_price": 40,
            },
        }
        return contexts.get(symbol)


@pytest.mark.asyncio
async def test_percentage_basket_uses_try_quotes_for_mixed_asset_classes(monkeypatch):
    monkeypatch.setattr(trading, "get_trading_repository", lambda: BasketRepository())
    allocations = [
        PercentageBasketAllocation(symbol="THYAO", weight_pct=25),
        PercentageBasketAllocation(symbol="AAPL", weight_pct=25),
        PercentageBasketAllocation(symbol="BTC", weight_pct=25),
        PercentageBasketAllocation(symbol="USD/TRY", weight_pct=25),
    ]

    result = await trading.yuzdesel_sepet_onizle(1, allocations)

    assert {item.asset_class for item in result.items} == {
        "STOCK",
        "USA_STOCK",
        "CRYPTO",
        "FOREX",
    }
    assert result.estimated_reserve <= result.available_balance
    assert next(item for item in result.items if item.symbol == "AAPL").quantity == 2
    assert next(item for item in result.items if item.symbol == "BTC").quantity == 0.0025
    assert next(item for item in result.items if item.symbol == "USD/TRY").quantity == 62.5


def test_percentage_basket_requires_unique_weights_totalling_one_hundred():
    with pytest.raises(ValidationError):
        PercentageBasketPreviewRequest(
            allocations=[
                {"symbol": "THYAO", "weight_pct": 60},
                {"symbol": "THYAO", "weight_pct": 40},
            ]
        )

    with pytest.raises(ValidationError):
        PercentageBasketPreviewRequest(
            allocations=[
                {"symbol": "THYAO", "weight_pct": 40},
                {"symbol": "BTC", "weight_pct": 40},
            ]
        )
