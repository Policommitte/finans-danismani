"""Piyasa uclari - varlik listesi, fiyat grafigi, RAG destekli arama."""

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.schemas.market import (
    AssetsResponse,
    HistoryResponse,
    MarketSearchRequest,
    MarketSearchResponse,
    NewsListResponse,
    OhlcResponse,
)
from app.services import market as service
from app.services import news as news_service

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


@router.get("/ohlc", response_model=OhlcResponse)
async def ohlc(
    user: CurrentUser,
    symbol: str = Query(description="Varlik kodu (orn. GARAN)"),
    days: int = Query(default=30, ge=1, le=MAX_HISTORY_GUN),
) -> OhlcResponse:
    """Mum grafik icin GERCEK gunluk OHLC serisi - Yahoo'dan canli cekilir.

    Sadece dogrudan bir Yahoo ticker'i olan semboller desteklenir; digerleri
    icin bos `candles` doner (404 DEGIL - frontend cizgi grafige duser).
    """
    return await service.ohlc_getir(symbol, days=days)


@router.post("/search", response_model=MarketSearchResponse)
async def search(user: CurrentUser, payload: MarketSearchRequest) -> MarketSearchResponse:
    """Haber/bilanco/rapor aramasi.

    GET degil POST: sorgu metni uzun olabilir ve URL'de loglanmasi istenmez.
    Ajan devreye GIRMEZ; dogrudan RAG indeksinde arama yapilir.
    """
    return await service.arama_yap(
        query=payload.query, top_k=payload.top_k, sirket=payload.sirket, tip=payload.tip
    )


@router.get("/news", response_model=NewsListResponse)
async def news(
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    kategori: str | None = Query(default=None, description="doviz | ekonomi | hisse | altin | piyasa"),
) -> NewsListResponse:
    """Bulten sayfasi icin en yeni haberler (duz liste, arama degil).

    Her haberin `image_url`'i doludur: gercek gorsel yoksa kategoriye/basliga
    gore otomatik atanir (bkz. app/services/news.py -> get_fallback_image).
    """
    return await news_service.haberler_getir(limit=limit, kategori=kategori)
