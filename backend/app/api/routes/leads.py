"""Lead motoru uclari - BSD kuyrugu, otonom kuyruk, dislananlar, tarama tetikleme."""

from fastapi import APIRouter, Path, Query, Response, status

from app.auth.deps import CurrentAdvisor
from app.schemas.leads import (
    LeadOutcomeRequest,
    LeadQueueResponse,
    LeadScanRequest,
    LeadScanSummary,
)
from app.services import leads as service

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("/bsd-queue", response_model=LeadQueueResponse)
async def bsd_queue(
    user: CurrentAdvisor,
    limit: int = Query(default=100, ge=1, le=500, description="Kac kayit donsun"),
) -> LeadQueueResponse:
    """BSD (insan danisman) kuyrugu - aranacak kisiler, skor sirali."""
    return await service.bsd_kuyrugu_getir(limit=limit)


@router.get("/autonomous-queue", response_model=LeadQueueResponse)
async def autonomous_queue(
    user: CurrentAdvisor,
    limit: int = Query(default=100, ge=1, le=500, description="Kac kayit donsun"),
) -> LeadQueueResponse:
    """Otonom (mail gonderilen) kuyruk."""
    return await service.otonom_kuyruk_getir(limit=limit)


@router.get("/excluded", response_model=LeadQueueResponse)
async def excluded(
    user: CurrentAdvisor,
    limit: int = Query(default=100, ge=1, le=500, description="Kac kayit donsun"),
) -> LeadQueueResponse:
    """Dislanan kullanicilar ve gerekceleri."""
    return await service.dislananlar_getir(limit=limit)


@router.post("/scan", response_model=LeadScanSummary)
async def scan(user: CurrentAdvisor, payload: LeadScanRequest) -> LeadScanSummary:
    """Lead taramasini elle tetikler.

    Asgari aralik nedeniyle atlanirsa hata DEGIL, `skipped=True` doner.
    """
    return await service.tarama_calistir(trigger="manual", force=payload.force)


@router.post("/{user_id}/outcome", status_code=status.HTTP_204_NO_CONTENT)
async def record_outcome(
    user: CurrentAdvisor,
    payload: LeadOutcomeRequest,
    user_id: int = Path(description="Sonucu isaretlenen musterinin id'si"),
) -> Response:
    """Danismanin telefon gorusmesi sonucunu isaretler.

    Ekleme-only: her cagri yeni bir satirdir, en son satir gecerlidir.
    `outcome='ACIK'` gonderilirse isaretleme temizlenir (satir silinmez).

    `KABUL` ve `ISTEMIYOR` bir sonraki taramada kullaniciyi kuyruk disi
    birakir (`advisor_closed`); `ULASILAMADI` birakmaz - tekrar aranmali.
    """
    await service.gorusme_sonucu_kaydet(
        user_id=user_id,
        advisor_id=user.get("id"),
        outcome=payload.outcome,
        note=payload.note,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
