"""Otonom oneri motoru testleri (AUT / D-02, D-07).

Kural mantiginin cogu saf fonksiyonlarda oldugu icin dogrudan test edilir;
yasam dongusu bellek ici repository uzerinden kosar.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import BusinessRuleError
from app.core.quantity import is_valid_quantity, round_quantity
from app.repositories import in_memory
from app.repositories.in_memory import InMemoryRecommendationRepository, reset_data
from app.services import recommendation as service
from app.signals import generate_signals

SIMDI = datetime(2026, 8, 27, 11, 0, tzinfo=timezone.utc)


def _asset(**kw):
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


def _user(**kw):
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


def _signal(**kw):
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


def test_index_and_stale_price_filtered_out():
    sinyaller = generate_signals(
        [
            _asset(asset_id=1, asset_class="INDEX", daily_change_pct=-9.0),
            _asset(asset_id=4, asset_class="BOND", symbol="US10Y", daily_change_pct=-9.0),
            _asset(
                asset_id=2,
                symbol="BIMAS",
                daily_change_pct=-8.0,
                price_updated_at=SIMDI - timedelta(hours=2),
            ),
            _asset(asset_id=3, symbol="SASA", daily_change_pct=-7.0),
        ],
        now=SIMDI,
        threshold=0.55,
        ttl_minutes=240,
    )
    # Endeks ve tahvil-getiri gostergesi islem disi, BIMAS'in fiyati bayat.
    assert [s["symbol"] for s in sinyaller] == ["SASA"]


def test_stale_price_filter_prevents_never_filling_order():
    """Fiyat beslemesi olmayan varliga oneri uretilirse emir PENDING asili kalir."""
    sinyaller = generate_signals(
        [
            _asset(
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


def test_below_threshold_signal_stored_but_not_published():
    """D-02: 'Guven esigi gecildi mi? -> hayir -> Sinyali ic kayda al'."""
    sinyaller = generate_signals(
        [_asset(daily_change_pct=-5.1)], now=SIMDI, threshold=0.90, ttl_minutes=240
    )
    assert len(sinyaller) == 1
    assert sinyaller[0]["published"] is False
    assert "esik" in sinyaller[0]["suppressed_reason"]


def test_one_signal_per_asset():
    """FR-AUT-001: her oneri tek enstruman ve tek yon icerir."""
    sinyaller = generate_signals(
        [_asset(daily_change_pct=-6.0, weekly_change_pct=15.0, yearly_change_pct=30.0)],
        now=SIMDI,
        threshold=0.0,
        ttl_minutes=240,
    )
    assert len(sinyaller) == 1


# ------------------------------------------------------- kisisellestirme


def test_no_crypto_recommended_for_low_risk_profile():
    yuk, gerekce = service.personalize(
        _signal(asset_class="CRYPTO"),
        _user(risk_tolerance="LOW"),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None
    assert "LOW" in gerekce


def test_profile_minimum_confidence_applied():
    """Ayni sinyal MEDIUM'da gecer, LOW'da elenir."""
    sinyal = _signal(confidence=0.62)
    kabul, _ = service.personalize(
        sinyal,
        _user(risk_tolerance="MEDIUM"),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    ret, gerekce = service.personalize(
        sinyal,
        _user(risk_tolerance="LOW"),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert kabul is not None
    assert ret is None and "0.7" in gerekce


def test_daily_recommendation_limit(monkeypatch):
    """BR-AUT-03: gunde en fazla 3 oneri."""
    yuk, gerekce = service.personalize(
        _signal(), _user(), {}, gunluk_adet=3, gunluk_tutar=0, acik_varliklar=set()
    )
    assert yuk is None and "gunluk oneri limiti" in gerekce


def test_disallowed_asset_class_filtered_out():
    yuk, gerekce = service.personalize(
        _signal(asset_class="CRYPTO"),
        _user(allowed_asset_classes=["STOCK"]),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None and "izinli siniflari" in gerekce


def test_no_sell_recommended_for_unowned_asset():
    yuk, gerekce = service.personalize(
        _signal(direction="SELL"),
        _user(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None and "pozisyonu yok" in gerekce


def test_sell_recommendation_covers_part_of_position():
    yuk, _ = service.personalize(
        _signal(direction="SELL"),
        _user(),
        {1: 100.0},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is not None
    assert 0 < yuk["quantity"] < 100.0


def test_buy_quantity_does_not_exceed_single_trade_limit():
    yuk, _ = service.personalize(
        _signal(),
        _user(per_order_limit_try=1_000.0),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is not None
    assert yuk["estimated_amount"] <= 1_000.0


def test_no_recommendation_when_cash_insufficient():
    yuk, gerekce = service.personalize(
        _signal(),
        _user(available_balance=10.0, portfolio_value_try=0.0),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None and gerekce is not None


def test_no_second_recommendation_for_same_asset():
    yuk, gerekce = service.personalize(
        _signal(),
        _user(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar={1},
    )
    assert yuk is None and "acik bir oneri" in gerekce


def test_recommendation_card_carries_required_fields():
    """FR-AUT-003 + BR-AUT-01: gerekce, kaynak ve risk notu olmadan kart olmaz."""
    yuk, _ = service.personalize(
        _signal(), _user(), {}, gunluk_adet=0, gunluk_tutar=0, acik_varliklar=set()
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
        ("GOLD", 1000.00, 5.0),  # gram altin TAM gram
        ("COMMODITY", 4213.24, 1.0),  # emtia tam adet
        ("CRYPTO", 3822612.11, 0.001308),  # kripto: tek kusurat istisnasi
        ("FOREX", 41.20, 121.25),  # doviz: 0,25'in katlari
    ],
)
def test_quantity_rounded_by_asset_class(sinif, fiyat, beklenen):
    """Bolunebilirlik FIYATA degil SINIFA baglidir."""
    assert round_quantity(5000 / fiyat, sinif) == beklenen


def test_fractions_only_valid_for_crypto_and_forex():
    """Doviz disinda kusurat yok; doviz de yalnizca 0,25'in katlari."""
    assert is_valid_quantity(1.5, "STOCK") is False
    assert is_valid_quantity(2.0, "STOCK") is True
    assert is_valid_quantity(0.3871, "GOLD") is False  # gram altin tam gram
    assert is_valid_quantity(1.1867, "COMMODITY") is False  # emtia tam adet
    assert is_valid_quantity(0.0013, "CRYPTO") is True  # tek istisna
    assert is_valid_quantity(0.75, "FOREX") is True
    assert is_valid_quantity(0.30, "FOREX") is False


