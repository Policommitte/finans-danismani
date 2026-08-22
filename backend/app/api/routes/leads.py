"""Lead motoru uclari - BSD kuyrugu, otonom kuyruk, dislananlar, tarama tetikleme."""

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.schemas.leads import LeadQueueResponse, LeadScanRequest, LeadScanSummary
from app.services import leads as service

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("/bsd-queue", response_model=LeadQueueResponse)
async def bsd_queue(
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500, description="Kac kayit donsun"),
) -> LeadQueueResponse:
    """BSD (insan danisman) kuyrugu - aranacak kisiler, skor sirali."""
    return await service.bsd_kuyrugu_getir(limit=limit)


@router.get("/autonomous-queue", response_model=LeadQueueResponse)
async def autonomous_queue(
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500, description="Kac kayit donsun"),
) -> LeadQueueResponse:
    """Otonom (mail gonderilen) kuyruk."""
    return await service.otonom_kuyruk_getir(limit=limit)


@router.get("/excluded", response_model=LeadQueueResponse)
async def excluded(
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500, description="Kac kayit donsun"),
) -> LeadQueueResponse:
    """Dislanan kullanicilar ve gerekceleri."""
    return await service.dislananlar_getir(limit=limit)


@router.post("/scan", response_model=LeadScanSummary)
async def scan(user: CurrentUser, payload: LeadScanRequest) -> LeadScanSummary:
    """Lead taramasini elle tetikler.

    Asgari aralik nedeniyle atlanirsa hata DEGIL, `skipped=True` doner.
    """
    return await service.tarama_calistir(trigger="manual", force=payload.force)
