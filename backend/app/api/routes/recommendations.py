"""Otonom oneri uclari (AUT / UC-08).

Emir OLUSTURMA burada yapilmaz; onay `services/trading.py`ye devredilir.
Boylece manuel ve otonom akis AYNI limit, bakiye ve idempotency kontrollerinden
gecer - iki farkli emir yolu iki farkli davranis demek olurdu.
"""

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.repositories.deps import get_recommendation_repository
from app.schemas.idle_cash import (
    IdleCashBasketCatalog,
    IdleCashSuggestion,
    IdleCashSuggestionRequest,
)
from app.schemas.recommendation import (
    ApproveRequest,
    AutonomousSettings,
    Recommendation,
    RecommendationListResponse,
    RejectRequest,
)
from app.services import recommendation as service
from app.services.idle_cash import (
    idle_cash_basket_catalog_for_goal,
    idle_cash_suggestion_for_goal,
)

router = APIRouter(prefix="/api/oneriler", tags=["oneriler"])


@router.get("", response_model=RecommendationListResponse)
async def listele(
    user: CurrentUser,
    durum: str | None = Query(
        default=None,
        description="PUBLISHED | VIEWED | APPROVED | CONVERTED | REJECTED | EXPIRED | HALTED",
    ),
) -> RecommendationListResponse:
    """FR-AUT-011: otonom eylemler ekrani. `counts` sekme rozetlerini besler."""
    return await service.onerileri_getir(user["id"], durum)


@router.get("/ayarlar", response_model=AutonomousSettings)
async def ayarlari_getir(user: CurrentUser) -> AutonomousSettings:
    """FR-PRF-014 + FR-AUT-026: limitler ve otonom akisin acik/kapali olmasi."""
    return AutonomousSettings(**await get_recommendation_repository().get_limits(user["id"]))


@router.put("/ayarlar", response_model=AutonomousSettings)
async def ayarlari_guncelle(user: CurrentUser, payload: AutonomousSettings) -> AutonomousSettings:
    row = await get_recommendation_repository().upsert_limits(user["id"], payload.model_dump())
    return AutonomousSettings(**row)


@router.post("/sepet", response_model=IdleCashSuggestion)
async def sepet_onerisi(
    user: CurrentUser, payload: IdleCashSuggestionRequest
) -> IdleCashSuggestion:
    """Atıl bakiye için risk profiline ve seçilen hedefe göre kurallı sepet."""
    return await idle_cash_suggestion_for_goal(user["id"], payload.goal)


@router.post("/sepetler", response_model=IdleCashBasketCatalog)
async def sepet_alternatifleri(
    user: CurrentUser, payload: IdleCashSuggestionRequest
) -> IdleCashBasketCatalog:
    """Seçilen hedef için atıl bakiyeye uygun farklı sepet alternatifleri."""
    return await idle_cash_basket_catalog_for_goal(user["id"], payload.goal)


@router.get("/{oneri_id}", response_model=Recommendation)
async def getir(user: CurrentUser, oneri_id: int) -> Recommendation:
    """Kart acilinca durum Goruntulendi'ye gecer (D-07)."""
    return await service.oneri_getir(user["id"], oneri_id)


@router.post("/{oneri_id}/ret", response_model=Recommendation)
async def reddet(user: CurrentUser, oneri_id: int, payload: RejectRequest) -> Recommendation:
    """FR-AUT-023: gerekceli ret. Reddedilen oneri de denetime yazilir."""
    return await service.oneri_reddet(user["id"], oneri_id, payload.reason)


@router.post("/{oneri_id}/onayla")
async def onayla(user: CurrentUser, oneri_id: int, payload: ApproveRequest) -> dict:
    """Onay -> emir (BR-AUT-08: bir oneri en fazla bir emir dogurur).

    FR-AUT-014: kullanici onerilen adedi degistirebilir; limit ve bakiye
    kontrolu trading servisinde YENIDEN yapilir.
    """
    return await service.oneri_onayla(user["id"], oneri_id, payload.quantity)
