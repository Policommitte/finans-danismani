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
