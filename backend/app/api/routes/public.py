"""Login gerektirmeyen public frontend endpointleri."""

from fastapi import APIRouter

from app.schemas.public import (
    PublicLandingPreviewResponse,
    PublicMarketTickerResponse,
)
from app.services.public_market import get_public_market_ticker
from app.services.public_preview import get_public_landing_preview

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/market-ticker", response_model=PublicMarketTickerResponse)
async def market_ticker() -> PublicMarketTickerResponse:
    """Landing sayfasinda gosterilecek public piyasa seridi."""
    return await get_public_market_ticker()


@router.get("/landing-preview", response_model=PublicLandingPreviewResponse)
async def landing_preview() -> PublicLandingPreviewResponse:
    """Login oncesi landing modalinda gosterilecek demo portfoy ozeti."""
    return await get_public_landing_preview()
