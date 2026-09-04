import pytest

from app.services import portfolio


class _SahteRepository:
    """Donem kar/zarari BU testlerin konusu degil - hepsi zaman damgasi ve
    kiyas serisi normalizasyonuna bakiyor. `get_period_pnl` bos doner."""

    async def get_period_pnl(self, user_id, portfolio_id=None, start_ts=None):
        del user_id, portfolio_id, start_ts
        return []


class _PortfolioRepository(_SahteRepository):
    async def get_performance_history(self, user_id, portfolio_id, **kwargs):
        del user_id, portfolio_id, kwargs
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
    class _BenchmarkRepository(_SahteRepository):
        async def get_performance_history(self, user_id, portfolio_id, **kwargs):
            del user_id, portfolio_id, kwargs
            return [
                {"ts": "2026-08-20T10:00:00+03:00", "total_value_try": 1000, "bist100_price": 100},
                {"ts": "2026-08-20T10:15:00+03:00", "total_value_try": 1040, "bist100_price": 105},
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _BenchmarkRepository())

    result = await portfolio.performans_getir(user_id=1)

    assert [point.bist100_value_try for point in result.points] == [1000.0, 1050.0]


@pytest.mark.asyncio
async def test_performance_uses_same_timestamp_for_late_benchmark_baseline(monkeypatch):
    class _LateBenchmarkRepository(_SahteRepository):
        async def get_performance_history(self, user_id, portfolio_id, **kwargs):
            del user_id, portfolio_id, kwargs
            return [
                {"ts": "2026-08-20T10:00:00+03:00", "total_value_try": 1000, "bist100_price": None},
                {"ts": "2026-08-20T10:15:00+03:00", "total_value_try": 1040, "bist100_price": 100},
                {"ts": "2026-08-20T10:30:00+03:00", "total_value_try": 1080, "bist100_price": 105},
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _LateBenchmarkRepository())

    result = await portfolio.performans_getir(user_id=1)

    assert [point.bist100_value_try for point in result.points] == [None, 1040.0, 1092.0]


@pytest.mark.asyncio
async def test_uzun_aralikta_gun_ici_korumalari_KAPALI(monkeypatch):
    # Regresyon: `valid_from` (12 gun oncesini isaret eden esik) ve %5
    # sicrama filtresi gelistirme donemi artiklari icin konmustu. Uzun
    # aralikta uygulanirlarsa aylik/yillik grafik ya tamamen kesilir ya
    # da her buyuk gunluk hareketten sonra bastan baslar.
    cagrilar: list[dict] = []

    class _Repo(_SahteRepository):
        async def get_performance_history(self, user_id, portfolio_id, **kwargs):
            del user_id, portfolio_id
            cagrilar.append(kwargs)
            return [
                {"ts": "2026-01-10T10:00:00+03:00", "total_value_try": 1000},
                # %20'lik sicrama: gun ici olsa seriyi sifirlardi.
                {"ts": "2026-02-10T10:00:00+03:00", "total_value_try": 1200},
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _Repo())

    sonuc = await portfolio.performans_getir(user_id=1, range_key="1Y")

    assert cagrilar[0]["valid_from"] is None
    assert cagrilar[0]["gunluk"] is True
    assert len(sonuc.points) == 2  # sicrama seriyi KESMEDI


@pytest.mark.asyncio
async def test_gun_ici_aralikta_korumalar_ACIK(monkeypatch):
    cagrilar: list[dict] = []

    class _Repo(_SahteRepository):
        async def get_performance_history(self, user_id, portfolio_id, **kwargs):
            del user_id, portfolio_id
            cagrilar.append(kwargs)
            return [
                {"ts": "2026-08-20T10:00:00+03:00", "total_value_try": 1000},
                {"ts": "2026-08-20T10:15:00+03:00", "total_value_try": 1200},
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _Repo())

    sonuc = await portfolio.performans_getir(user_id=1, range_key="1G")

    assert cagrilar[0]["valid_from"] is not None
    assert cagrilar[0]["gunluk"] is False
    assert len(sonuc.points) == 1  # %20 sicrama oncesi seri sifirlandi


