"""Atıl bakiye için sohbet üzerinden üretilen öneri sözleşmesi."""

from typing import Literal

from pydantic import BaseModel, Field


class IdleCashSuggestionItem(BaseModel):
    asset_id: int
    symbol: str
    name: str
    asset_class: str
    quantity: float = Field(gt=0)
    reference_price: float = Field(gt=0)
    estimated_amount: float = Field(gt=0)
    weight_pct: float = Field(gt=0, le=100)
    rationale: list[str]


class IdleCashSuggestion(BaseModel):
    mode: Literal["basket", "single"]
    balance_source: Literal["idle_balance", "paper_cash"]
    available_balance: float = Field(gt=0)
    investable_amount: float = Field(gt=0)
    estimated_total: float = Field(gt=0)
    unallocated_balance: float = Field(ge=0)
    risk_profile: Literal["LOW", "MEDIUM", "HIGH"]
    goal: Literal["LONG_TERM", "GROWTH", "MOMENTUM", "LOW_VOLATILITY"]
    preference_summary: str
    items: list[IdleCashSuggestionItem]
    disclaimer: str
    generated_at: str


class IdleCashSuggestionRequest(BaseModel):
    goal: Literal["LONG_TERM", "GROWTH", "MOMENTUM", "LOW_VOLATILITY"] = "LONG_TERM"


class IdleCashBasketOption(BaseModel):
    id: str
    title: str
    summary: str
    suggestion: IdleCashSuggestion


class IdleCashBasketCatalog(BaseModel):
    goal: Literal["LONG_TERM", "GROWTH", "MOMENTUM", "LOW_VOLATILITY"]
    universe_size: int = Field(ge=1)
    eligible_asset_count: int = Field(ge=1)
    options: list[IdleCashBasketOption] = Field(min_length=1)
