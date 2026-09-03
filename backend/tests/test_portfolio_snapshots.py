"""Portfoy snapshot yolunun eski performans hesabindan bagimsiz testleri."""

from datetime import datetime, timezone

import pytest

from app.services import portfolio as service


class _SnapshotRepository:
    async def get_value_snapshots(self, user_id, portfolio_id=None, hours=24):
        assert user_id == 7
        assert portfolio_id is None
        assert hours == 48
        return [
            {
                "ts": datetime(2026, 9, 2, 9, 30, tzinfo=timezone.utc),
                "holdings_value_try": 250_000.125,
                "cash_value_try": 50_000,
                "total_value_try": 300_000.125,
            }
        ]


@pytest.mark.asyncio
async def test_snapshot_servisi_kaydedilmis_bilesenleri_degistirmeden_dondurur(monkeypatch):
    monkeypatch.setattr(service, "get_portfolio_repository", lambda: _SnapshotRepository())

    response = await service.snapshot_performansi_getir(7, hours=48)

    assert response.hours == 48
    assert response.interval_minutes == 5
    assert len(response.points) == 1
    assert response.points[0].holdings_value_try == 250_000.12
    assert response.points[0].cash_value_try == 50_000
    assert response.points[0].total_value_try == 300_000.12
    assert response.points[0].ts == "2026-09-02T09:30:00+00:00"


@pytest.mark.asyncio
async def test_snapshot_hatasi_fiyat_tickini_durdurmaz(monkeypatch):
    from app.market import scheduler
    from app.notifications import dispatcher
    from app.services import recommendation, trading

    class MarketRepository:
        async def get_assets_for_price_update(self):
            return [{"asset_id": 1, "current_price": 100}]

        async def apply_price_updates(self, updates, write_live, source):
            return len(updates)

    class BrokenPortfolioRepository:
        async def write_value_snapshots(self):
            raise RuntimeError("snapshot tablosu gecici olarak kullanilamiyor")

    class Provider:
        name = "api"
        son_kaynak = "api"

        async def next_prices(self, assets):
            return [{"asset_id": 1, "price": 101}]

    async def no_orders(updates):
        return 0

    async def no_expired():
        return 0

    async def no_recommendations():
        return {"recommendations": []}

    async def no_notifications():
        return None

    monkeypatch.setattr(scheduler, "get_market_repository", lambda: MarketRepository())
    monkeypatch.setattr(scheduler, "get_portfolio_repository", lambda: BrokenPortfolioRepository())
    monkeypatch.setattr(trading, "bekleyen_emirleri_isle", no_orders)
    monkeypatch.setattr(recommendation, "expire_due_recommendations", no_expired)
    monkeypatch.setattr(recommendation, "generate_recommendations", no_recommendations)
    monkeypatch.setattr(dispatcher, "dispatch_notifications", no_notifications)

    assert await scheduler.price_tick(Provider(), write_live=False) == 1
