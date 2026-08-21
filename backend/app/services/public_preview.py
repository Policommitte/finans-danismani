"""Landing sayfasindaki temsili portfoy onizlemesi."""

from app.repositories.in_memory import InMemoryPortfolioRepository
from app.schemas.public import (
    PublicLandingAllocationItem,
    PublicLandingHoldingItem,
    PublicLandingPreviewResponse,
)

DEMO_USER_ID = 1


async def get_public_landing_preview() -> PublicLandingPreviewResponse:
    """Onizlemeyi aktif veritabanindan bagimsiz, sabit demo verisinden uretir."""
    repository = InMemoryPortfolioRepository()
    summary = await repository.get_summary(DEMO_USER_ID)
    allocation = await repository.get_allocation(DEMO_USER_ID)
    holdings = await repository.get_holdings(DEMO_USER_ID)

    if summary is None:
        raise RuntimeError("Landing onizleme verisi bulunamadi.")

    return PublicLandingPreviewResponse(
        total_value_try=_number(summary["total_value_try"]),
        total_pnl_pct=_optional_number(summary.get("total_pnl_pct")),
        holding_count=int(summary["holding_count"]),
        allocation=[
            PublicLandingAllocationItem(
                asset_class=item["asset_class"],
                class_value_try=_number(item["class_value"]),
                class_pct=_number(item["class_pct"]),
            )
            for item in allocation
        ],
        holdings=[
            PublicLandingHoldingItem(
                symbol=item["symbol"],
                asset_name=item["asset_name"],
                asset_class=item["asset_class"],
                current_price=_number(item["current_price"]),
                daily_change_pct=_optional_number(item.get("daily_change_pct")),
                market_value_try=_number(item["market_value_try"]),
                pnl_pct=_optional_number(item.get("pnl_pct")),
            )
            for item in holdings
        ],
    )


def _number(value: object) -> float:
    return round(float(value or 0), 2)


def _optional_number(value: object | None) -> float | None:
    return None if value is None else _number(value)
