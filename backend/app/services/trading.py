"""Sanal bakiye ile piyasa emri olusturma ve gerceklestirme servisi."""

from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.quantity import adet_gecerli_mi, gecersiz_adet_mesaji
from app.repositories.deps import get_trading_repository
from app.schemas.trading import (
    OrderPreview,
    OrdersResponse,
    PaperOrder,
    TradingAccount,
)

COMMISSION_RATE = 0.0015


async def hesap_getir(user_id: int) -> TradingAccount:
    row = await get_trading_repository().get_account(user_id)
    if row is None:
        raise NotFoundError("Paper trading hesabi bulunamadi.")
    return TradingAccount(
        portfolio_id=int(row["portfolio_id"]),
        portfolio_name=row["portfolio_name"],
        currency=row["currency"],
        available_balance=_f(row["available_balance"]),
        reserved_balance=_f(row["reserved_balance"]),
    )


async def emir_onizle(
    user_id: int,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "MARKET",
    limit_price: float | None = None,
    validity: str = "GTC",
    stop_loss_price: float | None = None,
) -> OrderPreview:
    row = await get_trading_repository().get_order_context(user_id, symbol)
    if row is None:
        raise NotFoundError(f"'{symbol.upper()}' hissesi bulunamadi.")
    _context_validate(row, side, quantity, order_type, limit_price, validity, stop_loss_price)

    price = float(row["current_price"])
    calculation_price = float(limit_price) if order_type == "LIMIT" else price
    gross = calculation_price * quantity
    commission = gross * COMMISSION_RATE
    total = gross + commission if side == "BUY" else gross - commission
    reserve = (
        gross + commission
        if side == "BUY" and order_type == "LIMIT"
        else gross * 1.02 + commission if side == "BUY" else 0
    )
    available = float(row["available_balance"])
    holding = float(row.get("holding_quantity") or 0)
    pending_sell = float(row.get("pending_sell_quantity") or 0)

    if side == "BUY" and available < reserve:
        raise BusinessRuleError(
            "Fiyat tamponu dahil bu alim emri icin kullanilabilir sanal bakiye yetersiz."
        )
    if side == "SELL" and holding - pending_sell < quantity:
        raise BusinessRuleError("Bekleyen emirler dusuldugunde satilabilir hisse adedi yetersiz.")

    return OrderPreview(
        symbol=row["symbol"],
        asset_name=row["asset_name"],
        side=side,
        quantity=_q(quantity),
        order_type=order_type,
        limit_price=None if limit_price is None else _f(limit_price),
        stop_loss_price=None if stop_loss_price is None else _q(stop_loss_price),
        stop_loss_currency=None if stop_loss_price is None else row["currency"],
        validity="GTC" if order_type == "MARKET" else validity,
        expires_at=_iso(_expires_at(order_type, validity)),
        quoted_price=_f(price),
        gross_amount=_f(gross),
        estimated_commission=_f(commission),
        estimated_total=_f(total),
        estimated_reserve=_f(reserve),
        available_balance=_f(available),
        holding_quantity=_q(holding),
        price_updated_at=_iso(row.get("price_updated_at")),
        execution_note=(
            "Limit koşulu sağlandığında emir, doğrulanmış güncel fiyatla gerçekleşir."
            if order_type == "LIMIT"
            else "Emir, alınacak bir sonraki doğrulanmış fiyatla gerçekleşir."
        ),
    )


async def emir_olustur(
    user_id: int,
    symbol: str,
    side: str,
    quantity: float,
    idempotency_key: str,
    order_type: str = "MARKET",
    limit_price: float | None = None,
    validity: str = "GTC",
    stop_loss_price: float | None = None,
) -> PaperOrder:
    if side not in {"BUY", "SELL"}:
        raise BusinessRuleError("Islem yonu BUY veya SELL olmalidir.")
    row = await get_trading_repository().create_market_order(
        user_id=user_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        idempotency_key=idempotency_key,
        commission_rate=COMMISSION_RATE,
        order_type=order_type,
        limit_price=limit_price,
        validity="GTC" if order_type == "MARKET" else validity,
        expires_at=_expires_at(order_type, validity),
        stop_loss_price=stop_loss_price,
    )
    return _order(row)


