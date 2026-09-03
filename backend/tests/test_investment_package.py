from datetime import datetime, timezone

import pytest

from app.core.errors import BusinessRuleError
from app.schemas.investment_package import InvestmentPackageRequest
from app.services.investment_package import build_package, select_strategy_key


def _context(balance: float = 10_000, risk: str = "MEDIUM") -> dict:
    return {
        "risk_tolerance": risk,
        "available_balance": balance,
        "portfolio_id": 1,
        "allowed_asset_classes": ["STOCK"],
    }


def _assets(prices: list[float]) -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "asset_id": index,
            "symbol": f"STK{index}",
            "name": f"Hisse {index}",
            "asset_class": "STOCK",
            "sector": f"S{index % 3}",
            "region": "TR",
            "current_price": price,
            "daily_change_pct": index * 0.1,
            "weekly_change_pct": index * 0.4,
            "yearly_change_pct": index * 2,
            "volatility_20d_pct": 2.0,
            "volatility_observation_count": 20,
            "price_updated_at": now,
        }
        for index, price in enumerate(prices, start=1)
    ]


@pytest.mark.parametrize(
    ("horizon", "risk", "expected"),
    [
        ("SHORT", "HIGH", "DEFENSIVE"),
        ("SHORT", "LOW", "DEFENSIVE"),
        ("MEDIUM", "MEDIUM", "CORE"),
        ("LONG", "MEDIUM", "CORE"),
        ("LONG", "HIGH", "OPPORTUNITY"),
    ],
)
def test_strategy_follows_horizon_and_risk(horizon, risk, expected):
    assert select_strategy_key(horizon, risk) == expected


def test_package_uses_requested_budget_not_cash_balance():
    request = InvestmentPackageRequest(
        amount=5_000, horizon="LONG", risk_profile="HIGH", goal="GROWTH"
    )
    package = build_package(
        _context(balance=50_000, risk="LOW"), _assets([100, 140, 180, 220]), {}, request
    )

    assert package.requested_amount == 5_000
    assert package.available_balance == 50_000
    assert package.exceeds_balance is False
    assert package.risk_profile == "HIGH"
    assert package.suggestion.risk_profile == "HIGH"
    assert package.suggestion.investable_amount == 5_000
    assert package.suggestion.estimated_total <= 5_000
    assert package.strategy_key == "OPPORTUNITY"
    assert package.title
    assert "5.000 TL" in package.summary
    assert package.metrics.largest_weight_pct <= 100


def test_package_flags_budget_above_cash_balance():
    request = InvestmentPackageRequest(
        amount=20_000, horizon="SHORT", risk_profile="LOW", goal="LOW_VOLATILITY"
    )
    package = build_package(_context(balance=1_000), _assets([100, 140, 180, 220]), {}, request)

    assert package.exceeds_balance is True
    assert package.strategy_key == "DEFENSIVE"


def test_budget_too_small_for_any_asset_raises_business_rule():
    request = InvestmentPackageRequest(
        amount=50, horizon="MEDIUM", risk_profile="MEDIUM", goal="LONG_TERM"
    )
    with pytest.raises(BusinessRuleError):
        build_package(_context(), _assets([100, 140]), {}, request)
