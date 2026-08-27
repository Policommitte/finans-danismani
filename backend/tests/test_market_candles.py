"""Trading grafigi OHLC toplulastirma testleri."""

from datetime import datetime, timezone

import pytest

from app.services import market


class CandleRepository:
    async def get_candles(self, symbol: str, interval: str, days: int) -> list[dict]:
        return []

    async def get_history(self, symbol: str, days: int = 30) -> list[dict]:
        assert symbol == "THYAO"
        assert days == 60
        return [
            {"ts": datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc), "price": 100},
            {"ts": datetime(2026, 8, 25, 9, 5, tzinfo=timezone.utc), "price": 105},
            {"ts": datetime(2026, 8, 25, 9, 10, tzinfo=timezone.utc), "price": 98},
            {"ts": datetime(2026, 8, 25, 9, 15, tzinfo=timezone.utc), "price": 102},
        ]


@pytest.mark.asyncio
async def test_fiyat_noktalari_15_dakikalik_ohlc_mumlarina_toplanir(monkeypatch):
    monkeypatch.setattr(market, "get_market_repository", lambda: CandleRepository())

    response = await market.mumlar_getir("THYAO", interval="15m", range_key="5d")

    assert response.symbol == "THYAO"
    assert response.interval == "15m"
    assert len(response.candles) == 2
    assert response.candles[0].model_dump() == {
        "time": int(datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc).timestamp()),
        "open": 100.0,
        "high": 105.0,
        "low": 98.0,
        "close": 98.0,
        "volume": None,
    }
    assert response.candles[1].open == 102
    assert response.candles[1].close == 102


class OhlcvRepository:
    requested_interval = None
    requested_days = None

    async def get_candles(self, symbol: str, interval: str, days: int) -> list[dict]:
        self.requested_interval = interval
        self.requested_days = days
        return [
            {
                "ts": datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
                "open": 100,
                "high": 108,
                "low": 99,
                "close": 105,
                "volume": 10,
            },
            {
                "ts": datetime(2026, 8, 25, 9, 5, tzinfo=timezone.utc),
                "open": 105,
                "high": 110,
                "low": 102,
                "close": 107,
                "volume": 20,
            },
        ]


@pytest.mark.asyncio
async def test_gercek_ohlcv_satirlari_ust_periyoda_toplanir(monkeypatch):
    monkeypatch.setattr(market, "get_market_repository", lambda: OhlcvRepository())

    response = await market.mumlar_getir("THYAO", interval="15m", range_key="1d")

    assert len(response.candles) == 1
    assert response.candles[0].model_dump() == {
        "time": int(datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc).timestamp()),
        "open": 100.0,
        "high": 110.0,
        "low": 99.0,
        "close": 107.0,
        "volume": 30.0,
    }


@pytest.mark.asyncio
async def test_uzun_tarih_araligi_gunluk_mum_kaynagini_kullanir(monkeypatch):
    repository = OhlcvRepository()
    monkeypatch.setattr(market, "get_market_repository", lambda: repository)

    response = await market.mumlar_getir("THYAO", interval="1d", range_key="1y")

    assert repository.requested_interval == "1d"
    assert repository.requested_days == 730
    assert response.interval == "1d"


@pytest.mark.asyncio
async def test_kisa_aralik_sola_kaydirma_icin_gecmis_mumlari_da_yukler(monkeypatch):
    repository = OhlcvRepository()
    monkeypatch.setattr(market, "get_market_repository", lambda: repository)

    await market.mumlar_getir("THYAO", interval="5m", range_key="1d")

    assert repository.requested_interval == "5m"
    assert repository.requested_days == 60


@pytest.mark.asyncio
async def test_bir_dakikalik_grafik_ham_1dk_mumlarini_kullanir(monkeypatch):
    repository = OhlcvRepository()
    monkeypatch.setattr(market, "get_market_repository", lambda: repository)

    await market.mumlar_getir("THYAO", interval="1m", range_key="1d")

    assert repository.requested_interval == "1m"
    assert repository.requested_days == 30


def test_dort_saatlik_mumlar_istanbul_saatine_hizalanir():
    candles = market._ohlcv_topla(
        [
            {
                "ts": datetime(2026, 8, 24, 6, 55, tzinfo=timezone.utc),
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 10,
            },
            {
                "ts": datetime(2026, 8, 24, 14, 55, tzinfo=timezone.utc),
                "open": 101,
                "high": 103,
                "low": 100,
                "close": 102,
                "volume": 20,
            },
        ],
        market.INTERVAL_SECONDS["4h"],
    )

    assert [candle.time for candle in candles] == [
        int(datetime(2026, 8, 24, 5, 0, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 8, 24, 13, 0, tzinfo=timezone.utc).timestamp()),
    ]
