"""İşlem merkezindeki kalıcı atıl bakiye sepeti sözleşmesi."""

from typing import Literal

from pydantic import BaseModel, Field


class IdleCashSuggestionItem(BaseModel):
    asset_id: int
    symbol: str
    name: str
    asset_class: str
    currency: str
    sector: str
    region: str
    quantity: float = Field(gt=0)
    reference_price: float = Field(gt=0)
    estimated_amount: float = Field(gt=0)
    weight_pct: float = Field(gt=0, le=100)
    goal_rank: int = Field(ge=1)
    candidate_count: int = Field(ge=1)
    suitability_level: Literal["HIGH", "MEDIUM", "LOW"]
    score_components: dict[str, float]
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


class IdleCashBasketMetrics(BaseModel):
    expected_volatility_20d_pct: float = Field(ge=0)
    average_correlation: float | None = Field(default=None, ge=-1, le=1)
    diversification_score: float = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    asset_class_count: int = Field(ge=1)
    sector_count: int = Field(ge=1)
    region_count: int = Field(ge=1)
    largest_weight_pct: float = Field(gt=0, le=100)


class IdleCashBasketBacktest(BaseModel):
    status: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT"]
    methodology_version: str
    observation_count: int = Field(ge=0)
    start_date: str | None = None
    end_date: str | None = None
    gross_return_pct: float | None = None
    net_return_pct: float | None = None
    benchmark_return_pct: float | None = None
    excess_return_pct: float | None = None
    annualized_volatility_pct: float | None = Field(default=None, ge=0)
    max_drawdown_pct: float | None = Field(default=None, ge=0)
    risk_adjusted_return: float | None = None
    transaction_cost_impact_pct: float | None = Field(default=None, ge=0)
    rebalance_count: int = Field(ge=0)
    benchmark_label: str
    note: str


class IdleCashBasketOption(BaseModel):
    id: str
    title: str
    summary: str
    strategy_key: Literal["CORE", "DEFENSIVE", "OPPORTUNITY"]
    strategy_label: str
    strategy_description: str
    metrics: IdleCashBasketMetrics
    backtest: IdleCashBasketBacktest
    suggestion: IdleCashSuggestion


class IdleCashBasketCatalog(BaseModel):
    goal: Literal["LONG_TERM", "GROWTH", "MOMENTUM", "LOW_VOLATILITY"]
    universe_size: int = Field(ge=1)
    eligible_asset_count: int = Field(ge=1)
    stale_asset_count: int = Field(ge=0)
    insufficient_history_asset_count: int = Field(ge=0)
    evaluation_frequency: str
    evaluated_at: str
    last_changed_at: str
    next_evaluation_at: str
    membership_changed: bool = False
    stability_note: str
    options: list[IdleCashBasketOption] = Field(min_length=1)
