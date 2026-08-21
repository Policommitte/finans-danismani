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


@pytest.mark.parametrize(
    ("ayar", "beklenen"),
    [
        ("simulated", SimulatedMarketProvider),
        ("api", ApiMarketProvider),
    ],
)
def test_saglayici_ayara_gore_secilir(ayar, beklenen):
    assert isinstance(build_provider(ayar), beklenen)


def test_ayar_bos_birakilirsa_varsayilan_saglayici_secilir(monkeypatch):
    """Bos ayar `MARKET_DATA_PROVIDER` varsayilanina duser (su an "api")."""
    from app.config import settings

    monkeypatch.setattr(settings, "market_data_provider", "api")
    assert isinstance(build_provider(""), ApiMarketProvider)

    monkeypatch.setattr(settings, "market_data_provider", "simulated")
    assert isinstance(build_provider(""), SimulatedMarketProvider)


# ---------------------------------------------------------------------------
# ApiMarketProvider - Yahoo'ya baglanan gercek saglayici
#
# Bu testler AGA CIKMAZ: `app.market.yahoo.canli_fiyatlar` degistirilir.
# Gercek cagri yapilsaydi testler yavas ve kirilgan olurdu (Yahoo resmi API
# degildir; kesinti veya engelleme CI'yi kirmis olurdu).
# ---------------------------------------------------------------------------


class SahteKotaDeposu:
    """`get_api_usage_today` / `record_api_usage` sunan bellek ici depo."""

    def __init__(self, kullanilan: int = 0) -> None:
        self.kullanilan = kullanilan
        self.kaydedilen = 0

    async def get_api_usage_today(self) -> int:
        return self.kullanilan

    async def record_api_usage(self, calls: int = 1) -> None:
        self.kaydedilen += calls


def _yahoo_taklit(monkeypatch, fiyatlar=None, hata: Exception | None = None):
    """`canli_kotasyonlar` yerine sahte bir uygulama koyar; cagriyi kaydeder."""
    from app.market import yahoo

    cagrilar: list[list[str]] = []

    async def sahte(db_symbols):
        cagrilar.append(list(db_symbols))
        if hata is not None:
            raise hata
        return {
            symbol: {"price": price, "previous_close": None}
            for symbol, price in (fiyatlar or {}).items()
        }

    monkeypatch.setattr(yahoo, "canli_kotasyonlar", sahte)
    return cagrilar


async def test_api_saglayici_yahoo_fiyatlarini_dondurur(monkeypatch):
    _yahoo_taklit(monkeypatch, fiyatlar={"THYAO": 301.25, "BTC": 64227.97})
    saglayici = ApiMarketProvider(kota_deposu=SahteKotaDeposu())

    sonuc = await saglayici.next_prices(VARLIKLAR)

    assert sonuc == [
        {"asset_id": 1, "price": 301.25},
        {"asset_id": 12, "price": 64227.97},
    ]
    assert saglayici.son_kaynak == "api"


async def test_api_saglayici_onceki_kapanisi_repository_guncellemesine_tasir(monkeypatch):
    from app.market import yahoo

    async def sahte(_symbols):
        return {"THYAO": {"price": 301.25, "previous_close": 298.0}}

    monkeypatch.setattr(yahoo, "canli_kotasyonlar", sahte)
    sonuc = await ApiMarketProvider(kota_deposu=SahteKotaDeposu()).next_prices(VARLIKLAR)

    assert sonuc == [{"asset_id": 1, "price": 301.25, "previous_close": 298.0}]


async def test_fiyati_alinamayan_varlik_atlanir(monkeypatch):
    """Eksik fiyat icin eski deger korunur; listeye EKLENMEZ."""
    _yahoo_taklit(monkeypatch, fiyatlar={"THYAO": 301.25})
    saglayici = ApiMarketProvider(kota_deposu=SahteKotaDeposu())

    sonuc = await saglayici.next_prices(VARLIKLAR)

    assert sonuc == [{"asset_id": 1, "price": 301.25}]


async def test_yahoo_hata_verirse_son_fiyatlar_korunur(monkeypatch):
    """KRITIK: ag hatasi portfoy fiyatlarini simule etmemeli."""
    _yahoo_taklit(monkeypatch, hata=TimeoutError("yahoo yanit vermedi"))
    saglayici = ApiMarketProvider(kota_deposu=SahteKotaDeposu())

    sonuc = await saglayici.next_prices(VARLIKLAR)

    assert sonuc == []
    assert saglayici.son_kaynak == "unavailable"


async def test_yahoo_bos_dondururse_son_fiyatlar_korunur(monkeypatch):
    _yahoo_taklit(monkeypatch, fiyatlar={})
    saglayici = ApiMarketProvider(kota_deposu=SahteKotaDeposu())

    sonuc = await saglayici.next_prices(VARLIKLAR)

    assert sonuc == []
    assert saglayici.son_kaynak == "unavailable"


async def test_kota_dolduysa_yahoo_hic_cagrilmaz(monkeypatch):
    """Kota korumasi: tavan asildiysa istek ve simule fiyat uretilmez."""
    from app.config import settings

    monkeypatch.setattr(settings, "market_api_daily_quota", 100)
    cagrilar = _yahoo_taklit(monkeypatch, fiyatlar={"THYAO": 1.0})
    saglayici = ApiMarketProvider(kota_deposu=SahteKotaDeposu(kullanilan=100))

    sonuc = await saglayici.next_prices(VARLIKLAR)

    assert cagrilar == [], "kota dolduysa Yahoo'ya istek atilmamali"
    assert saglayici.son_kaynak == "unavailable"
    assert sonuc == []


