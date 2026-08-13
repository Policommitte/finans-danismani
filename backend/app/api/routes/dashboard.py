"""Dashboard birlesik ozet ucu."""

from fastapi import APIRouter

from app.auth.deps import CurrentUser
from app.schemas.dashboard import DashboardSummaryResponse
from app.services import dashboard as service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def summary(user: CurrentUser) -> DashboardSummaryResponse:
    """Dashboard ILK yuklemesi: portfoy + dagilim + risk + hareketliler.

    Sekmeler ve tazeleme granuler uclari kullanir; bu uc yalnizca ilk acilisin
    4 istegini 1'e indirmek icindir.
    """
    return await service.ozet_getir(user["id"])
