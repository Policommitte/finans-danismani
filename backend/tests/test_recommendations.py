"""Otonom oneri motoru testleri (AUT / D-02, D-07).

Kural mantiginin cogu saf fonksiyonlarda oldugu icin dogrudan test edilir;
yasam dongusu bellek ici repository uzerinden kosar.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import BusinessRuleError
from app.core.quantity import adet_gecerli_mi, adet_yuvarla
from app.repositories import in_memory
from app.repositories.in_memory import InMemoryRecommendationRepository, reset_data
from app.services import recommendation as service
from app.signals import sinyal_uret

SIMDI = datetime(2026, 8, 27, 11, 0, tzinfo=timezone.utc)


def _varlik(**kw):
    taban = {
        "asset_id": 1,
        "symbol": "THYAO",
        "asset_class": "STOCK",
        "current_price": 300.0,
        "daily_change_pct": 0.0,
        "weekly_change_pct": 0.0,
        "yearly_change_pct": 0.0,
        "price_updated_at": SIMDI,
    }
    return {**taban, **kw}


def _kullanici(**kw):
    taban = {
        "user_id": 1,
        "portfolio_id": 1,
        "risk_tolerance": "MEDIUM",
        "available_balance": 50_000.0,
        "portfolio_value_try": 100_000.0,
        "per_order_limit_try": 5_000.0,
        "daily_limit_try": 15_000.0,
        "allowed_asset_classes": [],
        "max_daily_recommendations": 3,
        "autonomous_enabled": True,
    }
    return {**taban, **kw}


def _sinyal(**kw):
    taban = {
        "id": 1,
        "asset_id": 1,
        "asset_class": "STOCK",
        "direction": "BUY",
        "confidence": 0.75,
        "rule_code": "PULLBACK_IN_UPTREND",
        "rationale": ["Yillik trend yukari", "Haftalik geri cekilme"],
        "evidence": {},
        "reference_price": 300.0,
        "expires_at": SIMDI + timedelta(hours=4),
        "engine_version": "scan-v1",
    }
    return {**taban, **kw}


# ---------------------------------------------------------------- sinyal


def test_endeks_ve_bayat_fiyat_elenir():
    sinyaller = sinyal_uret(
        [
            _varlik(asset_id=1, asset_class="INDEX", daily_change_pct=-9.0),
            _varlik(
                asset_id=2,
                symbol="BIMAS",
                daily_change_pct=-8.0,
                price_updated_at=SIMDI - timedelta(hours=2),
            ),
            _varlik(asset_id=3, symbol="SASA", daily_change_pct=-7.0),
        ],
        now=SIMDI,
        threshold=0.55,
        ttl_minutes=240,
    )
    # Endeks islem disi, BIMAS'in fiyati bayat -> yalnizca SASA kalir.
    assert [s["symbol"] for s in sinyaller] == ["SASA"]


def test_bayat_fiyat_elemesi_asla_gerceklesmeyecek_emri_onler():
    """Fiyat beslemesi olmayan varliga oneri uretilirse emir PENDING asili kalir."""
    sinyaller = sinyal_uret(
        [
            _varlik(
                symbol="TUPRS",
                daily_change_pct=-9.0,
                price_updated_at=SIMDI - timedelta(minutes=45),
            )
        ],
        now=SIMDI,
        threshold=0.55,
        ttl_minutes=240,
        max_staleness_minutes=30,
    )
    assert sinyaller == []


def test_esik_alti_sinyal_yazilir_ama_yayinlanmaz():
    """D-02: 'Guven esigi gecildi mi? -> hayir -> Sinyali ic kayda al'."""
    sinyaller = sinyal_uret(
        [_varlik(daily_change_pct=-5.1)], now=SIMDI, threshold=0.90, ttl_minutes=240
    )
    assert len(sinyaller) == 1
    assert sinyaller[0]["published"] is False
    assert "esik" in sinyaller[0]["suppressed_reason"]


def test_tek_varliga_tek_sinyal_uretilir():
    """FR-AUT-001: her oneri tek enstruman ve tek yon icerir."""
    sinyaller = sinyal_uret(
        [_varlik(daily_change_pct=-6.0, weekly_change_pct=15.0, yearly_change_pct=30.0)],
        now=SIMDI,
        threshold=0.0,
        ttl_minutes=240,
    )
    assert len(sinyaller) == 1


# ------------------------------------------------------- kisisellestirme


def test_dusuk_risk_profiline_kripto_onerilmez():
    yuk, gerekce = service.kisisellestir(
        _sinyal(asset_class="CRYPTO"),
        _kullanici(risk_tolerance="LOW"),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None
    assert "LOW" in gerekce


def test_profil_asgari_guveni_uygulanir():
    """Ayni sinyal MEDIUM'da gecer, LOW'da elenir."""
    sinyal = _sinyal(confidence=0.62)
    kabul, _ = service.kisisellestir(
        sinyal,
        _kullanici(risk_tolerance="MEDIUM"),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    ret, gerekce = service.kisisellestir(
        sinyal,
        _kullanici(risk_tolerance="LOW"),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert kabul is not None
    assert ret is None and "0.7" in gerekce


def test_gunluk_oneri_limiti(monkeypatch):
    """BR-AUT-03: gunde en fazla 3 oneri."""
    yuk, gerekce = service.kisisellestir(
        _sinyal(), _kullanici(), {}, gunluk_adet=3, gunluk_tutar=0, acik_varliklar=set()
    )
    assert yuk is None and "gunluk oneri limiti" in gerekce


def test_izinli_olmayan_sinif_elenir():
    yuk, gerekce = service.kisisellestir(
        _sinyal(asset_class="CRYPTO"),
        _kullanici(allowed_asset_classes=["STOCK"]),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None and "izinli siniflari" in gerekce


def test_elde_olmayan_varlik_icin_satis_onerilmez():
    yuk, gerekce = service.kisisellestir(
        _sinyal(direction="SELL"),
        _kullanici(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None and "pozisyonu yok" in gerekce


def test_satis_onerisi_pozisyonun_bir_bolumunu_kapsar():
    yuk, _ = service.kisisellestir(
        _sinyal(direction="SELL"),
        _kullanici(),
        {1: 100.0},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is not None
    assert 0 < yuk["quantity"] < 100.0


def test_alim_adedi_tek_islem_limitini_asmaz():
    yuk, _ = service.kisisellestir(
        _sinyal(),
        _kullanici(per_order_limit_try=1_000.0),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is not None
    assert yuk["estimated_amount"] <= 1_000.0


def test_nakit_yetersizse_oneri_uretilmez():
    yuk, gerekce = service.kisisellestir(
        _sinyal(),
        _kullanici(available_balance=10.0, portfolio_value_try=0.0),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None and gerekce is not None


def test_ayni_varliga_ikinci_oneri_uretilmez():
    yuk, gerekce = service.kisisellestir(
        _sinyal(),
        _kullanici(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar={1},
    )
    assert yuk is None and "acik bir oneri" in gerekce


def test_oneri_karti_zorunlu_alanlari_tasir():
    """FR-AUT-003 + BR-AUT-01: gerekce, kaynak ve risk notu olmadan kart olmaz."""
    yuk, _ = service.kisisellestir(
        _sinyal(), _kullanici(), {}, gunluk_adet=0, gunluk_tutar=0, acik_varliklar=set()
    )
    assert yuk["rationale"] and len(yuk["rationale"]) <= 5
    assert yuk["risk_note"]
    assert yuk["sources"]
    assert yuk["personalization"]["risk_profile"] == "MEDIUM"


# ------------------------------------------------------------------ adet


@pytest.mark.parametrize(
    "sinif, fiyat, beklenen",
    [
        ("USA_STOCK", 4246.92, 1.0),  # INTC: 5.000 TL -> 1,17 -> 1 adet
        ("USA_STOCK", 57222.76, 0.0),  # LLY: tek adet bile butceyi asiyor
        ("STOCK", 305.00, 16.0),  # THYAO
        ("ETF", 1200.00, 4.0),
        ("CRYPTO", 3822612.11, 0.001308),  # BTC: kusurat sart
        ("GOLD", 7176.87, 0.6966),  # gram altin bolunebilir
    ],
)
def test_adet_sinifa_gore_yuvarlanir(sinif, fiyat, beklenen):
    """Bolunebilirlik FIYATA degil SINIFA baglidir."""
    assert adet_yuvarla(5000 / fiyat, sinif) == beklenen


def test_hisse_kusuratli_alinamaz():
    assert adet_gecerli_mi(1.5, "STOCK") is False
    assert adet_gecerli_mi(2.0, "STOCK") is True
    assert adet_gecerli_mi(0.0013, "CRYPTO") is True


def test_tek_adet_butceye_sigmiyorsa_oneri_uretilmez():
    """LLY 57.222 TL; tek islem limiti 5.000 TL -> kusuratli oneri YERINE hic oneri."""
    yuk, gerekce = service.kisisellestir(
        _sinyal(asset_class="USA_STOCK", reference_price=57_222.76),
        _kullanici(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None
    assert "bir adede yetmiyor" in gerekce


def test_hisse_onerisi_tam_adet_uretir():
    yuk, _ = service.kisisellestir(
        _sinyal(asset_class="USA_STOCK", reference_price=4_246.92),
        _kullanici(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is not None
    assert float(yuk["quantity"]).is_integer()


# ------------------------------------------------------------- sessiz saat


@pytest.mark.parametrize(
    "saat_utc, beklenen",
    [(20, True), (2, True), (9, False), (15, False)],
)
def test_sessiz_saat(saat_utc, beklenen):
    """FR-AUT-010: 22:00-08:00 (Istanbul) arasi oneri uretilmez."""
    an = datetime(2026, 8, 27, saat_utc, 0, tzinfo=timezone.utc)
    assert service.sessiz_saat_mi(an) is beklenen


# --------------------------------------------------------- yasam dongusu


@pytest.fixture
def repo():
    reset_data()
    return InMemoryRecommendationRepository()


async def _oneri_olustur(repo, **kw):
    yuk = {
        "signal_id": None,
        "user_id": 1,
        "portfolio_id": 1,
        "asset_id": 1,
        "side": "BUY",
        "quantity": 2.0,
        "reference_price": 300.0,
        "estimated_amount": 600.0,
        "confidence": 0.75,
        "rationale": ["gerekce"],
        "risk_note": "not",
        "sources": [{"label": "k"}],
        "personalization": {},
        "expires_at": (SIMDI + timedelta(hours=4)).isoformat(),
    }
    return await repo.create_recommendation({**yuk, **kw})


@pytest.mark.asyncio
async def test_oneri_olusunca_bildirim_kuyruga_girer(repo):
    """FR-AUT-006: oneri uygulama ici ve e-posta ile iletilir."""
    await _oneri_olustur(repo)
    kuyruk = [
        n for n in in_memory._NOTIFICATION_OUTBOX if n["event_type"] == "RECOMMENDATION_CREATED"
    ]
    assert len(kuyruk) == 1
    assert kuyruk[0]["payload"]["side"] == "BUY"


@pytest.mark.asyncio
async def test_gerekceli_ret_ve_gecersiz_gerekce(repo):
    oneri = await _oneri_olustur(repo)
    reddedilen = await repo.reject(1, oneri["id"], "TOO_RISKY")
    assert reddedilen["status"] == "REJECTED"
    assert reddedilen["rejection_reason"] == "TOO_RISKY"

    with pytest.raises(BusinessRuleError):
        await service.oneri_reddet(1, oneri["id"], "SACMA_GEREKCE")


@pytest.mark.asyncio
async def test_reddedilen_oneri_tekrar_reddedilemez(repo):
    oneri = await _oneri_olustur(repo)
    await repo.reject(1, oneri["id"], "NO_CASH")
    with pytest.raises(BusinessRuleError):
        await repo.reject(1, oneri["id"], "NO_CASH")


@pytest.mark.asyncio
async def test_bir_oneri_en_fazla_bir_emir_dogurur(repo):
    """BR-AUT-08."""
    oneri = await _oneri_olustur(repo)
    await repo.attach_order(1, oneri["id"], 42)
    with pytest.raises(BusinessRuleError):
        await repo.attach_order(1, oneri["id"], 43)


@pytest.mark.asyncio
async def test_ttl_dolan_oneri_kapanir_ve_onaylanamaz(repo):
    """BR-AUT-04: sure dolduktan sonra onaylanamaz."""
    gecmis = datetime.now(timezone.utc) - timedelta(minutes=1)
    await _oneri_olustur(repo, expires_at=gecmis.isoformat())
    assert await repo.expire_due(datetime.now(timezone.utc)) == 1
    assert (await repo.list_recommendations(1))[0]["status"] == "EXPIRED"


@pytest.mark.asyncio
async def test_kill_switch_bekleyen_onerileri_durdurur(repo):
    """FR-AUT-034."""
    await _oneri_olustur(repo)
    await repo.set_kill_switch(True, "piyasa anormalligi", "admin")
    assert await repo.kill_switch_active() is True
    assert await repo.halt_open("piyasa anormalligi") == 1
    assert (await repo.list_recommendations(1))[0]["status"] == "HALTED"


@pytest.mark.asyncio
async def test_kart_acilinca_goruntulendi_olur(repo):
    oneri = await _oneri_olustur(repo)
    guncel = await repo.mark_viewed(1, oneri["id"])
    assert guncel["status"] == "VIEWED"
    assert guncel["viewed_at"] is not None


@pytest.mark.asyncio
async def test_kapali_otonom_akista_kullanici_taranmaz(repo):
    """FR-AUT-026: kullanici otonom akisi tamamen kapatabilir."""
    await repo.upsert_limits(1, {"autonomous_enabled": False})
    kullanicilar = await repo.autonomous_users()
    assert all(u["user_id"] != 1 for u in kullanicilar)