async def emirleri_getir(user_id: int, limit: int = 20) -> OrdersResponse:
    rows = await get_trading_repository().list_orders(user_id, limit)
    return OrdersResponse(items=[_order(row) for row in rows], limit=limit)


async def emir_iptal(user_id: int, order_id: int) -> PaperOrder:
    return _order(await get_trading_repository().cancel_order(user_id, order_id))


async def bekleyen_emirleri_isle(updates: list[dict]) -> int:
    """Yalnizca bu tick'te dogrulanmis fiyat gelen varliklari gerceklestirir."""
    return await get_trading_repository().process_pending_orders(updates, COMMISSION_RATE)


def _context_validate(
    row: dict,
    side: str,
    quantity: float,
    order_type: str,
    limit_price: float | None,
    validity: str,
    stop_loss_price: float | None,
) -> None:
    if side not in {"BUY", "SELL"}:
        raise BusinessRuleError("Islem yonu BUY veya SELL olmalidir.")
    if quantity <= 0:
        raise BusinessRuleError("Emir adedi sifirdan buyuk olmalidir.")
    # Hisse ve ETF bolunmez: 1,18 adet INTC diye bir sey yok. Kontrol
    # ARAYUZDE DEGIL burada: istemci dogrulamasi atlanabilir.
    if not adet_gecerli_mi(quantity, row.get("asset_class")):
        raise BusinessRuleError(gecersiz_adet_mesaji(row.get("asset_class")))
    if row["asset_class"] == "INDEX":
        raise BusinessRuleError("Endeksler dogrudan alinip satilamaz.")
    if float(row["current_price"] or 0) <= 0:
        raise BusinessRuleError("Hisse icin gecerli bir fiyat bulunamadi.")
    if order_type not in {"MARKET", "LIMIT"}:
        raise BusinessRuleError("Emir tipi MARKET veya LIMIT olmalidir.")
    if order_type == "LIMIT" and (limit_price is None or limit_price <= 0):
        raise BusinessRuleError("Limit fiyati sifirdan buyuk olmalidir.")
    if validity not in {"DAY", "GTC"}:
        raise BusinessRuleError("Gecerlilik DAY veya GTC olmalidir.")
    if stop_loss_price is not None:
        if side != "BUY":
            raise BusinessRuleError("Stop-loss yalnizca alim emrine eklenebilir.")
        fx_rate = float(row.get("fx_rate") or 1)
        reference = (
            float(limit_price) / fx_rate
            if order_type == "LIMIT"
            else float(row.get("native_price") or row["current_price"])
        )
        if stop_loss_price <= 0 or stop_loss_price >= reference:
            raise BusinessRuleError("Stop-loss fiyati alim referans fiyatindan dusuk olmalidir.")


def _order(row: dict) -> PaperOrder:
    return PaperOrder(
        id=int(row["id"]),
        symbol=row["symbol"],
        asset_name=row["asset_name"],
        side=row["side"],
        order_type=row.get("order_type") or "MARKET",
        limit_price=None if row.get("limit_price") is None else _f(row["limit_price"]),
        stop_loss_price=(
            None if row.get("stop_loss_price") is None else _q(row["stop_loss_price"])
        ),
        stop_loss_currency=row.get("stop_loss_currency"),
        parent_order_id=(
            None if row.get("parent_order_id") is None else int(row["parent_order_id"])
        ),
        validity=row.get("validity") or "GTC",
        expires_at=_iso(row.get("expires_at")),
        quantity=_q(row["quantity"]),
        quoted_price=_f(row["quoted_price"]),
        status=row["status"],
        filled_quantity=_q(row.get("filled_quantity")),
        average_fill_price=(
            None if row.get("average_fill_price") is None else _f(row["average_fill_price"])
        ),
        commission=_f(row.get("commission")),
        rejection_reason=row.get("rejection_reason"),
        created_at=_iso(row["created_at"]) or "",
        filled_at=_iso(row.get("filled_at")),
    )


def _expires_at(order_type: str, validity: str) -> datetime | None:
    if order_type != "LIMIT" or validity != "DAY":
        return None
    istanbul = ZoneInfo("Europe/Istanbul")
    local_now = datetime.now(istanbul)
    return datetime.combine(local_now.date(), time.max, tzinfo=istanbul).astimezone(timezone.utc)


def _f(value) -> float:
    return round(float(value or 0), 2)


def _q(value) -> float:
    return round(float(value or 0), 6)


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
