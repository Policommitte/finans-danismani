from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import NotFoundError
from app.services.idle_cash import (
    _degisim_imzasi,
    _kalici_katalog_olustur,
    _sepet_geri_testi,
    _tl_bazli_getiriler,
    _uyelik_tarihlerini_guncelle,
    basket_catalog_build,
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
            "volatility_20d_pct": 2.0,
            "volatility_observation_count": 20,
            "price_updated_at": datetime.now(timezone.utc),
        }
        for index, price in enumerate(prices, start=1)
    ]


def test_normal_balance_creates_basket():
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    assets = _assets([100, 140, 180, 220])
    for asset in assets:
        asset["price_updated_at"] = now
    result = suggestion_build(
        _context(),
        assets,
        {},
        "LONG_TERM",
        now=now,
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
        asset(4, "GROWTH", 0.7, 15.0, 32),
        asset(5, "DEFENSIVE", 0.05, -0.1, 2),
    ]
    volatility = {1: 1.0, 2: 2.0, 3: 12.0, 4: 8.0, 5: 0.1}
    for item in assets:
        item["volatility_20d_pct"] = volatility[item["asset_id"]]

    signatures = set()
    for goal in ("LONG_TERM", "GROWTH", "MOMENTUM", "LOW_VOLATILITY"):
        result = suggestion_build(_context(), assets, {}, goal)
        signatures.add(tuple((item.symbol, item.weight_pct) for item in result.items))

    assert len(signatures) == 4


def test_catalog_creates_three_distinct_basket_options():
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assets = _assets([80, 90, 100, 110, 120, 130, 140, 150, 160])
    for asset in assets:
        asset["price_updated_at"] = now
    catalog = basket_catalog_build(
        _context(),
        assets,
        {},
        "LONG_TERM",
        now=now,
    )

    assert catalog.goal == "LONG_TERM"
    assert len(catalog.options) == 3
    assert [option.strategy_key for option in catalog.options] == [
        "CORE",
        "DEFENSIVE",
        "OPPORTUNITY",
    ]
    signatures = {
        tuple((item.asset_id, item.weight_pct) for item in option.suggestion.items)
        for option in catalog.options
    }
    assert len(signatures) == 3
    assert all(
        option.suggestion.estimated_total <= option.suggestion.investable_amount
        for option in catalog.options
    )
    option_sets = [
        {item.asset_id for item in option.suggestion.items} for option in catalog.options
    ]
    assert all(
        len(first & second) / len(first | second) <= 0.60
        for index, first in enumerate(option_sets)
        for second in option_sets[index + 1 :]
    )
    assert all(option.metrics.diversification_score >= 0 for option in catalog.options)


def test_catalog_does_not_repeat_when_asset_pool_is_small():
    catalog = basket_catalog_build(_context(100), _assets([80]), {}, "LONG_TERM")

    assert len(catalog.options) == 1


