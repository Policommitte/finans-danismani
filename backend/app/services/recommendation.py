"""Otonom oneri servisi - D-02'nin POLIFIN kulvari.

AKIS (D-02 ile birebir)
    tarama verisi -> sinyal -> guven esigi -> kisisellestirme -> profil uyumu
    -> oneri karti -> (bildirim) -> TTL -> karar -> onay ekrani -> emir

IKI FILTRE SUNUCU TARAFINDADIR
    "Guven esigi" ve "Profil uyumlu mu?" kararlari burada verilir; elenen
    sinyal istemciye GONDERILIP orada gizlenmez (D-02 gelistirme notu 1).
    Kullaniciya ulasmayan sinyalin gerekcesi `signals.suppressed_reason` ve
    denetim kaydinda durur.

KARAR MANTIGI SAF FONKSIYONDADIR
    `personalize()` I/O yapmaz; ayni girdi her zaman ayni ciktiyi verir.
    Boylece FR-AUT-012 ("neden bana geldi?") gercek bir cevap dondurebilir ve
    kurallar testle sabitlenebilir.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.config import settings
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.quantity import round_quantity
from app.repositories.deps import get_recommendation_repository
from app.schemas.recommendation import (
    RET_GEREKCELERI,
    Recommendation,
    RecommendationListResponse,
)
from app.services import trading as trading_service
from app.signals import generate_signals, rule_name

logger = logging.getLogger(__name__)

#: BR-AUT-01 / FR-AUT-003: her oneri kartiyla BIRLIKTE tasinir.
#: Metin sunucudan gider; istemcinin kendi uyarisini uydurmasi beklenmez.
SPK_UYARISI = (
    "Bu icerik yatirim tavsiyesi degildir. Burada yer alan bilgiler genel "
    "nitelikte olup kisisel yatirim hedeflerinize uygun olmayabilir."
)

#: Risk profiline gore izin verilmeyen varlik siniflari ve asgari guven.
#: Dusuk toleransli kullaniciya kripto onerilmez; ayrica ayni sinyalin
#: gecmesi icin daha yuksek guven aranir.
PROFIL_KURALLARI: dict[str, dict] = {
    "LOW": {"yasak_siniflar": {"CRYPTO"}, "asgari_guven": 0.70},
    "MEDIUM": {"yasak_siniflar": set(), "asgari_guven": 0.60},
    "HIGH": {"yasak_siniflar": set(), "asgari_guven": 0.55},
}
VARSAYILAN_PROFIL = "MEDIUM"


def is_quiet_hour(now: datetime) -> bool:
    """FR-AUT-010: sessiz saatlerde oneri URETILMEZ.

    Uretmemek, uretip bildirimi kuyruga almaktan bilincli olarak tercih
    edildi: sabaha kadar bekleyen bir onerinin TTL'i zaten dolar ve kullanici
    acildiginda "suresi dolmus" bir kart gorurdu.
    """
    yerel = now.astimezone(ZoneInfo(settings.market_day_timezone))
    bas, bit = settings.quiet_hours_start, settings.quiet_hours_end
    if bas == bit:
        return False
    if bas < bit:
        return bas <= yerel.hour < bit
    # Gece yarisini asan aralik (orn. 22:00-08:00)
    return yerel.hour >= bas or yerel.hour < bit


def personalize(
    signal: dict,
    user: dict,
    holdings: dict[int, float],
    *,
    gunluk_adet: int,
    gunluk_tutar: float,
    acik_varliklar: set[int],
) -> tuple[dict | None, str | None]:
    """Sinyali bir kullaniciya uyarlar. SAF fonksiyon.

    Doner: (oneri_yuku, None) ya da (None, eleme_gerekcesi).

    FR-AUT-002 girdileri: risk profili, mevcut portfoy ve agirliklar,
    kullanici limitleri, nakit bakiye, izinli enstruman siniflari.
    """
    asset_id = int(signal["asset_id"])
    sinif = (signal.get("asset_class") or "").upper()
    fiyat = float(signal["reference_price"])

    # --- gunluk ust sinirlar (BR-AUT-03) ---
    if gunluk_adet >= int(user["max_daily_recommendations"]):
        return None, "gunluk oneri limiti dolu"
    if gunluk_tutar >= float(user["daily_limit_try"]):
        return None, "gunluk tutar limiti dolu"

    # --- ayni varliga acik oneri varken ikincisi uretilmez ---
    if asset_id in acik_varliklar:
        return None, "bu varlik icin zaten acik bir oneri var"

    # --- izinli enstruman siniflari (FR-PRF-014) ---
    izinli = list(user.get("allowed_asset_classes") or [])
    if izinli and sinif not in {c.upper() for c in izinli}:
        return None, f"{sinif} kullanicinin izinli siniflari disinda"

    # --- profil uyumu (D-02 "Profil uyumlu mu?") ---
    profil = (user.get("risk_tolerance") or VARSAYILAN_PROFIL).upper()
    kural = PROFIL_KURALLARI.get(profil, PROFIL_KURALLARI[VARSAYILAN_PROFIL])
    if sinif in kural["yasak_siniflar"]:
        return None, f"{sinif} {profil} risk profiline uygun degil"
    if float(signal["confidence"]) < kural["asgari_guven"]:
        return None, (
            f"guven {signal['confidence']} < {profil} profili icin gereken "
            f"{kural['asgari_guven']}"
        )

    elde = float(holdings.get(asset_id, 0.0))

    if signal["direction"] == "SELL":
        # Elde olmayan varlik satilamaz - oneri de edilemez.
        if elde <= 0:
            return None, "kullanicinin bu varlikta pozisyonu yok"
        # Pozisyonun bir bolumu onerilir; tamamini kapatmak otonom bir
        # akisin tek basina verecegi karar degildir.
        adet = round_quantity(elde * 0.30, sinif)
        if adet <= 0:
            return None, "onerilebilecek anlamli bir satis adedi yok"
        tutar = adet * fiyat
    else:
        nakit = float(user["available_balance"])
        portfoy = float(user.get("portfolio_value_try") or 0.0)
        # Pozisyon buyuklugu UC sinirin en kucugu: kullanicinin tek islem
        # limiti, portfoy yuzdesi ve eldeki nakit.
        tavan = min(
            float(user["per_order_limit_try"]),
            max(portfoy, nakit) * settings.recommendation_position_pct,
            nakit * 0.95,  # komisyon ve fiyat oynamasi icin pay birakilir
            float(user["daily_limit_try"]) - gunluk_tutar,
        )
        if tavan <= 0:
            return None, "kullanilabilir nakit ya da limit yetersiz"
        adet = round_quantity(tavan / fiyat, sinif)
        if adet <= 0:
            # Bolunmez bir enstrumanda tek adedin fiyati butceyi asiyor
            # (orn. tek islem limiti 5.000 TL iken LLY 57.222 TL). Kusuratli
            # hisse onermek yerine oneri HIC uretilmez.
            return None, (
                f"tek adet {fiyat:,.2f} TRY; kullanilabilir butce "
                f"{tavan:,.2f} TRY bir adede yetmiyor"
            )
        tutar = adet * fiyat

    return (
        {
            "signal_id": signal.get("id"),
            "user_id": int(user["user_id"]),
            "portfolio_id": int(user["portfolio_id"]),
            "asset_id": asset_id,
            "side": signal["direction"],
            "quantity": adet,
            "reference_price": fiyat,
            "estimated_amount": round(tutar, 2),
            "confidence": float(signal["confidence"]),
            "rationale": list(signal["rationale"])[:5],
            "risk_note": _risk_note(signal, profil),
            "sources": _sources(signal),
            "personalization": {
                "risk_profile": profil,
                "rule_code": signal["rule_code"],
                "rule_name": rule_name(signal["rule_code"]),
                "engine_version": signal.get("engine_version"),
                "holding_quantity": elde,
                "available_balance": float(user["available_balance"]),
                "per_order_limit_try": float(user["per_order_limit_try"]),
                "confidence_required": kural["asgari_guven"],
            },
            "expires_at": signal["expires_at"],
        },
        None,
    )


def _risk_note(signal: dict, profil: str) -> str:
    yon = "alim" if signal["direction"] == "BUY" else "satis"
    return (
        f"Bu {yon} onerisi \"{rule_name(signal['rule_code'])}\" kuralindan uretildi ve "
        f"{profil} risk profiline gore filtrelendi. Gecmis fiyat hareketi "
        f"gelecegi garanti etmez; fiyat ters yonde hareket edebilir."
    )


def _percent_text(value) -> str:
    try:
        sayi = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"%{sayi:+.1f}".replace(".", ",")


def _sources(signal: dict) -> list[dict]:
    """BR-AUT-01: kaynaksiz oneri gosterilemez."""
    kanit = signal.get("evidence") or {}
    return [
        {
            "label": f"Kural: {rule_name(signal['rule_code'])}",
            "kind": "rule",
            "url": None,
        },
        {
            # Yuzdeler TEK ONDALIGA yuvarlanir: "%-4.2006" gibi ham bir sayi
            # kaynak satirini okunmaz yapiyordu.
            "label": (
                "Piyasa verisi — "
                f"gunluk {_percent_text(kanit.get('daily_change_pct'))}, "
                f"haftalik {_percent_text(kanit.get('weekly_change_pct'))}, "
                f"yillik {_percent_text(kanit.get('yearly_change_pct'))}"
                f" (veri: {str(kanit.get('price_as_of', ''))[:16].replace('T', ' ')})"
            ),
            "kind": "market",
            "url": None,
        },
    ]


# =====================================================================
# Orkestrasyon (I/O)
# =====================================================================


async def generate_recommendations(now: datetime | None = None) -> dict:
    """Tam tur: tarama -> sinyal -> kisisellestirme -> oneri.

    Fiyat tick'inden cagrilir. Sayaclari doner; hicbir kosulda istisna
    firlatmaz - cagiran fiyat akisidir ve durmamalidir.
    """
    an = now or datetime.now(timezone.utc)
    repo = get_recommendation_repository()
    sayac = {"signals": 0, "published": 0, "recommendations": 0, "skipped": 0}

    if await repo.kill_switch_active():
        # FR-AUT-034: kill-switch aktifken YENI oneri uretilmez ve
        # bekleyenler kullaniciya "gecici olarak durduruldu" ile kapatilir.
        durdurulan = await repo.halt_open("kill-switch aktif")
        if durdurulan:
            await repo.log_audit(
                {
                    "event_type": "KILL_SWITCH_HALT",
                    "actor": "SYSTEM",
                    "reason": "kill-switch aktif",
                    "detail": {"halted": durdurulan},
                }
            )
        return {**sayac, "halted": durdurulan, "reason": "kill-switch"}

    if is_quiet_hour(an):
        return {**sayac, "reason": "sessiz saat"}

    assets = await repo.assets_for_scan()
    ham_sinyaller = generate_signals(
        assets,
        now=an,
        threshold=settings.signal_confidence_threshold,
        ttl_minutes=settings.recommendation_ttl_minutes,
    )
    sayac["signals"] = len(ham_sinyaller)
    if not ham_sinyaller:
        return sayac

    # Sinif bilgisi sinyalde tasinmaz (enstruman bazli tablo), kisisellestirme
    # icin gerekli - varlik listesinden eslestirilir.
    sinif_haritasi = {int(a["asset_id"]): a.get("asset_class") for a in assets}

    yayinlanan = await repo.save_signals(ham_sinyaller)
    sayac["published"] = len(yayinlanan)
    if not yayinlanan:
        return sayac

    # Kullanici listesi tick basina sinirlanir; siradakiler sonraki turda
    # islenir. Sinir olmadan ilk tur fiyat gorevini dakikalarca mesgul ediyordu.
    tum_kullanicilar = await repo.autonomous_users()
    islenecek = tum_kullanicilar[: max(settings.recommendation_users_per_tick, 1)]
    sayac["users_scanned"] = len(islenecek)
    sayac["users_deferred"] = len(tum_kullanicilar) - len(islenecek)

    for user in islenecek:
        # SIRA ONEMLI: gunluk sayac EN UCUZ sorgudur ve kullanicilarin cogu
        # ilk tick'ten sonra kotasini doldurmus olur. Once o bakilirsa
        # kalan tick'lerde kullanici basina UC sorgu yerine BIR sorgu atilir.
        istatistik = await repo.daily_stats(int(user["user_id"]))
        gunluk_adet = istatistik["count"]
        gunluk_tutar = istatistik["amount"]
        if gunluk_adet >= int(user["max_daily_recommendations"]) or gunluk_tutar >= float(
            user["daily_limit_try"]
        ):
            continue

        holdings = await repo.holdings_map(int(user["portfolio_id"]))
        acik = set(await repo.open_recommendation_asset_ids(int(user["user_id"])))

        # Guveni yuksek sinyal once degerlendirilir: gunluk kota dolarken
        # kullaniciya en guclu sinyaller ulassin.
        for signal in sorted(yayinlanan, key=lambda s: -float(s["confidence"])):
            yuk, gerekce = personalize(
                {**signal, "asset_class": sinif_haritasi.get(int(signal["asset_id"]))},
                user,
                holdings,
                gunluk_adet=gunluk_adet,
                gunluk_tutar=gunluk_tutar,
                acik_varliklar=acik,
            )
            if yuk is None:
                sayac["skipped"] += 1
                continue

            oneri = await repo.create_recommendation(yuk)
            await repo.log_audit(
                {
                    "recommendation_id": oneri.get("id"),
                    "user_id": int(user["user_id"]),
                    "event_type": "RECOMMENDATION_CREATED",
                    "actor": "SYSTEM",
                    "new_status": "PUBLISHED",
                    "detail": {
                        "rule_code": signal["rule_code"],
                        "confidence": float(signal["confidence"]),
                    },
                }
            )
            sayac["recommendations"] += 1
            gunluk_adet += 1
            gunluk_tutar += float(yuk["estimated_amount"])
            acik.add(int(yuk["asset_id"]))
            if gunluk_adet >= int(user["max_daily_recommendations"]):
                break

    return sayac


async def expire_due_recommendations() -> int:
    """BR-AUT-04: TTL dolan acik onerileri kapatir."""
    return await get_recommendation_repository().expire_due(datetime.now(timezone.utc))


async def list_recommendations(
    user_id: int, status: str | None = None
) -> RecommendationListResponse:
    repo = get_recommendation_repository()
    # TTL kapanisi OKUMADA da yapilir. Yalnizca fiyat tick'ine birakilsaydi -
    # ve gecmiste oldugu gibi backend bir sure kapali kalsaydi - suresi dolmus
    # oneriler "Bekleyen" sekmesinde acikmis gibi gorunurdu.
    await repo.expire_due(datetime.now(timezone.utc))
    rows = await repo.list_recommendations(user_id, status)
    return RecommendationListResponse(
        items=[_to_card(r) for r in rows],
        counts=await repo.counts_by_status(user_id),
    )


async def get_recommendation(user_id: int, recommendation_id: int) -> Recommendation:
    """Kart acildiginda durum Goruntulendi'ye gecer (D-07)."""
    repo = get_recommendation_repository()
    await repo.expire_due(datetime.now(timezone.utc))
    row = await repo.get_recommendation(user_id, recommendation_id)
    if row is None:
        raise NotFoundError("Bu oneri artik mevcut degil.")
    guncel = await repo.mark_viewed(user_id, recommendation_id)
    return _to_card(guncel or row)


