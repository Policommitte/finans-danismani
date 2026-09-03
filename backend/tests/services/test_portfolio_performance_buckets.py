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


@pytest.mark.asyncio
async def test_performance_normalizes_bist100_to_portfolio_baseline(monkeypatch):
    class _BenchmarkRepository:
        async def get_performance_history(self, user_id, portfolio_id, hours):
            del user_id, portfolio_id, hours
            return [
                {"ts": "2026-08-20T10:00:00+03:00", "total_value_try": 1000, "bist100_price": 100},
                {"ts": "2026-08-20T10:15:00+03:00", "total_value_try": 1040, "bist100_price": 105},
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _BenchmarkRepository())

    result = await portfolio.performans_getir(user_id=1)

    assert [point.bist100_value_try for point in result.points] == [1000.0, 1050.0]


@pytest.mark.asyncio
async def test_performance_uses_same_timestamp_for_late_benchmark_baseline(monkeypatch):
    class _LateBenchmarkRepository:
        async def get_performance_history(self, user_id, portfolio_id, hours):
            del user_id, portfolio_id, hours
            return [
                {"ts": "2026-08-20T10:00:00+03:00", "total_value_try": 1000, "bist100_price": None},
                {"ts": "2026-08-20T10:15:00+03:00", "total_value_try": 1040, "bist100_price": 100},
                {"ts": "2026-08-20T10:30:00+03:00", "total_value_try": 1080, "bist100_price": 105},
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _LateBenchmarkRepository())

    result = await portfolio.performans_getir(user_id=1)

    assert [point.bist100_value_try for point in result.points] == [None, 1040.0, 1092.0]