def test_no_recommendation_when_single_unit_exceeds_budget():
    """LLY 57.222 TL; tek islem limiti 5.000 TL -> kusuratli oneri YERINE hic oneri."""
    yuk, gerekce = service.personalize(
        _signal(asset_class="USA_STOCK", reference_price=57_222.76),
        _user(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is None
    assert "bir adede yetmiyor" in gerekce


def test_stock_recommendation_produces_whole_quantity():
    yuk, _ = service.personalize(
        _signal(asset_class="USA_STOCK", reference_price=4_246.92),
        _user(),
        {},
        gunluk_adet=0,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is not None
    assert float(yuk["quantity"]).is_integer()


def test_warning_text_carries_no_simulation_sentence():
    """Urun karari: kart uyarisi yalnizca yatirim tavsiyesi ibaresini tasir."""
    assert "yatirim tavsiyesi degildir" in service.SPK_UYARISI
    assert "simulasyon" not in service.SPK_UYARISI.lower()


# ------------------------------------------------------------- sessiz saat


@pytest.mark.parametrize(
    "saat_utc, beklenen",
    [(20, True), (2, True), (9, False), (15, False)],
)
def test_quiet_hours(saat_utc, beklenen):
    """FR-AUT-010: 22:00-08:00 (Istanbul) arasi oneri uretilmez."""
    an = datetime(2026, 8, 27, saat_utc, 0, tzinfo=timezone.utc)
    assert service.is_quiet_hour(an) is beklenen


def test_daily_limit_defaults_to_four():
    """Urun karari: gunde 3 degil 4 oneri."""
    assert InMemoryRecommendationRepository.VARSAYILAN_LIMITLER["max_daily_recommendations"] == 4
    yuk, gerekce = service.personalize(
        _signal(),
        _user(max_daily_recommendations=4),
        {},
        gunluk_adet=3,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert yuk is not None, "3 oneri verilmisken dorduncusu hala uretilebilmeli"
    ret, _ = service.personalize(
        _signal(),
        _user(max_daily_recommendations=4),
        {},
        gunluk_adet=4,
        gunluk_tutar=0,
        acik_varliklar=set(),
    )
    assert ret is None


# --------------------------------------------------------- yasam dongusu


@pytest.fixture
def repo():
    reset_data()
    return InMemoryRecommendationRepository()


async def _create_recommendation(repo, **kw):
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
        "sources": [{"label": "Kural: test", "kind": "rule", "url": None}],
        "personalization": {},
        "expires_at": (SIMDI + timedelta(hours=4)).isoformat(),
    }
    return await repo.create_recommendation({**yuk, **kw})


@pytest.mark.asyncio
async def test_notification_queued_when_recommendation_created(repo):
    """FR-AUT-006: oneri uygulama ici ve e-posta ile iletilir."""
    await _create_recommendation(repo)
    kuyruk = [
        n for n in in_memory._NOTIFICATION_OUTBOX if n["event_type"] == "RECOMMENDATION_CREATED"
    ]
    assert len(kuyruk) == 1
    assert kuyruk[0]["payload"]["side"] == "BUY"


@pytest.mark.asyncio
async def test_rejection_with_reason_and_invalid_reason(repo):
    oneri = await _create_recommendation(repo)
    reddedilen = await repo.reject(1, oneri["id"], "TOO_RISKY")
    assert reddedilen["status"] == "REJECTED"
    assert reddedilen["rejection_reason"] == "TOO_RISKY"

    with pytest.raises(BusinessRuleError):
        await service.reject_recommendation(1, oneri["id"], "SACMA_GEREKCE")


@pytest.mark.asyncio
async def test_rejected_recommendation_cannot_be_rejected_again(repo):
    oneri = await _create_recommendation(repo)
    await repo.reject(1, oneri["id"], "NO_CASH")
    with pytest.raises(BusinessRuleError):
        await repo.reject(1, oneri["id"], "NO_CASH")


@pytest.mark.asyncio
async def test_one_recommendation_yields_at_most_one_order(repo):
    """BR-AUT-08."""
    oneri = await _create_recommendation(repo)
    await repo.attach_order(1, oneri["id"], 42)
    with pytest.raises(BusinessRuleError):
        await repo.attach_order(1, oneri["id"], 43)


@pytest.mark.asyncio
async def test_ttl_expired_recommendation_closes_and_cannot_be_approved(repo):
    """BR-AUT-04: sure dolduktan sonra onaylanamaz."""
    gecmis = datetime.now(timezone.utc) - timedelta(minutes=1)
    await _create_recommendation(repo, expires_at=gecmis.isoformat())
    assert await repo.expire_due(datetime.now(timezone.utc)) == 1
    assert (await repo.list_recommendations(1))[0]["status"] == "EXPIRED"


@pytest.mark.asyncio
async def test_kill_switch_halts_pending_recommendations(repo):
    """FR-AUT-034."""
    await _create_recommendation(repo)
    await repo.set_kill_switch(True, "piyasa anormalligi", "admin")
    assert await repo.kill_switch_active() is True
    assert await repo.halt_open("piyasa anormalligi") == 1
    assert (await repo.list_recommendations(1))[0]["status"] == "HALTED"


@pytest.mark.asyncio
async def test_expired_recommendation_also_closed_on_read(repo, monkeypatch):
    """Fiyat gorevi durmus olsa bile liste dogruyu gostermeli.

    Gecmiste suresi dolmus oneriler "Bekleyen" sekmesinde acikmis gibi
    duruyordu; TTL kapanisi yalnizca tick'te calisiyordu.
    """
    gecmis = datetime.now(timezone.utc) - timedelta(minutes=5)
    await _create_recommendation(repo, expires_at=gecmis.isoformat())
    monkeypatch.setattr("app.services.recommendation.get_recommendation_repository", lambda: repo)

    liste = await service.list_recommendations(1)

    assert [k.status for k in liste.items] == ["EXPIRED"]


@pytest.mark.asyncio
async def test_opening_card_marks_viewed(repo):
    oneri = await _create_recommendation(repo)
    guncel = await repo.mark_viewed(1, oneri["id"])
    assert guncel["status"] == "VIEWED"
    assert guncel["viewed_at"] is not None


@pytest.mark.asyncio
async def test_user_not_scanned_when_autonomous_flow_disabled(repo):
    """FR-AUT-026: kullanici otonom akisi tamamen kapatabilir."""
    await repo.upsert_limits(1, {"autonomous_enabled": False})
    kullanicilar = await repo.autonomous_users()
    assert all(u["user_id"] != 1 for u in kullanicilar)
