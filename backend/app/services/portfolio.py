"""Portfoy ekrani domain servisi.

Katman kurali: `routes -> services -> repositories`. Endpoint'ler repository'yi
dogrudan cagirmaz; boylece veri kaynagi degistiginde (bellek ici -> Postgres)
ve alan adlari duzeltildiginde tek dokunulan yer burasidir.

Servis HESAP YAPMAZ: toplamlar ve yuzdeler DB view'larindan gelir (mimari v4
bolum 9.2). Burada yalnizca sozlesmeye (schemas/portfolio.py) uygun bicime
cevirme yapilir.
"""

from __future__ import annotations

from app.core.errors import NotFoundError
from app.repositories.deps import get_portfolio_repository
from app.schemas.portfolio import (
    AllocationResponse,
    AllocationSlice,
    Holding,
    HoldingsResponse,
    PortfolioSummary,
    Transaction,
    TransactionsResponse,
)


async def ozet_getir(user_id: int, portfolio_id: int | None = None) -> PortfolioSummary:
    summary = await get_portfolio_repository().get_summary(user_id, portfolio_id)
    if summary is None:
        raise NotFoundError("Portfoy ozeti bulunamadi.")

    return PortfolioSummary(
        portfolio_id=summary.get("portfolio_id"),
        holding_count=int(summary["holding_count"]),
        total_value_try=_f(summary["total_value_try"]),
        total_cost_try=_f(summary["total_cost_try"]),
        total_pnl_try=_f(summary["total_pnl_try"]),
        total_pnl_pct=_f_opt(summary.get("total_pnl_pct")),
    )


async def varliklar_getir(user_id: int, portfolio_id: int | None = None) -> HoldingsResponse:
    rows = await get_portfolio_repository().get_holdings(user_id, portfolio_id)
    items = [_holding(row) for row in rows]

    return HoldingsResponse(
        items=items,
        total_value_try=round(sum(item.market_value_try for item in items), 2),
    )


async def dagilim_getir(user_id: int, portfolio_id: int | None = None) -> AllocationResponse:
    rows = await get_portfolio_repository().get_allocation(user_id, portfolio_id)
    return AllocationResponse(
        items=[
            AllocationSlice(
                asset_class=row["asset_class"],
                class_value_try=_f(row["class_value"]),
                class_pct=_f(row["class_pct"]),
            )
            for row in rows
        ]
    )


async def islemler_getir(
    user_id: int, portfolio_id: int | None = None, limit: int = 20
) -> TransactionsResponse:
    rows = await get_portfolio_repository().get_transactions(user_id, portfolio_id, limit=limit)
    return TransactionsResponse(
        items=[
            Transaction(
                id=int(row["id"]),
                symbol=row["symbol"],
                asset_name=row["asset_name"],
                transaction_type=row["transaction_type"],
                quantity=_f(row["quantity"]),
                unit_price=_f(row["unit_price"]),
                transaction_date=str(row["transaction_date"]),
            )
            for row in rows
        ],
        limit=limit,
    )


def _holding(row: dict) -> Holding:
    return Holding(
        symbol=row["symbol"],
        asset_name=row["asset_name"],
        asset_class=row["asset_class"],
        currency=row["currency"],
        quantity=_f(row["quantity"]),
        average_buy_price=_f(row["average_buy_price"]),
        current_price=_f(row["current_price"]),
        daily_change_pct=_f_opt(row.get("daily_change_pct")),
        market_value_try=_f(row["market_value_try"]),
        cost_basis_try=_f(row["cost_basis_try"]),
        pnl_try=_f(row["pnl_try"]),
        pnl_pct=_f_opt(row.get("pnl_pct")),
    )


def _f(value) -> float:
    """psycopg NUMERIC kolonlari `Decimal` doner; JSON'a cevrilmeden float'a alinir."""
    return round(float(value or 0), 2)


def _f_opt(value) -> float | None:
    return None if value is None else round(float(value), 2)
