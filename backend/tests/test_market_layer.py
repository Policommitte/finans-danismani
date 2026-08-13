"""Piyasa verisi katmani ve saglik uclari testleri (mimari v4 bolum 8, §14-11)."""

import pytest

from app.market.provider import ApiMarketProvider, SimulatedMarketProvider, build_provider
from app.market.scheduler import price_tick
from app.repositories.deps import describe_backend

VARLIKLAR = [
    {"asset_id": 1, "symbol": "THYAO", "current_price": 315.50, "sim_volatility": 0.02},
    {"asset_id": 12, "symbol": "BTC", "current_price": 65400.0, "sim_volatility": 0.04},
]


async def test_simulator_ayni_seed_ile_ayni_seriyi_uretir():
    """Demo tekrarlanabilirligi: prova edilen senaryo sunumda birebir ayni."""
    birinci = await SimulatedMarketProvider(seed=7).next_prices(VARLIKLAR)
    ikinci = await SimulatedMarketProvider(seed=7).next_prices(VARLIKLAR)

    assert birinci == ikinci


async def test_simulator_farkli_seed_ile_farkli_seri_uretir():
    birinci = await SimulatedMarketProvider(seed=7).next_prices(VARLIKLAR)
    ikinci = await SimulatedMarketProvider(seed=8).next_prices(VARLIKLAR)

    assert birinci != ikinci


async def test_simulator_fiyati_makul_bir_bantta_tutar():
    """Tek adimda %20'den fazla sapma olmamali; grafik gercekci kalmali."""
    saglayici = SimulatedMarketProvider(seed=3)

    for _ in range(50):
        for guncelleme in await saglayici.next_prices(VARLIKLAR):
            baz = next(
                v["current_price"] for v in VARLIKLAR if v["asset_id"] == guncelleme["asset_id"]
            )
            assert 0 < guncelleme["price"] <= baz * 1.2


async def test_simulator_sifir_fiyatli_varligi_atlar():
    sonuc = await SimulatedMarketProvider(seed=1).next_prices(
        [{"asset_id": 99, "symbol": "BOS", "current_price": 0, "sim_volatility": 0.01}]
    )

    assert sonuc == []


async def test_api_saglayici_baglanmadigi_icin_simulatore_duser():
    """Gercek API PO onayi bekliyor; sistem yine de calismali."""
    sonuc = await ApiMarketProvider().next_prices(VARLIKLAR)

    assert len(sonuc) == len(VARLIKLAR)


@pytest.mark.parametrize(
    ("ayar", "beklenen"),
    [
        ("simulated", SimulatedMarketProvider),
        ("api", ApiMarketProvider),
        ("", SimulatedMarketProvider),
    ],
)
def test_saglayici_ayara_gore_secilir(ayar, beklenen):
    assert isinstance(build_provider(ayar), beklenen)


async def test_fiyat_tick_i_fiyatlari_gunceller():
    from app.repositories.deps import get_market_repository

    repository = get_market_repository()
    onceki = (await repository.get_quote("THYAO"))["price"]

    sayi = await price_tick(SimulatedMarketProvider(seed=11), write_history=False)

    assert sayi > 0
    assert (await repository.get_quote("THYAO"))["price"] != onceki


async def test_fiyat_tick_i_gunluk_degisimi_yeniden_hesaplar():
    """Yoksa yuzde seed degerinde donar (mimari v4 bolum 8.2)."""
    from app.repositories.deps import get_market_repository

    repository = get_market_repository()
    onceki = (await repository.get_quote("BTC"))["daily_change_pct"]

    await price_tick(SimulatedMarketProvider(seed=13), write_history=False)

    assert (await repository.get_quote("BTC"))["daily_change_pct"] != onceki


# ---------------------------------------------------------------------------
# Saglik uclari
# ---------------------------------------------------------------------------


def test_health_veri_kaynagini_bildirir(client):
    govde = client.get("/health").json()

    assert govde["status"] == "ok"
    assert govde["data_source"] == "in-memory"


def test_health_db_url_yoksa_disabled_doner(client):
    """'DB yok' ile 'DB var ama erisilemiyor' ayirt edilebilmeli."""
    govde = client.get("/health/db").json()

    assert govde["status"] == "disabled"


def test_health_kimlik_dogrulama_istemez(client):
    assert client.get("/health").status_code == 200


def test_veri_kaynagi_ayara_gore_raporlanir(override_settings):
    from app.repositories.deps import reset_repositories

    override_settings(database_url="postgresql+psycopg://x/y")
    reset_repositories()

    assert describe_backend() == "postgresql"
