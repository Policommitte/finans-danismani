"""Login gerektirmeyen public frontend endpointleri."""

from fastapi import APIRouter

from app.schemas.public import (
    PublicLandingAllocationItem,
    PublicLandingHoldingItem,
    PublicLandingPreviewResponse,
    PublicMarketTickerResponse,
)
from app.services import portfolio as portfolio_service
from app.services.public_market import get_public_market_ticker

router = APIRouter(prefix="/api/public", tags=["public"])
DEMO_USER_ID = 1


@router.get("/market-ticker", response_model=PublicMarketTickerResponse)
async def market_ticker() -> PublicMarketTickerResponse:
    """Landing sayfasinda gosterilecek public piyasa seridi."""
    return await get_public_market_ticker()


@router.get("/landing-preview", response_model=PublicLandingPreviewResponse)
async def landing_preview() -> PublicLandingPreviewResponse:
    """Login oncesi landing modalinda gosterilecek demo portfoy ozeti."""
    summary = await portfolio_service.ozet_getir(DEMO_USER_ID)
    allocation = await portfolio_service.dagilim_getir(DEMO_USER_ID)
    holdings = await portfolio_service.varliklar_getir(DEMO_USER_ID)

    return PublicLandingPreviewResponse(
        total_value_try=summary.total_value_try,
        total_pnl_pct=summary.total_pnl_pct,
        holding_count=summary.holding_count,
        allocation=[
            PublicLandingAllocationItem(
                asset_class=item.asset_class,
                class_value_try=item.class_value_try,
                class_pct=item.class_pct,
            )
            for item in allocation.items
        ],
        holdings=[
            PublicLandingHoldingItem(
                symbol=item.symbol,
                asset_name=item.asset_name,
                asset_class=item.asset_class,
                current_price=item.current_price,
                daily_change_pct=item.daily_change_pct,
                market_value_try=item.market_value_try,
                pnl_pct=item.pnl_pct,
            )
            for item in holdings.items
        ],
    )