async def test_kota_sayacina_TICKER_SAYISI_islenir(monkeypatch):
    """KRITIK: `yf.download` tek istek DEGILDIR - her ticker ayri HTTP istegi.

    Sayac tick basina `1` islerse `market_api_usage` gercegin ~16'da birini
    gosterir ve `MARKET_API_DAILY_QUOTA` tavani hicbir zaman tetiklenmez.
    """
    _yahoo_taklit(monkeypatch, fiyatlar={"THYAO": 301.25, "BTC": 64227.97})
    depo = SahteKotaDeposu()

    await ApiMarketProvider(kota_deposu=depo).next_prices(VARLIKLAR)

    # THYAO.IS + BTC-USD = 2 istek
    assert depo.kaydedilen == 2


async def test_turetilmis_varligin_kur_istegi_de_sayilir(monkeypatch):
    """GRAM_ALTIN icin GC=F'nin YANI SIRA USDTRY=X de cekilir: 2 istek."""
    _yahoo_taklit(monkeypatch, fiyatlar={"GRAM_ALTIN": 6864.63})
    depo = SahteKotaDeposu()
    varliklar = [
        {"asset_id": 7, "symbol": "GRAM_ALTIN", "current_price": 6800.0, "sim_volatility": 0.008}
    ]

    await ApiMarketProvider(kota_deposu=depo).next_prices(varliklar)

    assert depo.kaydedilen == 2


async def test_hata_durumunda_da_gercek_istek_sayisi_islenir(monkeypatch):
    """Istekler zaten yapildi; hata aldik diye kotadan dusulmemeleri olmaz."""
    _yahoo_taklit(monkeypatch, hata=TimeoutError("yahoo yanit vermedi"))
    depo = SahteKotaDeposu()

    await ApiMarketProvider(kota_deposu=depo).next_prices(VARLIKLAR)

    assert depo.kaydedilen == 2


async def test_desteklenmeyen_varlik_yahoo_ya_sorulmaz(monkeypatch):
    """Yahoo'da karsiligi olmayan sembol (orn. tahvil) istege dahil edilmez."""
    cagrilar = _yahoo_taklit(monkeypatch, fiyatlar={"THYAO": 301.25})
    varliklar = VARLIKLAR + [
        {"asset_id": 99, "symbol": "TR10Y", "current_price": 100.0, "sim_volatility": 0.002}
    ]

    await ApiMarketProvider(kota_deposu=SahteKotaDeposu()).next_prices(varliklar)

    assert "TR10Y" not in cagrilar[0]


async def test_hicbir_varlik_desteklenmiyorsa_son_fiyatlar_korunur(monkeypatch):
    cagrilar = _yahoo_taklit(monkeypatch, fiyatlar={})
    varliklar = [
        {"asset_id": 99, "symbol": "TR10Y", "current_price": 100.0, "sim_volatility": 0.002}
    ]

    saglayici = ApiMarketProvider(kota_deposu=SahteKotaDeposu())
    sonuc = await saglayici.next_prices(varliklar)

    assert cagrilar == []
    assert saglayici.son_kaynak == "unavailable"
    assert sonuc == []


async def test_bellek_ici_depo_kota_sayacini_gercekten_tutar():
    """Yedek katmanda tavan YOK OLMAMALI.

    DB'ye ulasilamadiginda repository katmani bellek ici yedege duser ama
    `MARKET_DATA_PROVIDER=api` ise Yahoo cagrilari devam eder. Sayac burada
    sabit `0` donerse gunluk tavan tam da en cok gerektigi anda devre disi
    kalir - yani kota korumasi sessizce kaybolur.
    """
    from app.repositories.in_memory import InMemoryMarketRepository, reset_data

    reset_data()
    depo = InMemoryMarketRepository()

    assert await depo.get_api_usage_today() == 0

    await depo.record_api_usage(16)
    await depo.record_api_usage(16)

    assert await depo.get_api_usage_today() == 32

    reset_data()
    assert await depo.get_api_usage_today() == 0


async def test_kota_sayaci_okunamazsa_cagri_yine_de_yapilir(monkeypatch):
    """Sayac bir yan kayittir; okunamamasi fiyat cekmeyi engellememeli."""

    class BozukDepo:
        async def get_api_usage_today(self):
            raise RuntimeError("tablo yok")

        async def record_api_usage(self, calls=1):
            raise RuntimeError("tablo yok")

    cagrilar = _yahoo_taklit(monkeypatch, fiyatlar={"THYAO": 301.25, "BTC": 64227.97})
    saglayici = ApiMarketProvider(kota_deposu=BozukDepo())

    sonuc = await saglayici.next_prices(VARLIKLAR)

    assert cagrilar, "sayac hatasi cagriyi engellememeli"
    assert saglayici.son_kaynak == "api"
    assert len(sonuc) == 2


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

        sayi = await price_tick(SimulatedMarketProvider(seed=11), write_live=False)

        assert sayi > 0
        assert (await repository.get_quote("THYAO"))["price"] != onceki


@pytest.mark.db
async def test_fiyat_tick_i_gunluk_degisimi_yeniden_hesaplar():
    """Yoksa yuzde seed degerinde donar (mimari v4 bolum 8.2)."""
    async with _fiyatlari_koru():
        from app.repositories.deps import get_market_repository

        repository = get_market_repository()
        onceki = (await repository.get_quote("BTC"))["daily_change_pct"]

        await price_tick(SimulatedMarketProvider(seed=13), write_live=False)

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
