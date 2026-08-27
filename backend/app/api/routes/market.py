"""Piyasa uclari - varlik listesi, fiyat grafigi, RAG destekli arama."""

from typing import Literal

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.schemas.market import (
    AssetsResponse,
    CandlesResponse,
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


#: `borsa-verisi/` betigi Yahoo'dan varsayilan olarak 2 yillik gecmis ceker
#: (`period=2y`); ust sinir bununla eslesir. Daha genis bir gecmis yuklenirse
#: bu deger DE guncellenmelidir - aksi halde veri veritabaninda durur ama
#: frontend'e hic ulasmaz.
MAX_HISTORY_GUN = 730


@router.get("/history", response_model=HistoryResponse)
async def history(
    user: CurrentUser,
    symbol: str = Query(description="Varlik kodu (orn. THYAO)"),
    days: int = Query(default=30, ge=1, le=MAX_HISTORY_GUN),
) -> HistoryResponse:
    """PriceChart icin ham fiyat serisi.

    Gunluk/haftalik gorunum icin varsayilan 30 gun yeterlidir; frontend
    yillik gorunum icin `days=365` veya `days=730` gonderebilir.
    """
    return await service.gecmis_getir(symbol, days=days)


@router.get("/candles", response_model=CandlesResponse)
async def candles(
    user: CurrentUser,
    symbol: str = Query(description="Varlik kodu (orn. THYAO)"),
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = "15m",
    range_key: Literal["1d", "5d", "1m", "3m", "1y"] = Query("1m", alias="range"),
) -> CandlesResponse:
    """Trading grafigi icin zaman kovalarina ayrilmis OHLC mumlari."""
    return await service.mumlar_getir(symbol, interval=interval, range_key=range_key)


@router.post("/search", response_model=MarketSearchResponse)
async def search(user: CurrentUser, payload: MarketSearchRequest) -> MarketSearchResponse:
    """Haber/bilanco/rapor aramasi.

    GET degil POST: sorgu metni uzun olabilir ve URL'de loglanmasi istenmez.
    Ajan devreye GIRMEZ; dogrudan RAG indeksinde arama yapilir.
    """
    return await service.arama_yap(
        query=payload.query, top_k=payload.top_k, sirket=payload.sirket, tip=payload.tip
    )