def _mixed_assets() -> list[dict]:
    classes = [
        "STOCK",
        "STOCK",
        "USA_STOCK",
        "USA_STOCK",
        "ETF",
        "ETF",
        "GOLD",
        "FOREX",
        "COMMODITY",
        "CRYPTO",
        "CRYPTO",
        "BOND",
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
            "volatility_20d_pct": 2.0,
            "volatility_observation_count": 20,
            "price_updated_at": datetime.now(timezone.utc),
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


def test_stale_prices_are_excluded_and_reported():
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assets = _assets([100, 110])
    assets[0]["price_updated_at"] = now - timedelta(days=5)
    assets[1]["price_updated_at"] = now

    catalog = basket_catalog_build(_context(), assets, {}, "LONG_TERM", now=now)

    assert catalog.stale_asset_count == 1
    assert catalog.eligible_asset_count == 1
    assert catalog.options[0].suggestion.items[0].asset_id == assets[1]["asset_id"]


def test_low_volatility_requires_twenty_daily_returns():
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assets = _assets([100, 110])
    for asset in assets:
        asset["price_updated_at"] = now
    assets[0]["volatility_observation_count"] = 19

    catalog = basket_catalog_build(_context(), assets, {}, "LOW_VOLATILITY", now=now)

    assert catalog.insufficient_history_asset_count == 1
    assert catalog.eligible_asset_count == 1
    assert catalog.options[0].suggestion.items[0].asset_id == assets[1]["asset_id"]


def test_goal_relative_rank_replaces_public_raw_score():
    result = suggestion_build(_context(), _assets([100]), {}, "LONG_TERM")
    item = result.items[0]

    assert item.score_components
    assert item.goal_rank == 1
    assert item.candidate_count == 1
    assert item.suitability_level == "HIGH"


def test_membership_dates_are_preserved_per_asset():
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = datetime(2026, 2, 1, tzinfo=timezone.utc)
    dates = {"0:1": old.isoformat(), "0:2": old.isoformat(), "1:4": old.isoformat()}

    updated = _uyelik_tarihlerini_guncelle(dates, [[1, 3], [4]], now)

    assert updated["0:1"] == old.isoformat()
    assert updated["0:3"] == now.isoformat()
    assert updated["1:4"] == old.isoformat()
    assert "0:2" not in updated


def test_change_signal_signature_depends_on_actual_asset_pair():
    assert _degisim_imzasi([1, 2], [1, 3]) == "2->3"
    assert _degisim_imzasi([1, 2], [1, 4]) == "2->4"


def test_risk_based_weights_give_lower_volatility_more_weight():
    assets = _assets([100, 100, 100, 100])
    for asset, volatility in zip(assets, [1.0, 2.0, 3.0, 4.0]):
        asset["volatility_20d_pct"] = volatility

    result = suggestion_build(_context(), assets, {}, "LONG_TERM", strategy_index=1)
    weights = {item.asset_id: item.weight_pct for item in result.items}

    assert weights[assets[0]["asset_id"]] > weights[assets[-1]["asset_id"]]


def test_defensive_strategy_rejects_highly_correlated_pair():
    assets = _assets([100, 100, 100])
    common = {f"2026-01-{day:02d}": float(day) for day in range(1, 31)}
    inverse = {day: -value for day, value in common.items()}
    assets[0]["daily_returns_60d"] = common
    assets[1]["daily_returns_60d"] = dict(common)
    assets[2]["daily_returns_60d"] = inverse

    result = suggestion_build(_context(), assets, {}, "LONG_TERM", strategy_index=1)
    selected = {item.asset_id for item in result.items}

    assert not {assets[0]["asset_id"], assets[1]["asset_id"]} <= selected


def _daily_returns(count: int, value_factory) -> dict[str, float]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return {
        (start + timedelta(days=index)).date().isoformat(): float(value_factory(index))
        for index in range(count)
    }


def test_backtest_includes_cost_benchmark_and_risk_metrics():
    assets = _assets([100, 100, 100])
    for asset in assets:
        asset["currency"] = "TRY"
    assets[0]["daily_returns_252d"] = _daily_returns(40, lambda index: 1.0 if index < 20 else -0.4)
    assets[1]["daily_returns_252d"] = _daily_returns(
        40, lambda index: 0.5 if index % 2 == 0 else -0.2
    )
    assets[2]["daily_returns_252d"] = _daily_returns(40, lambda _index: 0.1)

    result = _sepet_geri_testi(assets[:2], [0.6, 0.4], assets, assets, "LONG_TERM")

    assert result.status == "LIMITED"
    assert result.observation_count == 40
    assert result.net_return_pct is not None
    assert result.gross_return_pct is not None
    assert result.net_return_pct < result.gross_return_pct
    assert result.benchmark_return_pct is not None
    assert result.max_drawdown_pct is not None and result.max_drawdown_pct > 0
    assert result.annualized_volatility_pct is not None
    assert result.transaction_cost_impact_pct is not None
    assert result.transaction_cost_impact_pct > 0


def test_backtest_reports_insufficient_common_history():
    assets = _assets([100, 100])
    assets[0]["daily_returns_252d"] = _daily_returns(19, lambda _index: 0.1)
    assets[1]["daily_returns_252d"] = _daily_returns(19, lambda _index: 0.2)

    result = _sepet_geri_testi(assets, [0.5, 0.5], assets, assets, "LONG_TERM")

    assert result.status == "INSUFFICIENT"
    assert result.observation_count == 19
    assert result.net_return_pct is None


def test_foreign_asset_return_is_converted_to_try():
    usd_asset = {
        **_assets([100])[0],
        "symbol": "AAPL",
        "currency": "USD",
        "daily_returns_252d": {"2026-01-02": 1.0},
    }
    usd_try = {
        **_assets([100])[0],
        "asset_id": 99,
        "symbol": "USD/TRY",
        "currency": "TRY",
        "daily_returns_252d": {"2026-01-02": 2.0},
    }

    result = _tl_bazli_getiriler(usd_asset, [usd_asset, usd_try])

    assert result["2026-01-02"] == pytest.approx(3.02)


class _BasketStateRepository:
    def __init__(self):
        self.state = None

    async def get_basket_state(self, user_id: int, goal: str):
        return dict(self.state) if self.state else None

    async def upsert_basket_state(self, user_id: int, goal: str, state: dict):
        self.state = {"user_id": user_id, "goal": goal, **state}
        return dict(self.state)


@pytest.mark.asyncio
async def test_long_term_membership_needs_minimum_time_and_two_confirmations():
    repository = _BasketStateRepository()
    context = _context(100_000, "MEDIUM")
    assets = _assets([100] * 10)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for asset in assets:
        asset["price_updated_at"] = start

    initial = await _kalici_katalog_olustur(repository, 1, context, assets, {}, "LONG_TERM", start)
    initial_memberships = [
        [item.asset_id for item in option.suggestion.items] for option in initial.options
    ]

    for asset in assets:
        asset["yearly_change_pct"] = 150 if asset["asset_id"] <= 5 else -100
        asset["price_updated_at"] = start + timedelta(days=31)

    first_review = await _kalici_katalog_olustur(
        repository, 1, context, assets, {}, "LONG_TERM", start + timedelta(days=31)
    )
    first_memberships = [
        [item.asset_id for item in option.suggestion.items] for option in first_review.options
    ]
    assert first_memberships == initial_memberships
    assert first_review.membership_changed is False

    for asset in assets:
        asset["price_updated_at"] = start + timedelta(days=38)
    second_review = await _kalici_katalog_olustur(
        repository, 1, context, assets, {}, "LONG_TERM", start + timedelta(days=38)
    )
    second_memberships = [
        [item.asset_id for item in option.suggestion.items] for option in second_review.options
    ]
    assert second_memberships != initial_memberships
    assert second_review.membership_changed is True


@pytest.mark.asyncio
async def test_low_volatility_emergency_exit_bypasses_minimum_hold():
    repository = _BasketStateRepository()
    context = _context(100_000, "MEDIUM")
    assets = _assets([100] * 10)
    for asset in assets:
        asset["volatility_20d_pct"] = 1.0
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for asset in assets:
        asset["price_updated_at"] = start

    initial = await _kalici_katalog_olustur(
        repository, 1, context, assets, {}, "LOW_VOLATILITY", start
    )
    first_asset_id = initial.options[0].suggestion.items[0].asset_id
    for asset in assets:
        if asset["asset_id"] == first_asset_id:
            asset["volatility_20d_pct"] = 20.0

    reviewed = await _kalici_katalog_olustur(
        repository, 1, context, assets, {}, "LOW_VOLATILITY", start + timedelta(days=1)
    )
    reviewed_ids = [item.asset_id for item in reviewed.options[0].suggestion.items]

    assert first_asset_id not in reviewed_ids
    assert reviewed.membership_changed is True


@pytest.mark.asyncio
async def test_different_replacement_candidate_restarts_confirmation_count():
    repository = _BasketStateRepository()
    context = _context(100_000, "MEDIUM")
    assets = _assets([100] * 10)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for asset in assets:
        asset["price_updated_at"] = start

    await _kalici_katalog_olustur(repository, 1, context, assets, {}, "LONG_TERM", start)

    for asset in assets:
        asset["yearly_change_pct"] = 150 if asset["asset_id"] <= 5 else -100
        asset["price_updated_at"] = start + timedelta(days=31)
    await _kalici_katalog_olustur(
        repository, 1, context, assets, {}, "LONG_TERM", start + timedelta(days=31)
    )
    first_signals = dict(repository.state["change_signals"])
    assert first_signals

    for asset in assets:
        asset["yearly_change_pct"] = 150 if 3 <= asset["asset_id"] <= 7 else -100
        asset["price_updated_at"] = start + timedelta(days=38)
    reviewed = await _kalici_katalog_olustur(
        repository, 1, context, assets, {}, "LONG_TERM", start + timedelta(days=38)
    )

    assert reviewed.membership_changed is False
    assert repository.state["change_signals"]
    assert all(signal["count"] == 1 for signal in repository.state["change_signals"].values())
