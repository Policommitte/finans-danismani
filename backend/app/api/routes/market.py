"""Piyasa uclari - varlik listesi, fiyat grafigi, RAG destekli arama."""

from typing import Literal

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.forecast import service as forecast_service
from app.forecast.types import Tahmin
from app.schemas.market import (
    AssetsResponse,
    CandlesResponse,
    HistoryResponse,
    MarketSearchRequest,
    MarketSearchResponse,
    NewsListResponse,
    OhlcResponse,
    PhotoResponse,
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


@router.get("/candles", response_model=CandlesResponse)
async def candles(
    user: CurrentUser,
    symbol: str = Query(description="Varlik kodu (orn. THYAO)"),
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = "15m",
    range_key: Literal["1d", "5d", "1m", "3m", "1y"] = Query("1m", alias="range"),
) -> CandlesResponse:
    """Trading grafigi icin zaman kovalarina ayrilmis OHLC mumlari."""
    return await service.mumlar_getir(symbol, interval=interval, range_key=range_key)


@router.get("/photo", response_model=PhotoResponse)
async def photo(
    user: CurrentUser,
    query: str = Query(min_length=2, description="Pexels arama terimi (orn. sirket/varlik adi)"),
) -> PhotoResponse:
    """Genel amacli fotograf aramasi (bkz. app/services/pexels.py).

    Tek bir habere bagli olmayan gorsel ihtiyaclari icin (portfoy varligi
    kapak gorseli, Yatirim Oyunu magaza karti gorseli gibi). `url` null
    donebilir - frontend bu durumda kendi yerel ikon/gradyan geri dususune
    duser, 404 FIRLATILMAZ.
    """
    return await service.fotograf_getir(query)


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
    kategori: str | None = Query(
        default=None, description="doviz | ekonomi | hisse | altin | piyasa"
    ),
) -> NewsListResponse:
    """Bulten sayfasi icin en yeni haberler (duz liste, arama degil).

    Her haberin `image_url`'i doludur: gercek gorsel yoksa kategoriye/basliga
    gore otomatik atanir (bkz. app/services/news.py -> get_fallback_image).
    """
    return await news_service.haberler_getir(limit=limit, kategori=kategori)


@router.get("/forecast", response_model=Tahmin | None)
async def forecast(
    user: CurrentUser, symbol: str = Query(description="Varlik kodu (orn. THYAO, USD/TRY)")
) -> Tahmin | None:
    """Bir varligin ~1 aylik fiyat tahmini; ozellik kapaliysa `null`.

    Sembol SORGU PARAMETRESIDIR, yol parcasi degil - kardes uclarla ayni
    (`/candles?symbol=`). Yol parcasi olarak yazildiginda `USD/TRY` ve
    `EUR/TRY` icin 404 aliniyordu: frontend `encodeURIComponent` ile
    `USD%2FTRY` gonderse de sunucu yolu yonlendirmeden ONCE cozuyor ve
    `/forecast/USD/TRY` hicbir rotaya uymuyor (TestClient ile dogrulandi).
    Frontend hatayi yuttugu icin doviz tahminleri sessizce hic cizilmiyordu.

    `null` donmesi HATA DEGILDIR - tahmin ozelligi opsiyoneldir
    (`FORECAST_MODEL` bos ya da torch/timesfm kurulu degil). Frontend
    `null` gorunce kesikli cizgiyi cizmez, grafigin geri kalani calisir.

    ⚠️ DOGRULUK BEKLENTISI: olculen hata naive tahmine (fiyat sabit kalir)
    cok yakindir - %6,93 vs %7,07 MAPE. Asil guvenilir bilgi NOKTA
    tahmininde degil, `alt`/`ust` BANDINDADIR (olculen kapsam %79,1,
    hedef %80). Arayuzun bunu boyle sunmasi urun karariydi.
    """
    return await forecast_service.varlik_tahmini(symbol)


@router.get("/forecast-portfolio", response_model=Tahmin | None)
async def forecast_portfolio(user: CurrentUser) -> Tahmin | None:
    """Kullanicinin TUM portfoyunun (varliklar + nakit) TL bazli tahmini.

    Tekil varlik tahminlerinin aksine burada para birimi cevirimi ve
    korelasyon dusuncesi devreye girer - bkz.
    `app/forecast/service.py::portfoy_tahmini` ve
    `engine.py::portfoy_tahmini_birlestir`.
    """
    return await forecast_service.portfoy_tahmini(user["id"])