@pytest.mark.asyncio
async def test_donem_kar_zarari_bilesenlerden_hesaplanir(monkeypatch):
    class _Repo:
        async def get_performance_history(self, user_id, portfolio_id, **kwargs):
            del user_id, portfolio_id, kwargs
            return [{"ts": "2026-08-01T10:00:00+03:00", "total_value_try": 1000}]

        async def get_period_pnl(self, user_id, portfolio_id=None, start_ts=None):
            del user_id, portfolio_id, start_ts
            return [
                # Donem icinde hic islem yok: saf fiyat farki.
                {
                    "symbol": "THYAO",
                    "bitis_degeri": 1200,
                    "baslangic_degeri": 1000,
                    "alim_maliyeti": 0,
                    "satis_hasilati": 0,
                },
                # Pozisyon donem icinde acildi: bugunku deger - odenen maliyet.
                {
                    "symbol": "BTC",
                    "bitis_degeri": 550,
                    "baslangic_degeri": 0,
                    "alim_maliyeti": 500,
                    "satis_hasilati": 0,
                },
                # Cok once tamamen satilmis: ekranda hic gorunmemeli.
                {
                    "symbol": "GOOG",
                    "bitis_degeri": 0,
                    "baslangic_degeri": 0,
                    "alim_maliyeti": 0,
                    "satis_hasilati": 0,
                },
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _Repo())

    sonuc = await portfolio.performans_getir(user_id=1, range_key="1A")

    assert [s.symbol for s in sonuc.symbol_pnl] == ["THYAO", "BTC"]
    assert sonuc.symbol_pnl[0].pnl_try == 200
    assert sonuc.symbol_pnl[0].pnl_pct == 20.0
    assert sonuc.symbol_pnl[1].pnl_try == 50
    assert sonuc.symbol_pnl[1].pnl_pct == 10.0
    # Toplam, varlik bazindaki rakamlarin toplamiyla AYNI olmali.
    assert sonuc.change_try == 250
    assert sonuc.change_pct == round(250 / 1500 * 100, 2)


@pytest.mark.asyncio
async def test_bir_haftalik_aralik_gun_ici_SAYILMAZ(monkeypatch):
    # Regresyon: gun ici sinirı 168 saatti, yani 1H de gun ici yoluna
    # giriyordu. %5 sicrama filtresi son kapanis ile bugunku canli fiyat
    # arasindaki farkta tetiklenip haftanin tamamini atiyor, ekranda 1H
    # ile 1G BIREBIR AYNI gorunuyordu.
    cagrilar: list[dict] = []

    class _Repo(_SahteRepository):
        async def get_performance_history(self, user_id, portfolio_id, **kwargs):
            del user_id, portfolio_id
            cagrilar.append(kwargs)
            return [
                {"ts": "2026-08-26T21:00:00+03:00", "total_value_try": 1000},
                # Kapanistan canli fiyata gecis: gun ici olsa haftanin
                # tamamini silerdi.
                {"ts": "2026-09-02T09:00:00+03:00", "total_value_try": 1300},
            ]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _Repo())

    sonuc = await portfolio.performans_getir(user_id=1, range_key="1H")

    assert cagrilar[0]["valid_from"] is None
    # 1 hafta da gunluk kovaya iner: gun ici noktalar birakilinca hafta ici
    # kapanislar (gunde 1) ile bugunun dakikalik noktalari (onlarca) ayni
    # eksene binip grafigi solda duz, sagda sikisik birakiyordu.
    assert cagrilar[0]["gunluk"] is True
    assert len(sonuc.points) == 2


@pytest.mark.asyncio
async def test_aylik_aralik_gunluk_kovaya_iner(monkeypatch):
    cagrilar: list[dict] = []

    class _Repo(_SahteRepository):
        async def get_performance_history(self, user_id, portfolio_id, **kwargs):
            del user_id, portfolio_id
            cagrilar.append(kwargs)
            return [{"ts": "2026-08-03T21:00:00+03:00", "total_value_try": 1000}]

    monkeypatch.setattr(portfolio, "get_portfolio_repository", lambda: _Repo())

    await portfolio.performans_getir(user_id=1, range_key="1A")

    assert cagrilar[0]["gunluk"] is True
