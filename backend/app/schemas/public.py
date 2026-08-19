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

