import pytest

from app.services import portfolio


class _PortfolioRepository:
    async def get_performance_history(self, user_id, portfolio_id, hours):
        del user_id, portfolio_id, hours
        return [
            {"ts": "2026-08-20T10:01:23+03:00", "total_value_try": 100},
            {"ts": "2026-08-20T10:14:59+03:00", "total_value_try": 102},
        ]


@pytest.mark.asyncio
async def test_performance_keeps_database_timestamps(monkeypatch):
    monkeypatch.setattr(
        portfolio,
        "get_portfolio_repository",
        lambda: _PortfolioRepository(),
    )

    result = await portfolio.performans_getir(user_id=1)

    assert [point.ts for point in result.points] == [
        "2026-08-20T10:01:23+03:00",
        "2026-08-20T10:14:59+03:00",
    ]
