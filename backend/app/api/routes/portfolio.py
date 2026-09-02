"""Portfoy uclari - SummaryCards, HoldingsTable, AllocationPie, islem gecmisi."""

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.schemas.portfolio import (
    AllocationResponse,
    HoldingsResponse,
    PortfolioPerformanceResponse,
    PortfolioSnapshotPerformanceResponse,
    PortfolioSummary,
    TransactionsResponse,
)
from app.services import portfolio as service

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
async def summary(user: CurrentUser) -> PortfolioSummary:
    """Toplam deger, maliyet ve kar/zarar."""
    return await service.ozet_getir(user["id"])


@router.get("/holdings", response_model=HoldingsResponse)
async def holdings(user: CurrentUser) -> HoldingsResponse:
    """Portfoydeki varliklar (deger sirali)."""
    return await service.varliklar_getir(user["id"])


@router.get("/allocation", response_model=AllocationResponse)
async def allocation(user: CurrentUser) -> AllocationResponse:
    """Varlik sinifi bazinda dagilim."""
    return await service.dagilim_getir(user["id"])


@router.get("/transactions", response_model=TransactionsResponse)
async def transactions(
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100, description="Kac islem donsun"),
) -> TransactionsResponse:
    """Son alim/satim islemleri."""
    return await service.islemler_getir(user["id"], limit=limit)


@router.get("/performance", response_model=PortfolioPerformanceResponse)
async def performance(
    user: CurrentUser,
    hours: int = Query(default=24, ge=1, le=168, description="Kac saatlik performans donsun"),
) -> PortfolioPerformanceResponse:
    """Mevcut portfoyun gercek fiyat gecmisiyle TL bazli performansi."""
    return await service.performans_getir(user["id"], hours=hours)


@router.get("/performance-v2", response_model=PortfolioSnapshotPerformanceResponse)
async def snapshot_performance(
    user: CurrentUser,
    hours: int = Query(default=24, ge=1, le=720, description="Kac saatlik snapshot donsun"),
) -> PortfolioSnapshotPerformanceResponse:
    """Basarili fiyat turlarindan sonra kaydedilen portfoy toplamlarini dondurur."""
    return await service.snapshot_performansi_getir(user["id"], hours=hours)
