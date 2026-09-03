"""Portfoy ekrani sozlesmeleri.

Tum parasal alanlar TRY'ye normalize edilmistir ve `_try` ile biter; cevrim
DB view'inda (`v_holdings_valued`) yapilir, frontend cevrim yapmaz.
"""

from typing import Literal

from pydantic import BaseModel, Field

#: Performans grafiginin donem secenekleri. Saate cevrimi TEK yerde,
#: `app/services/portfolio.py::PERFORMANS_ARALIKLARI` icinde yapilir.
PerformanceRange = Literal["1G", "1H", "1A", "1Y"]


class PortfolioSummary(BaseModel):
    """SummaryCards bileseni - `v_portfolio_summary` satiri."""

    portfolio_id: int | None = Field(default=None, description="Ozetin ait oldugu portfoy")
    holding_count: int = Field(description="Portfoydeki varlik sayisi")
    total_value_try: float = Field(description="Guncel toplam deger (TRY)")
    total_cost_try: float = Field(description="Toplam maliyet (TRY)")
    total_pnl_try: float = Field(description="Toplam kar/zarar (TRY)")
    total_pnl_pct: float | None = Field(default=None, description="Toplam kar/zarar yuzdesi")
    daily_change_try: float = Field(default=0, description="Onceki kapanisa gore degisim (TRY)")
    daily_change_pct: float | None = Field(
        default=None, description="Onceki kapanisa gore portfoy degisim yuzdesi"
    )
    weekly_change_try: float | None = Field(
        default=None, description="Yedi gun onceki dogrulanmis degere gore degisim (TRY)"
    )
    weekly_change_pct: float | None = Field(
        default=None, description="Yedi gun onceki dogrulanmis degere gore degisim yuzdesi"
    )
    monthly_change_try: float | None = Field(
        default=None, description="Otuz gun onceki dogrulanmis degere gore degisim (TRY)"
    )
    monthly_change_pct: float | None = Field(
        default=None, description="Otuz gun onceki dogrulanmis degere gore degisim yuzdesi"
    )


class Holding(BaseModel):
    """HoldingsTable satiri."""

    symbol: str
    asset_name: str
    asset_class: str = Field(description="STOCK | GOLD | FOREX | BOND | CRYPTO | ...")
    currency: str
    quantity: float
    average_buy_price: float
    current_price: float
    daily_change_pct: float | None = None
    daily_change_try: float = 0
    daily_change_pct_try: float | None = None
    market_value_try: float
    cost_basis_try: float
    pnl_try: float
    pnl_pct: float | None = None


class HoldingsResponse(BaseModel):
    items: list[Holding]
    total_value_try: float = Field(description="Satirlarin toplami - tabloda alt bilgi olarak")


class AllocationSlice(BaseModel):
    """AllocationPie dilimi."""

    asset_class: str
    class_value_try: float
    class_pct: float


class AllocationResponse(BaseModel):
    items: list[AllocationSlice]


class Transaction(BaseModel):
    id: int
    symbol: str
    asset_name: str
    transaction_type: str = Field(description="BUY | SELL")
    quantity: float
    unit_price: float
    transaction_date: str


class TransactionsResponse(BaseModel):
    items: list[Transaction]
    limit: int


class PortfolioPerformancePoint(BaseModel):
    ts: str
    total_value_try: float
    bist100_value_try: float | None = None


class SymbolPeriodPnl(BaseModel):
    """Tek bir varligin SECILEN DONEMDEKI kar/zarari.

    `Holding.pnl_try`'dan farki: o, alim gununden bugune TOPLAM kar/zarardir
    ve donemden bagimsizdir. Buradaki rakam yalnizca donem icindeki degeri
    olcer ve donem icinde yapilan alim/satimi da hesaba katar.
    """

    symbol: str
    pnl_try: float
    pnl_pct: float | None = Field(
        default=None,
        description="Donem basindaki deger + donem ici alim maliyetine oranla",
    )


class PortfolioPerformanceResponse(BaseModel):
    points: list[PortfolioPerformancePoint]
    hours: int
    range_key: PerformanceRange = Field(default="1G", description="1G | 1H | 1A | 1Y")
    change_try: float = Field(default=0.0, description="Donem boyunca portfoyun kar/zarari")
    change_pct: float | None = Field(
        default=None, description="`change_try`'in donem basi sermayeye orani"
    )
    symbol_pnl: list[SymbolPeriodPnl] = Field(
        default_factory=list, description="Varlik bazinda donem kar/zarari"
    )
