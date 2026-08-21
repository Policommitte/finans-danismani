"""Public, login gerektirmeyen endpoint sozlesmeleri."""

from pydantic import BaseModel


class PublicMarketTickerItem(BaseModel):
    symbol: str
    label: str
    value: float
    currency: str
    change_percent: float | None = None
    source: str


class PublicMarketTickerResponse(BaseModel):
    items: list[PublicMarketTickerItem]


class PublicLandingAllocationItem(BaseModel):
    asset_class: str
    class_value_try: float
    class_pct: float


class PublicLandingHoldingItem(BaseModel):
    symbol: str
    asset_name: str
    asset_class: str
    current_price: float
    daily_change_pct: float | None = None
    market_value_try: float
    pnl_pct: float | None = None


class PublicLandingPreviewResponse(BaseModel):
    total_value_try: float
    total_pnl_pct: float | None = None
    holding_count: int
    allocation: list[PublicLandingAllocationItem]
    holdings: list[PublicLandingHoldingItem]
