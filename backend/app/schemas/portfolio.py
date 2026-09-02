"""Portfoy ekrani sozlesmeleri.

Tum parasal alanlar TRY'ye normalize edilmistir ve `_try` ile biter; cevrim
DB view'inda (`v_holdings_valued`) yapilir, frontend cevrim yapmaz.
"""

from pydantic import BaseModel, Field


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


class PortfolioPerformanceResponse(BaseModel):
    points: list[PortfolioPerformancePoint]
    hours: int


class PortfolioValueSnapshotPoint(BaseModel):
    ts: str
    holdings_value_try: float
    cash_value_try: float
    total_value_try: float


class PortfolioSnapshotPerformanceResponse(BaseModel):
    points: list[PortfolioValueSnapshotPoint]
    hours: int
    interval_minutes: int = 5
