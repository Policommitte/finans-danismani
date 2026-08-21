"""Portfoy ekrani domain servisi.

Katman kurali: `routes -> services -> repositories`. Endpoint'ler repository'yi
dogrudan cagirmaz; boylece veri kaynagi degistiginde (bellek ici -> Postgres)
ve alan adlari duzeltildiginde tek dokunulan yer burasidir.

Servis HESAP YAPMAZ: toplamlar ve yuzdeler DB view'larindan gelir (mimari v4
bolum 9.2). Burada yalnizca sozlesmeye (schemas/portfolio.py) uygun bicime
cevirme yapilir.
"""

from __future__ import annotations

import asyncio

from app.core.errors import NotFoundError
from app.repositories.deps import get_portfolio_repository
from app.schemas.portfolio import (
    AllocationResponse,
    AllocationSlice,
    Holding,
    HoldingsResponse,
    PortfolioPerformancePoint,
    PortfolioPerformanceResponse,
    PortfolioSummary,
    Transaction,
    TransactionsResponse,
)


async def ozet_getir(user_id: int, portfolio_id: int | None = None) -> PortfolioSummary:
    repository = get_portfolio_repository()
    summary, holdings = await asyncio.gather(
        repository.get_summary(user_id, portfolio_id),
        repository.get_holdings(user_id, portfolio_id),
    )
    if summary is None:
        raise NotFoundError("Portfoy ozeti bulunamadi.")

    daily_change_try = sum(float(row.get("daily_change_try") or 0) for row in holdings)
    previous_total = float(summary["total_value_try"]) - daily_change_try

    return PortfolioSummary(
        portfolio_id=summary.get("portfolio_id"),
        holding_count=int(summary["holding_count"]),
        total_value_try=_f(summary["total_value_try"]),
        total_cost_try=_f(summary["total_cost_try"]),
        total_pnl_try=_f(summary["total_pnl_try"]),
        total_pnl_pct=_f_opt(summary.get("total_pnl_pct")),
        daily_change_try=_f(daily_change_try),
        daily_change_pct=(
            round(daily_change_try / previous_total * 100, 2) if previous_total > 0 else None
        ),
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


async def performans_getir(
    user_id: int, portfolio_id: int | None = None, hours: int = 24
) -> PortfolioPerformanceResponse:
    rows = await get_portfolio_repository().get_performance_history(
        user_id, portfolio_id, hours=hours
    )
    temiz_satirlar: list[dict] = []
    for row in rows:
        value = float(row["total_value_try"] or 0)
        if temiz_satirlar:
            previous = float(temiz_satirlar[-1]["total_value_try"] or 0)
            if previous > 0 and abs(value / previous - 1) > 0.05:
                # Eski seed fiyatindan ilk gercek piyasa fiyatina gecis,
                # kullanici performansi degildir; yeni canli baz buradan baslar.
                temiz_satirlar = []
        temiz_satirlar.append(row)

    benchmark_start = next(
        (
            row
            for row in temiz_satirlar
            if row.get("bist100_price") is not None and float(row["bist100_price"]) > 0
        ),
        None,
    )
    benchmark_baseline = (
        float(benchmark_start["bist100_price"]) if benchmark_start is not None else None
    )
    portfolio_baseline = (
        _f(benchmark_start["total_value_try"]) if benchmark_start is not None else 0
    )

    return PortfolioPerformanceResponse(
        points=[
            PortfolioPerformancePoint(
                ts=_iso_timestamp(row["ts"]),
                total_value_try=_f(row["total_value_try"]),
                bist100_value_try=(
                    round(portfolio_baseline * float(row["bist100_price"]) / benchmark_baseline, 2)
                    if benchmark_baseline
                    and row.get("bist100_price") is not None
                    and float(row["bist100_price"]) > 0
                    else None
                ),
            )
            for row in temiz_satirlar
        ],
        hours=hours,
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
        daily_change_try=_f(row.get("daily_change_try")),
        daily_change_pct_try=_f_opt(row.get("daily_change_pct_try")),
        market_value_try=_f(row["market_value_try"]),
        cost_basis_try=_f(row["cost_basis_try"]),
        pnl_try=_f(row["pnl_try"]),
        pnl_pct=_f_opt(row.get("pnl_pct")),
    )


def _f(value) -> float:
    """psycopg NUMERIC kolonlari `Decimal` doner; JSON'a cevrilmeden float'a alinir."""
    return round(float(value or 0), 2)


def _iso_timestamp(value) -> str:
    """DB datetime degerini tarayicilarin guvenle okuyacagi ISO bicimine getirir."""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _f_opt(value) -> float | None:
    return None if value is None else round(float(value), 2)
