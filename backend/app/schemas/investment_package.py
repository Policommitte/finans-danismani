"""Guided "I want to invest" chat flow: request/response contract.

The chat widget collects budget, horizon, risk appetite and goal through
quick-reply chips, then asks the backend for a ready-made package built on
the same rule-based scoring engine that powers the idle-cash baskets
(`services/idle_cash.py`). Buying the package reuses the regular paper
trading order endpoints, so limits, balance and idempotency checks stay in
one place.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.idle_cash import IdleCashBasketMetrics, IdleCashSuggestion

InvestmentHorizon = Literal["SHORT", "MEDIUM", "LONG"]
RiskProfile = Literal["LOW", "MEDIUM", "HIGH"]
InvestmentGoal = Literal["LONG_TERM", "GROWTH", "MOMENTUM", "LOW_VOLATILITY"]


class InvestmentPackageRequest(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000, description="Budget in TRY")
    horizon: InvestmentHorizon
    risk_profile: RiskProfile
    goal: InvestmentGoal


class InvestmentPackage(BaseModel):
    title: str
    summary: str
    horizon: InvestmentHorizon
    horizon_label: str
    risk_profile: RiskProfile
    goal: InvestmentGoal
    goal_label: str
    requested_amount: float = Field(gt=0)
    available_balance: float = Field(ge=0)
    #: True when the requested budget is above the cash the user actually has;
    #: the package is still produced so the user can see it, but the UI warns
    #: before the one-tap purchase.
    exceeds_balance: bool
    strategy_key: Literal["CORE", "DEFENSIVE", "OPPORTUNITY"]
    strategy_label: str
    metrics: IdleCashBasketMetrics
    suggestion: IdleCashSuggestion
    disclaimer: str