async def reject_recommendation(
    user_id: int, recommendation_id: int, reason: str
) -> Recommendation:
    if reason not in RET_GEREKCELERI:
        raise BusinessRuleError("Gecersiz ret gerekcesi.")
    repo = get_recommendation_repository()
    onceki = await repo.get_recommendation(user_id, recommendation_id)
    if onceki is None:
        raise NotFoundError("Bu oneri artik mevcut degil.")
    row = await repo.reject(user_id, recommendation_id, reason)
    # FR-AUT-032: reddedilen oneri de kayit altina alinir.
    await repo.log_audit(
        {
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "event_type": "RECOMMENDATION_REJECTED",
            "actor": "USER",
            "old_status": onceki["status"],
            "new_status": "REJECTED",
            "reason": reason,
        }
    )
    return _to_card(row)


async def approve_recommendation(
    user_id: int, recommendation_id: int, quantity: float | None = None
) -> dict:
    """Onay -> emir. Emir olusturma MEVCUT trading servisine devredilir.

    BR-AUT-08 iki katmanda korunur: idempotency anahtari oneri kimligine
    baglidir (ayni oneri ikinci kez emir uretemez) ve `attach_order`
    veritabani seviyesinde tekil kisitla son sozu soyler.
    """
    repo = get_recommendation_repository()
    row = await repo.get_recommendation(user_id, recommendation_id)
    if row is None:
        raise NotFoundError("Bu oneri artik mevcut degil.")
    if row.get("order_id") is not None:
        raise BusinessRuleError("Bu oneri zaten bir emre donusmus.")
    if row["status"] not in {"PUBLISHED", "VIEWED"}:
        raise BusinessRuleError("Bu onerinin gecerlilik suresi doldu ya da durduruldu.")
    if _is_past(row["expires_at"]):
        raise BusinessRuleError("Bu onerinin gecerlilik suresi doldu.")

    adet = float(quantity) if quantity else float(row["quantity"])
    if adet <= 0:
        raise BusinessRuleError("Emir adedi sifirdan buyuk olmalidir.")

    emir = await trading_service.emir_olustur(
        user_id=user_id,
        symbol=row["asset_symbol"],
        side=row["side"],
        quantity=adet,
        idempotency_key=f"rec-{recommendation_id}",
    )
    guncel = await repo.attach_order(user_id, recommendation_id, int(emir.id))
    await repo.log_audit(
        {
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "event_type": "RECOMMENDATION_CONVERTED",
            "actor": "USER",
            "old_status": row["status"],
            "new_status": "CONVERTED",
            "detail": {"order_id": int(emir.id), "quantity": adet},
        }
    )
    return {"recommendation": _to_card(guncel), "order": emir}


