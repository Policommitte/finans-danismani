"""Login gerektirmeyen public frontend endpointleri."""

from fastapi import APIRouter

from app.schemas.public import PublicMarketTickerResponse
from app.services.public_market import get_public_market_ticker

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/market-ticker", response_model=PublicMarketTickerResponse)
async def market_ticker() -> PublicMarketTickerResponse:
    """Landing sayfasinda gosterilecek public piyasa seridi."""
    return await get_public_market_ticker()

