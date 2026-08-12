"""Bellekteki sabit veri , DB hazır olunca sql.py devreye gircek."""

_HOLDINGS: list[dict] = [
    {
        "asset_type": "hisse",
        "symbol": "THYAO",
        "quantity": 100,
        "current_value": 45000.0,
        "weight_pct": 45.0,
    },
    {
        "asset_type": "altin",
        "symbol": "GRAM",
        "quantity": 20,
        "current_value": 25000.0,
        "weight_pct": 25.0,
    },
    {
        "asset_type": "doviz",
        "symbol": "USD",
        "quantity": 500,
        "current_value": 20000.0,
        "weight_pct": 20.0,
    },
    {
        "asset_type": "tahvil",
        "symbol": "TRT",
        "quantity": 10,
        "current_value": 10000.0,
        "weight_pct": 10.0,
    },
]


class InMemoryPortfolioRepository:
    def get_holdings(self, user_id: int) -> list[dict]:
        return list(_HOLDINGS)

    def get_summary(self, user_id: int) -> dict:
        total = sum(h["current_value"] for h in _HOLDINGS)
        return {
            "total_value": total,
            "currency": "TRY",
            "holding_count": len(_HOLDINGS),
        }
