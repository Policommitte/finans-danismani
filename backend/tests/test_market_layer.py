"""Piyasa verisi katmani ve saglik uclari testleri (mimari v4 bolum 8, §14-11)."""

from contextlib import asynccontextmanager

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


@pytest.mark.db
async def test_fiyat_tick_i_fiyatlari_gunceller():
    """Fiyat yazimi DESTRUKTIFTIR; test kendi degisikligini geri alir.

    Alinmasaydi bu testten sonra calisan tum toplam/dagilim testleri seed
    degerini degil uretilmis fiyati gorurdu.
    """
    async with _fiyatlari_koru():
        from app.repositories.deps import get_market_repository

        repository = get_market_repository()
        onceki = (await repository.get_quote("THYAO"))["price"]

        sayi = await price_tick(SimulatedMarketProvider(seed=11), write_history=False)

        assert sayi > 0
        assert (await repository.get_quote("THYAO"))["price"] != onceki


@pytest.mark.db
async def test_fiyat_tick_i_gunluk_degisimi_yeniden_hesaplar():
    """Yoksa yuzde seed degerinde donar (mimari v4 bolum 8.2)."""
    async with _fiyatlari_koru():
        from app.repositories.deps import get_market_repository

        repository = get_market_repository()
        onceki = (await repository.get_quote("BTC"))["daily_change_pct"]

        await price_tick(SimulatedMarketProvider(seed=13), write_history=False)

        assert (await repository.get_quote("BTC"))["daily_change_pct"] != onceki


@asynccontextmanager
async def _fiyatlari_koru():
    """`assets` fiyat kolonlarini test sonrasi eski haline dondurur."""
    from sqlalchemy import text

    from app.db.session import get_session_factory

    async with get_session_factory()() as session:
        onceki = (
            (
                await session.execute(
                    text("SELECT id, current_price, prev_close, daily_change_pct FROM assets")
                )
            )
            .mappings()
            .all()
        )

    try:
        yield
    finally:
        async with get_session_factory()() as session:
            for satir in onceki:
                await session.execute(
                    text(
                        "UPDATE assets SET current_price = :p, prev_close = :pc, "
                        "daily_change_pct = :d WHERE id = :i"
                    ),
                    {
                        "p": satir["current_price"],
                        "pc": satir["prev_close"],
                        "d": satir["daily_change_pct"],
                        "i": satir["id"],
                    },
                )
            await session.commit()


# ---------------------------------------------------------------------------
# Saglik uclari
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_health_veri_kaynagini_bildirir(client):
    govde = client.get("/health").json()

    assert govde["status"] == "ok"
    assert govde["data_source"] == "postgresql"


def test_health_db_url_yoksa_disabled_doner(client, override_settings):
    """'DB yok' ile 'DB var ama erisilemiyor' ayirt edilebilmeli."""
    override_settings(database_url="")

    govde = client.get("/health/db").json()

    assert govde["status"] == "disabled"


def test_health_kimlik_dogrulama_istemez(client):
    assert client.get("/health").status_code == 200


def test_baglanti_kurulamazsa_bellek_ici_veriye_dusulur(override_settings):
    """Yedek plan: erisilemeyen bir DB tanimliysa sistem hata vermez, duser.

    Ayarin DOLU olmasi yetmez; `deps.py` gercekten baglanabiliyor mu diye
    bakar. Aksi halde ayakta olmayan bir DB'de her istek patlardi.
    """
    from app.repositories.deps import reset_repositories

    # Kapali port: baglanti aninda reddedilir.
    override_settings(database_url="postgresql+psycopg://yok:yok@127.0.0.1:1/yok")
    reset_repositories()

    assert describe_backend() == "in-memory"


def test_database_url_yoksa_bellek_ici_veriye_dusulur(override_settings):
    from app.repositories.deps import reset_repositories

    override_settings(database_url="")
    reset_repositories()

    assert describe_backend() == "in-memory"
