"""Piyasa uclari - varlik listesi, fiyat grafigi, RAG destekli arama."""

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.schemas.market import (
    AssetsResponse,
    HistoryResponse,
    MarketSearchRequest,
    MarketSearchResponse,
)
from app.services import market as service

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/assets", response_model=AssetsResponse)
async def assets(
    user: CurrentUser,
    category: str | None = Query(default=None, description="STOCK | GOLD | CRYPTO | ..."),
) -> AssetsResponse:
    """Takip edilen varliklar ve guncel fiyatlari."""
    return await service.varliklar_getir(category)


@router.get("/history", response_model=HistoryResponse)
async def history(
    user: CurrentUser,
    symbol: str = Query(description="Varlik kodu (orn. THYAO)"),
    days: int = Query(default=30, ge=1, le=365),
) -> HistoryResponse:
    """PriceChart icin ham fiyat serisi."""
    return await service.gecmis_getir(symbol, days=days)


@router.post("/search", response_model=MarketSearchResponse)
async def search(user: CurrentUser, payload: MarketSearchRequest) -> MarketSearchResponse:
    """Haber/bilanco/rapor aramasi.

    GET degil POST: sorgu metni uzun olabilir ve URL'de loglanmasi istenmez.
    Ajan devreye GIRMEZ; dogrudan RAG indeksinde arama yapilir.
    """
    return await service.arama_yap(
        query=payload.query, top_k=payload.top_k, sirket=payload.sirket, tip=payload.tip
    )
