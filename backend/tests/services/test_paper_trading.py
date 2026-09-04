"""Paper trading emir yasam dongusu testleri."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import BusinessRuleError
from app.repositories.in_memory import (
    InMemoryPortfolioRepository,
    InMemoryTradingRepository,
    reset_data,
)


@pytest.fixture
def repository():
    reset_data()
    return InMemoryTradingRepository()


@pytest.mark.asyncio
async def test_buy_order_reserves_cash_and_fills_on_next_verified_tick(repository):
    before = await repository.get_account(1)

    order = await repository.create_market_order(
        user_id=1,
        symbol="THYAO",
        side="BUY",
        quantity=10,
        idempotency_key="test-buy-next-tick",
        commission_rate=0.0015,
    )

    pending_account = await repository.get_account(1)
    assert order["status"] == "PENDING"
    assert pending_account["available_balance"] < before["available_balance"]
    assert pending_account["reserved_balance"] > 0

    completed = await repository.process_pending_orders(
        [{"asset_id": 1, "price": 320.0}], commission_rate=0.0015
    )
    filled = (await repository.list_orders(1))[0]
    context = await repository.get_order_context(1, "THYAO")

    assert completed == 1
    assert filled["status"] == "FILLED"
    assert filled["average_fill_price"] == 320.0
    assert context["holding_quantity"] == 1010
    assert (await repository.get_account(1))["reserved_balance"] == 0

    portfolio = InMemoryPortfolioRepository()
    holdings = await portfolio.get_holdings(1)
    thyao = next(item for item in holdings if item["symbol"] == "THYAO")
    transactions = await portfolio.get_transactions(1)
    assert thyao["quantity"] == 1010
    assert transactions[0]["transaction_type"] == "BUY"
    assert transactions[0]["quantity"] == 10


@pytest.mark.asyncio
async def test_idempotency_key_does_not_reserve_cash_twice(repository):
    first = await repository.create_market_order(1, "THYAO", "BUY", 5, "same-request-key", 0.0015)
    after_first = await repository.get_account(1)
    second = await repository.create_market_order(1, "THYAO", "BUY", 5, "same-request-key", 0.0015)
    after_second = await repository.get_account(1)

    assert second["id"] == first["id"]
    assert after_second == after_first


@pytest.mark.asyncio
async def test_cannot_sell_more_than_paper_position(repository):
    with pytest.raises(BusinessRuleError, match="satilabilir"):
        await repository.create_market_order(1, "ASELS", "SELL", 1, "sell-without-position", 0.0015)


@pytest.mark.asyncio
async def test_existing_portfolio_holding_can_be_sold(repository):
    await repository.create_market_order(
        1, "THYAO", "SELL", 25, "sell-main-portfolio-position", 0.0015
    )
    completed = await repository.process_pending_orders(
        [{"asset_id": 1, "price": 320.0}], commission_rate=0.0015
    )

    portfolio = InMemoryPortfolioRepository()
    thyao = next(item for item in await portfolio.get_holdings(1) if item["symbol"] == "THYAO")
    assert completed == 1
    assert thyao["quantity"] == 975


@pytest.mark.asyncio
async def test_index_cannot_be_traded(repository):
    with pytest.raises(BusinessRuleError, match="Endeksler"):
        await repository.create_market_order(1, "BIST100", "BUY", 1, "unsupported-index", 0.0015)


@pytest.mark.asyncio
async def test_foreign_currency_asset_is_converted_to_try(repository):
    context = await repository.get_order_context(1, "BTC")
    assert context["current_price"] == pytest.approx(65400 * 33.55)

    await repository.create_market_order(1, "BTC", "BUY", 0.001, "btc-buy", 0.0015)
    completed = await repository.process_pending_orders(
        [{"asset_id": 12, "price": 66000}], commission_rate=0.0015
    )
    filled = (await repository.list_orders(1))[0]

    assert completed == 1
    assert filled["status"] == "FILLED"
    assert filled["average_fill_price"] == pytest.approx(66000 * 33.55)
    assert (await repository.get_order_context(1, "BTC"))["holding_quantity"] == 0.501

    portfolio = InMemoryPortfolioRepository()
    btc = next(item for item in await portfolio.get_holdings(1) if item["symbol"] == "BTC")
    expected_average = (0.5 * 60000 + 0.001 * 66000) / 0.501
    assert btc["average_buy_price"] == pytest.approx(expected_average)


@pytest.mark.asyncio
async def test_foreign_currency_stop_loss_uses_asset_currency(repository):
    buy = await repository.create_market_order(
        1,
        "BTC",
        "BUY",
        0.001,
        "btc-buy-with-native-stop",
        0.0015,
        stop_loss_price=64000,
    )

    assert buy["stop_loss_currency"] == "USD"
    assert (
        await repository.process_pending_orders(
            [{"asset_id": 12, "price": 66000}], commission_rate=0.0015
        )
        == 1
    )

    stop = next(
        row for row in await repository.list_orders(1) if row.get("parent_order_id") == buy["id"]
    )
    assert stop["order_type"] == "STOP_MARKET"
    assert stop["stop_loss_price"] == 64000
    assert stop["stop_loss_currency"] == "USD"

    assert (
        await repository.process_pending_orders(
            [{"asset_id": 12, "price": 64500}], commission_rate=0.0015
        )
        == 0
    )
    assert (
        await repository.process_pending_orders(
            [{"asset_id": 12, "price": 63500}], commission_rate=0.0015
        )
        == 1
    )

    filled_stop = next(row for row in await repository.list_orders(1) if row["id"] == stop["id"])
    assert filled_stop["status"] == "FILLED"
    assert filled_stop["average_fill_price"] == pytest.approx(63500 * 33.55)


@pytest.mark.asyncio
async def test_limit_buy_waits_above_limit_then_fills_at_better_price(repository):
    order = await repository.create_market_order(
        1,
        "THYAO",
        "BUY",
        10,
        "limit-buy",
        0.0015,
        order_type="LIMIT",
        limit_price=310.0,
        validity="GTC",
    )
    pending_account = await repository.get_account(1)

    assert order["order_type"] == "LIMIT"
    assert order["limit_price"] == 310.0
    assert pending_account["reserved_balance"] == pytest.approx(3104.65)
    assert await repository.process_pending_orders([{"asset_id": 1, "price": 312.0}], 0.0015) == 0
    assert (await repository.list_orders(1))[0]["status"] == "PENDING"

    assert await repository.process_pending_orders([{"asset_id": 1, "price": 308.0}], 0.0015) == 1
    filled = (await repository.list_orders(1))[0]
    assert filled["status"] == "FILLED"
    assert filled["average_fill_price"] == 308.0
    assert (await repository.get_account(1))["reserved_balance"] == 0


@pytest.mark.asyncio
async def test_limit_sell_fills_only_at_or_above_limit(repository):
    await repository.create_market_order(
        1,
        "THYAO",
        "SELL",
        25,
        "limit-sell",
        0.0015,
        order_type="LIMIT",
        limit_price=325.0,
        validity="GTC",
    )
    assert await repository.process_pending_orders([{"asset_id": 1, "price": 324.0}], 0.0015) == 0
    assert await repository.process_pending_orders([{"asset_id": 1, "price": 326.0}], 0.0015) == 1


@pytest.mark.asyncio
async def test_cancel_limit_buy_releases_reserved_cash(repository):
    before = await repository.get_account(1)
    order = await repository.create_market_order(
        1,
        "THYAO",
        "BUY",
        10,
        "cancel-limit-buy",
        0.0015,
        order_type="LIMIT",
        limit_price=300.0,
        validity="GTC",
    )
    assert (await repository.get_account(1))["reserved_balance"] > 0

    cancelled = await repository.cancel_order(1, order["id"])
    after = await repository.get_account(1)
    assert cancelled["status"] == "CANCELLED"
    assert after["available_balance"] == pytest.approx(before["available_balance"])
    assert after["reserved_balance"] == pytest.approx(before["reserved_balance"])


@pytest.mark.asyncio
async def test_expired_day_order_is_cancelled_and_releases_cash_without_price(repository):
    before = await repository.get_account(1)
    order = await repository.create_market_order(
        1,
        "THYAO",
        "BUY",
        10,
        "expired-day-limit",
        0.0015,
        order_type="LIMIT",
        limit_price=300.0,
        validity="DAY",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert await repository.process_pending_orders([], 0.0015) == 0
    expired = next(row for row in await repository.list_orders(1) if row["id"] == order["id"])
    after = await repository.get_account(1)
    assert expired["status"] == "CANCELLED"
    assert after["available_balance"] == pytest.approx(before["available_balance"])
    assert after["reserved_balance"] == pytest.approx(before["reserved_balance"])


@pytest.mark.asyncio
async def test_attached_stop_is_created_after_buy_fill_and_triggers_below_stop(repository):
    buy = await repository.create_market_order(
        1,
        "THYAO",
        "BUY",
        10,
        "buy-with-stop",
        0.0015,
        stop_loss_price=290.0,
    )
    assert not any(
        row.get("parent_order_id") == buy["id"] for row in await repository.list_orders(1)
    )

    assert await repository.process_pending_orders([{"asset_id": 1, "price": 300.0}], 0.0015) == 1
    stop = next(
        row for row in await repository.list_orders(1) if row.get("parent_order_id") == buy["id"]
    )
    assert stop["order_type"] == "STOP_MARKET"
    assert stop["status"] == "PENDING"
    assert stop["quantity"] == 10

    assert await repository.process_pending_orders([{"asset_id": 1, "price": 291.0}], 0.0015) == 0
    assert await repository.process_pending_orders([{"asset_id": 1, "price": 289.0}], 0.0015) == 1
    filled_stop = next(row for row in await repository.list_orders(1) if row["id"] == stop["id"])
    assert filled_stop["status"] == "FILLED"
    assert filled_stop["average_fill_price"] == 289.0


@pytest.mark.asyncio
async def test_manual_partial_and_full_sell_reconcile_attached_stop(repository):
    buy = await repository.create_market_order(
        1,
        "THYAO",
        "BUY",
        10,
        "buy-stop-reconcile",
        0.0015,
        stop_loss_price=290.0,
    )
    await repository.process_pending_orders([{"asset_id": 1, "price": 300.0}], 0.0015)
    stop = next(
        row for row in await repository.list_orders(1) if row.get("parent_order_id") == buy["id"]
    )

    await repository.create_market_order(1, "THYAO", "SELL", 4, "manual-partial-sell", 0.0015)
    await repository.process_pending_orders([{"asset_id": 1, "price": 300.0}], 0.0015)
    reduced = next(row for row in await repository.list_orders(1) if row["id"] == stop["id"])
    assert reduced["status"] == "PENDING"
    assert reduced["quantity"] == 6

    await repository.create_market_order(
        1, "THYAO", "SELL", 6, "manual-full-protected-sell", 0.0015
    )
    await repository.process_pending_orders([{"asset_id": 1, "price": 300.0}], 0.0015)
    cancelled = next(row for row in await repository.list_orders(1) if row["id"] == stop["id"])
    assert cancelled["status"] == "CANCELLED"
