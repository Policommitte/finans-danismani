from datetime import datetime, timezone

import pytest

from app.core.errors import NotFoundError
from app.services.idle_cash import (
    basket_catalog_build,
    hedef_belirle,
    idle_cash_request_mi,
    suggestion_build,
)


def _context(balance: float = 10_000, risk: str = "MEDIUM") -> dict:
    return {
        "risk_tolerance": risk,
        "idle_balance_try": balance,
        "available_balance": 2_000,
        "portfolio_id": 1,
        "allowed_asset_classes": ["STOCK"],
    }


def _assets(prices: list[float]) -> list[dict]:
    return [
        {
            "asset_id": index,
            "symbol": f"STK{index}",
            "name": f"Hisse {index}",
            "asset_class": "STOCK",
            "current_price": price,
            "daily_change_pct": index * 0.1,
            "weekly_change_pct": index * 0.4,
            "yearly_change_pct": index * 2,
        }
        for index, price in enumerate(prices, start=1)
    ]


@pytest.mark.parametrize(
    "message",
    [
        "Atıl bakiyemi nasıl değerlendirebilirim?",
        "Paramla ne almalıyım?",
        "Bana bir hisse sepeti öner",
        "Boşta duran nakdimi kullanmak istiyorum",
        "Bakiyem ne kadar?",
    ],
)
def test_idle_cash_intent_variations(message: str):
    assert idle_cash_request_mi(message)


def test_negative_intent_is_not_intercepted():
    assert not idle_cash_request_mi("Bana hisse sepeti önerme")


def test_goal_is_inferred_from_free_text():
    assert hedef_belirle("Uzun vadeli birikim yapmak istiyorum") == "LONG_TERM"
    assert hedef_belirle("Agresif büyüme istiyorum") == "GROWTH"
    assert hedef_belirle("Kısa vadeli momentum arıyorum") == "MOMENTUM"
    assert hedef_belirle("Düşük oynaklık istiyorum") == "LOW_VOLATILITY"
    assert hedef_belirle("Bana bir sepet hazırla") == "LONG_TERM"


def test_normal_balance_creates_basket():
    result = suggestion_build(
        _context(),
        _assets([100, 140, 180, 220]),
        {},
        "LONG_TERM",
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )

    assert result.mode == "basket"
    assert len(result.items) == 4
    assert result.available_balance == 10_000
    assert result.estimated_total <= result.investable_amount
    assert result.unallocated_balance == pytest.approx(10_000 - result.estimated_total)


def test_small_balance_falls_back_to_single_stock():
    result = suggestion_build(_context(100), _assets([80, 90, 95]), {}, "LONG_TERM")

    assert result.mode == "single"
    assert len(result.items) == 1
    assert result.items[0].quantity == 1


def test_missing_market_data_is_exception_scenario():
    with pytest.raises(NotFoundError, match="piyasa verisi"):
        suggestion_build(_context(), [], {}, "LONG_TERM")


def test_each_goal_changes_selection_or_allocation():
    def asset(asset_id: int, symbol: str, daily: float, weekly: float, yearly: float):
        return {
            **_assets([100])[0],
            "asset_id": asset_id,
            "symbol": symbol,
            "daily_change_pct": daily,
            "weekly_change_pct": weekly,
            "yearly_change_pct": yearly,
        }

    assets = [
        asset(1, "STABLE", 0.1, 0.2, 6),
        asset(2, "LONG", 0.4, 1.0, 35),
        asset(3, "MOMENTUM", 4.0, 18.0, 12),
        asset(4, "GROWTH", 0.7, 3.0, 18),
        asset(5, "DEFENSIVE", 0.05, -0.1, 2),
    ]

    signatures = set()
    for goal in ("LONG_TERM", "GROWTH", "MOMENTUM", "LOW_VOLATILITY"):
        result = suggestion_build(_context(), assets, {}, goal)
        signatures.add(tuple((item.symbol, item.weight_pct) for item in result.items))

    assert len(signatures) == 4


def test_catalog_creates_three_distinct_basket_options():
    assets = _assets([80, 90, 100, 110, 120, 130, 140, 150, 160])
    catalog = basket_catalog_build(
        _context(),
        assets,
        {},
        "LONG_TERM",
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    assert catalog.goal == "LONG_TERM"
    assert len(catalog.options) == 3
    signatures = {
        tuple((item.asset_id, item.weight_pct) for item in option.suggestion.items)
        for option in catalog.options
    }
    assert len(signatures) == 3
    assert all(
        option.suggestion.estimated_total <= option.suggestion.investable_amount
        for option in catalog.options
    )


def test_catalog_does_not_repeat_when_asset_pool_is_small():
    catalog = basket_catalog_build(_context(100), _assets([80]), {}, "LONG_TERM")

    assert len(catalog.options) == 1


def _mixed_assets() -> list[dict]:
    classes = [
        "STOCK", "STOCK", "USA_STOCK", "USA_STOCK", "ETF", "ETF",
        "GOLD", "FOREX", "COMMODITY", "CRYPTO", "CRYPTO", "BOND",
    ]
    return [
        {
            "asset_id": index,
            "symbol": "US10Y" if asset_class == "BOND" else f"A{index}",
            "name": f"Varlik {index}",
            "asset_class": asset_class,
            "currency": "PCT" if asset_class == "BOND" else "TRY",
            "current_price": 100 + index,
            "daily_change_pct": index / 10,
            "weekly_change_pct": index / 4,
            "yearly_change_pct": index * 2,
        }
        for index, asset_class in enumerate(classes, start=1)
    ]


@pytest.mark.parametrize(
    ("risk", "crypto_limit"),
    [("LOW", 0), ("MEDIUM", 1), ("HIGH", 2)],
)
def test_risk_profile_limits_crypto_and_diversifies_classes(risk: str, crypto_limit: int):
    context = _context(100_000, risk)
    context["allowed_asset_classes"] = []
    result = suggestion_build(context, _mixed_assets(), {}, "GROWTH")

    classes = [item.asset_class for item in result.items]
    assert 3 <= len(result.items) <= 6
    assert classes.count("CRYPTO") <= crypto_limit
    assert "BOND" not in classes
    assert len(set(classes)) >= 2


def test_quantity_rules_support_fractional_crypto_and_whole_stocks():
    assets = _mixed_assets()
    for asset in assets:
        if asset["asset_class"] == "CRYPTO":
            asset["current_price"] = 3_000_000
            asset["yearly_change_pct"] = 150
    context = _context(10_000, "HIGH")
    context["allowed_asset_classes"] = ["STOCK", "CRYPTO"]
    result = suggestion_build(context, assets, {}, "GROWTH")

    crypto = next(item for item in result.items if item.asset_class == "CRYPTO")
    stocks = [item for item in result.items if item.asset_class == "STOCK"]
    assert 0 < crypto.quantity < 1
    assert all(item.quantity.is_integer() for item in stocks)


def test_explicit_allowed_asset_classes_are_respected():
    context = _context(100_000)
    context["allowed_asset_classes"] = ["ETF", "GOLD"]
    result = suggestion_build(context, _mixed_assets(), {}, "LONG_TERM")

    assert {item.asset_class for item in result.items} <= {"ETF", "GOLD"}


def test_catalog_reports_full_universe_and_trade_eligible_count():
    context = _context(100_000)
    context["allowed_asset_classes"] = []
    catalog = basket_catalog_build(context, _mixed_assets(), {}, "LONG_TERM")

    assert catalog.universe_size == 12
    assert catalog.eligible_asset_count == 11
