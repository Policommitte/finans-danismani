"""Paper trading API sozlesmeleri."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

OrderSide = Literal["BUY", "SELL"]
OrderStatus = Literal["PENDING", "FILLED", "REJECTED", "CANCELLED"]
EntryOrderType = Literal["MARKET", "LIMIT"]
OrderType = Literal["MARKET", "LIMIT", "STOP_MARKET"]
OrderValidity = Literal["DAY", "GTC"]


class TradingAccount(BaseModel):
    portfolio_id: int
    portfolio_name: str
    currency: str = "TRY"
    available_balance: float
    reserved_balance: float


class OrderPreviewRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: OrderSide
    quantity: float = Field(gt=0)
    order_type: EntryOrderType = "MARKET"
    limit_price: float | None = Field(default=None, gt=0)
    stop_loss_price: float | None = Field(default=None, gt=0)
    validity: OrderValidity = "GTC"

    @model_validator(mode="after")
    def validate_limit_price(self):
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("Limit emri için limit fiyatı zorunludur.")
        if self.side == "SELL" and self.stop_loss_price is not None:
            raise ValueError("Stop-loss yalnızca alım emrine eklenebilir.")
        return self


class OrderPreview(BaseModel):
    symbol: str
    asset_name: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    limit_price: float | None = None
    stop_loss_price: float | None = None
    stop_loss_currency: str | None = None
    validity: OrderValidity
    expires_at: str | None = None
    quoted_price: float
    gross_amount: float
    estimated_commission: float
    estimated_total: float
    estimated_reserve: float
    available_balance: float
    holding_quantity: float
    price_updated_at: str | None = None
    execution_note: str


class CreateOrderRequest(OrderPreviewRequest):
    idempotency_key: str = Field(min_length=8, max_length=100)


class PercentageBasketAllocation(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    weight_pct: float = Field(gt=0, le=100)


class PercentageBasketPreviewRequest(BaseModel):
    allocations: list[PercentageBasketAllocation] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def validate_allocations(self):
        symbols = [item.symbol.strip().upper() for item in self.allocations]
        if len(symbols) != len(set(symbols)):
            raise ValueError("Sepette ayni sembol birden fazla kez kullanilamaz.")
        total = sum(item.weight_pct for item in self.allocations)
        if abs(total - 100) > 1e-6:
            raise ValueError("Sepet agirliklarinin toplami yuzde 100 olmalidir.")
        return self


class PercentageBasketPreviewItem(BaseModel):
    symbol: str
    asset_name: str
    asset_class: str
    currency: str
    weight_pct: float
    quoted_price_try: float
    quantity: float
    estimated_gross: float
    estimated_reserve: float


class PercentageBasketPreview(BaseModel):
    available_balance: float
    investable_gross: float
    estimated_gross: float
    estimated_reserve: float
    remaining_balance: float
    items: list[PercentageBasketPreviewItem]
    unavailable_symbols: list[str]
    unaffordable_symbols: list[str]


class PaperOrder(BaseModel):
    id: int
    symbol: str
    asset_name: str
    side: OrderSide
    order_type: OrderType = "MARKET"
    limit_price: float | None = None
    stop_loss_price: float | None = None
    stop_loss_currency: str | None = None
    parent_order_id: int | None = None
    validity: OrderValidity = "GTC"
    expires_at: str | None = None
    quantity: float
    quoted_price: float
    status: OrderStatus
    filled_quantity: float
    average_fill_price: float | None = None
    commission: float
    rejection_reason: str | None = None
    created_at: str
    filled_at: str | None = None


class OrdersResponse(BaseModel):
    items: list[PaperOrder]
    limit: int