async def set_kill_switch(active: bool, reason: str | None, actor: str) -> dict:
    repo = get_recommendation_repository()
    sonuc = await repo.set_kill_switch(active, reason, actor)
    durdurulan = await repo.halt_open(reason or "") if active else 0
    await repo.log_audit(
        {
            "event_type": "KILL_SWITCH_SET",
            "actor": actor,
            "reason": reason,
            "detail": {"active": active, "halted": durdurulan},
        }
    )
    return {**sonuc, "halted": durdurulan}


def _is_past(value) -> bool:
    an = value
    if isinstance(an, str):
        try:
            an = datetime.fromisoformat(an)
        except ValueError:
            return False
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an <= datetime.now(timezone.utc)


def _to_card(row: dict) -> Recommendation:
    return Recommendation(
        id=int(row["id"]),
        asset_symbol=row["asset_symbol"],
        asset_name=row["asset_name"],
        asset_class=row["asset_class"],
        side=row["side"],
        quantity=float(row["quantity"]),
        reference_price=float(row["reference_price"]),
        estimated_amount=float(row["estimated_amount"]),
        confidence=float(row["confidence"]),
        rationale=list(row["rationale"] or []),
        risk_note=row["risk_note"],
        sources=list(row["sources"] or []),
        personalization=dict(row.get("personalization") or {}),
        status=row["status"],
        rejection_reason=row.get("rejection_reason"),
        order_id=row.get("order_id"),
        expires_at=_iso(row["expires_at"]),
        created_at=_iso(row["created_at"]),
        viewed_at=_iso(row.get("viewed_at")),
        decided_at=_iso(row.get("decided_at")),
        disclaimer=SPK_UYARISI,
    )


def _iso(value) -> str:
    if value is None:
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
