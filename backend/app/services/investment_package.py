"""Ready-made investment package for the guided chat flow.

The chat assistant asks four things - budget, horizon, risk appetite and
goal - and hands them here. Instead of a second recommendation engine the
package is produced by the same scoring/selection pipeline as the idle-cash
baskets (`suggestion_build`), with the user's answers overriding the
profile-derived context:

* ``amount`` replaces the cash-account balance and the whole budget is
  investable (the idle-cash flow keeps a 10% buffer, a package is an
  explicit "invest this much" request).
* ``risk_profile`` replaces the stored risk tolerance for this one run.
* ``horizon`` picks the basket strategy: a short horizon leans on the
  defensive strategy, a long horizon with a high risk appetite on the
  opportunity strategy, everything else on the core strategy.
* ``goal`` is passed through untouched.

Purchasing is NOT done here - the frontend turns the package into regular
paper-trading market orders, so limits, balance and idempotency checks stay
in `services/trading.py`.
"""

from __future__ import annotations

import asyncio

from app.core.errors import NotFoundError
from app.repositories.deps import get_recommendation_repository
from app.schemas.investment_package import (
    InvestmentHorizon,
    InvestmentPackage,
    InvestmentPackageRequest,
    RiskProfile,
)
from app.services.idle_cash import _SEPET_STRATEJILERI, _sepet_metrikleri, suggestion_build
from app.services.recommendation import SPK_UYARISI

HORIZON_LABELS: dict[str, str] = {
    "SHORT": "kısa vade (1 yıla kadar)",
    "MEDIUM": "orta vade (1-3 yıl)",
    "LONG": "uzun vade (3 yıl ve üzeri)",
}

GOAL_LABELS: dict[str, str] = {
    "LONG_TERM": "uzun vadeli birikim",
    "GROWTH": "büyüme",
    "MOMENTUM": "momentum",
    "LOW_VOLATILITY": "düşük oynaklık",
}

RISK_LABELS: dict[str, str] = {"LOW": "düşük", "MEDIUM": "orta", "HIGH": "yüksek"}

PACKAGE_TITLES: dict[tuple[str, str], str] = {
    ("SHORT", "LOW"): "Güvenli Liman Paketi",
    ("SHORT", "MEDIUM"): "Kısa Vade Denge Paketi",
    ("SHORT", "HIGH"): "Kısa Vade Fırsat Paketi",
    ("MEDIUM", "LOW"): "Temkinli Birikim Paketi",
    ("MEDIUM", "MEDIUM"): "Dengeli Büyüme Paketi",
    ("MEDIUM", "HIGH"): "Atılımcı Büyüme Paketi",
    ("LONG", "LOW"): "Uzun Soluklu Güvence Paketi",
    ("LONG", "MEDIUM"): "Uzun Vade Birikim Paketi",
    ("LONG", "HIGH"): "Uzun Vade Fırsat Paketi",
}

_STRATEGY_INDEX = {strategy["key"]: index for index, strategy in enumerate(_SEPET_STRATEJILERI)}


def select_strategy_key(horizon: InvestmentHorizon, risk_profile: RiskProfile) -> str:
    """Map horizon + risk appetite onto one of the basket strategies."""
    if horizon == "SHORT":
        return "DEFENSIVE"
    if horizon == "LONG" and risk_profile == "HIGH":
        return "OPPORTUNITY"
    return "CORE"


def _to_number(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def build_package(
    context: dict,
    assets: list[dict],
    holdings: dict[int, float],
    request: InvestmentPackageRequest,
) -> InvestmentPackage:
    """Pure builder - the async wrapper below only fetches the inputs."""
    strategy_key = select_strategy_key(request.horizon, request.risk_profile)
    package_context = {
        **context,
        "risk_tolerance": request.risk_profile,
        "available_balance": request.amount,
    }
    suggestion = suggestion_build(
        package_context,
        assets,
        holdings,
        request.goal,
        strategy_index=_STRATEGY_INDEX[strategy_key],
        investable_ratio=1.0,
    )

    asset_map = {int(asset["asset_id"]): asset for asset in assets}
    selected_assets = [asset_map[item.asset_id] for item in suggestion.items]
    weights = [item.weight_pct / 100 for item in suggestion.items]
    metrics = _sepet_metrikleri(selected_assets, weights)

    actual_balance = round(max(0.0, _to_number(context.get("available_balance"))), 2)
    strategy = _SEPET_STRATEJILERI[_STRATEGY_INDEX[strategy_key]]
    formatted_amount = f"{request.amount:,.0f}".replace(",", ".")
    summary = (
        f"{formatted_amount} TL bütçe, {HORIZON_LABELS[request.horizon]}, "
        f"{RISK_LABELS[request.risk_profile]} risk iştahı ve "
        f"{GOAL_LABELS[request.goal]} hedefi için {len(suggestion.items)} varlıktan oluşan, "
        f"{strategy['label'].lower()} stratejili bir paket hazırlandı."
    )

    return InvestmentPackage(
        title=PACKAGE_TITLES[(request.horizon, request.risk_profile)],
        summary=summary,
        horizon=request.horizon,
        horizon_label=HORIZON_LABELS[request.horizon],
        risk_profile=request.risk_profile,
        goal=request.goal,
        goal_label=GOAL_LABELS[request.goal],
        requested_amount=round(request.amount, 2),
        available_balance=actual_balance,
        exceeds_balance=request.amount > actual_balance,
        strategy_key=strategy_key,  # type: ignore[arg-type]
        strategy_label=str(strategy["label"]),
        metrics=metrics,
        suggestion=suggestion,
        disclaimer=SPK_UYARISI,
    )


async def investment_package_for_user(
    user_id: int, request: InvestmentPackageRequest
) -> InvestmentPackage:
    repository = get_recommendation_repository()
    context, assets = await asyncio.gather(
        repository.user_context(user_id),
        repository.assets_for_scan(),
    )
    if context is None:
        raise NotFoundError("Bakiye ve risk bilgileri alınamadı.")
    holdings = await repository.holdings_map(int(context["portfolio_id"]))
    return build_package(context, assets, holdings, request)
