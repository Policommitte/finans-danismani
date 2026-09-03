"""Paper trading hesap ve emir uclari."""

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.schemas.trading import (
    CreateOrderRequest,
    OrderPreview,
    OrderPreviewRequest,
    OrdersResponse,
    PaperOrder,
    PercentageBasketPreview,
    PercentageBasketPreviewRequest,
    TradingAccount,
)
from app.services import trading as service

router = APIRouter(prefix="/api/trading", tags=["trading"])


@router.get("/account", response_model=TradingAccount)
async def account(user: CurrentUser) -> TradingAccount:
    return await service.hesap_getir(user["id"])


@router.post("/orders/preview", response_model=OrderPreview)
async def preview(user: CurrentUser, payload: OrderPreviewRequest) -> OrderPreview:
    return await service.emir_onizle(
        user["id"],
        payload.symbol,
        payload.side,
        payload.quantity,
        payload.order_type,
        payload.limit_price,
        payload.validity,
        payload.stop_loss_price,
    )


@router.post("/orders", response_model=PaperOrder, status_code=201)
async def create_order(user: CurrentUser, payload: CreateOrderRequest) -> PaperOrder:
    return await service.emir_olustur(
        user["id"],
        payload.symbol,
        payload.side,
        payload.quantity,
        payload.idempotency_key,
        payload.order_type,
        payload.limit_price,
        payload.validity,
        payload.stop_loss_price,
    )


@router.post("/basket/preview", response_model=PercentageBasketPreview)
async def preview_percentage_basket(
    user: CurrentUser,
    payload: PercentageBasketPreviewRequest,
) -> PercentageBasketPreview:
    return await service.yuzdesel_sepet_onizle(user["id"], payload.allocations)


@router.get("/orders", response_model=OrdersResponse)
async def orders(
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> OrdersResponse:
    return await service.emirleri_getir(user["id"], limit)


@router.post("/orders/{order_id}/cancel", response_model=PaperOrder)
async def cancel_order(order_id: int, user: CurrentUser) -> PaperOrder:
    return await service.emir_iptal(user["id"], order_id)
