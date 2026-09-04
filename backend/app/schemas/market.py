"""Piyasa sekmesi sozlesmeleri."""

from pydantic import BaseModel, Field


class Asset(BaseModel):
    symbol: str
    name: str
    asset_class: str
    currency: str
    current_price: float
    daily_change_pct: float | None = None
    weekly_change_pct: float | None = None
    yearly_change_pct: float | None = None


class AssetsResponse(BaseModel):
    items: list[Asset]


class PricePoint(BaseModel):
    ts: str = Field(description="ISO-8601 zaman damgasi")
    price: float


class HistoryResponse(BaseModel):
    """PriceChart - HAM seri (MCP tool'undan farkli olarak ozetlenmez)."""

    symbol: str
    days: int
    points: list[PricePoint]


class OhlcCandle(BaseModel):
    ts: str = Field(description="ISO-8601 zaman damgasi")
    open: float
    high: float
    low: float
    close: float


class OhlcResponse(BaseModel):
    """Mum grafik icin GERCEK gunluk OHLC serisi (bkz. app/market/yahoo.py).

    `candles` bos donebilir: sembolun dogrudan bir Yahoo ticker'i yoksa
    (turetilmis GRAM_ALTIN/GUMUS gibi) veya veri gecici olarak alinamadiysa.
    Frontend bu durumda cizgi grafige duser - UYDURMA mum ASLA uretilmez.
    """

    symbol: str
    days: int
    candles: list[OhlcCandle]


class Candle(BaseModel):
    time: int = Field(description="Mum baslangici, Unix saniyesi (UTC)")
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class CandlesResponse(BaseModel):
    symbol: str
    interval: str
    range: str
    candles: list[Candle]


class TechnicalIndicator(BaseModel):
    key: str
    label: str = Field(description="Arayuzde gosterilen ad, orn. 'RSI(14)'")
    value: float | None = None
    signal: str = Field(description="AL | SAT | NOTR | VERI_YOK")


class TechnicalMovingAverage(BaseModel):
    period: int
    sma: float | None = None
    sma_signal: str
    ema: float | None = None
    ema_signal: str


class TechnicalSummary(BaseModel):
    """Sinyallerin toplulastirilmis sonucu."""

    label: str = Field(description="GUCLU_AL | AL | NOTR | SAT | GUCLU_SAT")
    score: float = Field(description="-1 (guclu sat) ile +1 (guclu al) arasi")
    buy: int
    neutral: int
    sell: int


class TechnicalResponse(BaseModel):
    """Gunluk mumlardan hesaplanan teknik gorunum.

    `sufficient` False oldugunda hicbir sinif uretilmez ve `summary` null
    doner - eksik veriyle sayi UYDURULMAZ. 404 firlatilmaz; frontend bu
    durumda "analiz icin veri yetersiz" gosterir.
    """

    symbol: str
    interval: str = Field(default="1d", description="Sabit gunluk mum")
    days: int = Field(description="Istenen takvim penceresi (gun)")
    candle_count: int
    last_candle_ts: str | None = None
    source: str = Field(description="market_candles | yahoo | price_history | yok")
    sufficient: bool
    reason: str | None = Field(default=None, description="Yetersizse sebebi")
    price: float | None = None
    summary: TechnicalSummary | None = None
    indicator_summary: TechnicalSummary | None = None
    moving_average_summary: TechnicalSummary | None = None
    indicators: list[TechnicalIndicator] = []
    moving_averages: list[TechnicalMovingAverage] = []


class PhotoResponse(BaseModel):
    """Genel amacli Pexels fotograf aramasi (bkz. app/services/pexels.py).

    `url` None donebilir: API anahtari tanimsiz, sonuc yok veya istek
    basarisiz oldu - cagiran taraf (frontend) bu durumda kendi yerel
    ikon/gradyan geri dususune duser, hata GOSTERILMEZ.
    """

    query: str
    url: str | None = None


class MarketSearchRequest(BaseModel):
    query: str = Field(min_length=2, description="Dogal dilde arama sorgusu")
    top_k: int = Field(default=5, ge=1, le=20)
    sirket: str | None = Field(default=None, description="Sirket/sembol filtresi")
    tip: str | None = Field(default=None, description="haber | bilanco | analist_raporu | duyuru")


class SearchHit(BaseModel):
    doc_id: str | None = None
    baslik: str | None = None
    sirket: str | None = Field(default=None, description="Sirket unvani (orn. Turk Hava Yollari)")
    symbol: str | None = Field(default=None, description="Varlik kodu (orn. THYAO)")
    tarih: str | None = None
    tip: str | None = None
    excerpt: str = Field(description="Chunk metninin kirpilmis hali")
    score: float | None = None


class MarketSearchResponse(BaseModel):
    query: str
    items: list[SearchHit]


class NewsArticle(BaseModel):
    id: str
    baslik: str
    sirket: str | None = None
    symbol: str | None = None
    tarih: str | None = None
    tip: str | None = None
    kategori: str | None = None
    kaynak_url: str | None = None
    excerpt: str = Field(description="raw_text'in kirpilmis hali")
    body: list[str] = Field(description="raw_text paragraf paragraf")
    image_url: str = Field(
        description="Gercek gorsel varsa o, yoksa kategoriye gore otomatik atanan gorsel"
    )
    related_change_pct: float | None = Field(
        default=None,
        description=(
            "Haberin ilgili oldugu varligin (kategori/baslikta gecen sirket adindan "
            "cikarilir - orn. altin haberi -> GRAM_ALTIN) CANLI gunluk degisim yuzdesi. "
            "Guvenilir bir eslesme yoksa None doner; frontend bu durumda rozet gostermez."
        ),
    )


class NewsListResponse(BaseModel):
    items: list[NewsArticle]
