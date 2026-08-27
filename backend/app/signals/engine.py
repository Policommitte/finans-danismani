"""Tarama bazli sinyal uretimi (UC-07).

NEDEN HABER BAZLI DEGIL (UC-06)
-------------------------------
Haber -> enstruman eslemesi bugun CALISMIYOR: `rag.documents.asset_id` tum
satirlarda BOS (bkz. docs/gelecek-isler.md madde 2). Haberi bir enstrumana
baglayamadan "haber bazli sinyal" uretmek, gerekcesi kaynagiyla eslesmeyen
bir oneri demektir - BR-AUT-01'i ihlal eder. Bu yuzden hat tarama bazli
kurulmustur; `asset_id` doldurulunca AYNI arayuze haber kurallari eklenir.

LLM KULLANILMAZ
---------------
Kurallar deterministiktir. Ayni girdi her zaman ayni sinyali uretir; boylece
FR-AUT-012 ("neden bana geldi?") ve UC-18 aciklanabilirlik ucu gercek bir
cevap verebilir. Uretilen metin bir modelin o anki ciktisi degildir.

ESIK ALTI SINYAL DE YAZILIR
---------------------------
D-02'de "Guven esigi gecildi mi? -> hayir -> Sinyali ic kayda al" kutusu var.
Esigin altinda kalan sinyal `published=False` ve `suppressed_reason` ile
DONER; cagiran onu yine de kaydeder. Boylece motorun neyi neden elediginin
kaydi kalir.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

#: Endeksler dogrudan alinip satilamaz (BR-AUT / trading ile ayni kural).
ISLEM_DISI_SINIFLAR = frozenset({"INDEX"})


def _yuzde(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _guven(ham: float) -> float:
    """Ham skoru 0..1 arasina sikistirir, 3 basamaga yuvarlar."""
    return round(max(0.0, min(1.0, ham)), 3)


def _bayat_mi(price_updated_at, now: datetime, max_staleness_minutes: int) -> bool:
    if price_updated_at is None:
        return True
    an = price_updated_at
    if isinstance(an, str):
        try:
            an = datetime.fromisoformat(an)
        except ValueError:
            return True
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an < now - timedelta(minutes=max_staleness_minutes)


def _kurallar(gunluk: float | None, haftalik: float | None, yillik: float | None):
    """(rule_code, yon, ham_guven, gerekce_maddeleri) ureten kural tablosu.

    Kurallar BIRBIRINI DISLAR ve ilk eslesen kazanir: tek enstruman icin tek
    sinyal uretilir (FR-AUT-001 "her oneri tek enstruman ve tek yon icerir").
    Sira, ACILIYETE gore dizilmistir - risk azaltan kurallar once bakilir.
    """
    g = gunluk if gunluk is not None else 0.0
    h = haftalik if haftalik is not None else 0.0
    y = yillik if yillik is not None else 0.0

    # 1) Sert dusus - risk azaltma once gelir.
    if g <= -5.0:
        return (
            "SHARP_DROP",
            "SELL",
            0.50 + min(abs(g) - 5.0, 10.0) / 40.0,
            [
                f"Gun icinde %{abs(g):.1f} sert dusus var.",
                "Pozisyonu kismen azaltmak asagi yonlu riski sinirlar.",
            ],
        )

    # 2) Kisa vadede asiri isinma - kar realizasyonu.
    if h >= 12.0 and g >= 0:
        return (
            "OVEREXTENDED",
            "SELL",
            0.48 + min(h - 12.0, 12.0) / 48.0,
            [
                f"Son bir haftada %{h:.1f} yukselis oldu.",
                "Kisa vadeli asiri isinma sonrasi geri cekilme olasiligi artar.",
                "Kismi kar realizasyonu maliyeti dusurur.",
            ],
        )

    # 3) Yukselis trendinde geri cekilme - klasik alim firsati kurgusu.
    if y >= 10.0 and h <= -3.0:
        return (
            "PULLBACK_IN_UPTREND",
            "BUY",
            0.52 + min(abs(h) - 3.0, 9.0) / 36.0 + min(y, 40.0) / 200.0,
            [
                f"Yillik trend %{y:.1f} ile yukari yonlu.",
                f"Son bir haftada %{abs(h):.1f} geri cekilme yasandi.",
                "Trend bozulmadan olusan geri cekilme giris seviyesi sunar.",
            ],
        )

    # 4) Istikrarli yukselis - dusuk guvenli, temkinli sinyal.
    if y >= 15.0 and 0.0 <= h <= 5.0:
        return (
            "STEADY_UPTREND",
            "BUY",
            0.45 + min(y - 15.0, 25.0) / 100.0,
            [
                f"Yillik %{y:.1f} yukselis istikrarli seyrediyor.",
                f"Haftalik degisim %{h:.1f} ile dar bantta.",
            ],
        )

    return None


def sinyal_uret(
    assets: list[dict],
    *,
    now: datetime,
    threshold: float,
    ttl_minutes: int,
    max_staleness_minutes: int = 30,
    engine_version: str = "scan-v1",
) -> list[dict]:
    """Varlik listesinden sinyal uretir. SAF fonksiyon - I/O yapmaz.

    `max_staleness_minutes` KRITIKTIR: fiyati bayat bir varlik icin sinyal
    uretilirse, onerinin onaylanmasiyla olusan emir fiyat gelene kadar
    PENDING asili kalir. Depoda 42 varligin yalnizca 16'sinin Yahoo eslemesi
    var (bkz. app/market/yahoo.py YAHOO_TICKERS); geri kalanina oneri
    uretmek kullaniciya asla gerceklesmeyecek bir emir onermek olurdu.
    """
    sinyaller: list[dict] = []
    son_gecerlilik = now + timedelta(minutes=ttl_minutes)

    for asset in assets:
        sinif = (asset.get("asset_class") or "").upper()
        if sinif in ISLEM_DISI_SINIFLAR:
            continue

        fiyat = _yuzde(asset.get("current_price"))
        if not fiyat or fiyat <= 0:
            continue

        if _bayat_mi(asset.get("price_updated_at"), now, max_staleness_minutes):
            continue

        sonuc = _kurallar(
            _yuzde(asset.get("daily_change_pct")),
            _yuzde(asset.get("weekly_change_pct")),
            _yuzde(asset.get("yearly_change_pct")),
        )
        if sonuc is None:
            continue

        rule_code, yon, ham_guven, gerekce = sonuc
        guven = _guven(ham_guven)
        esik_gecti = guven >= threshold

        sinyaller.append(
            {
                "asset_id": int(asset["asset_id"]),
                "symbol": asset.get("symbol"),
                "direction": yon,
                "confidence": guven,
                "rule_code": rule_code,
                # FR-AUT-003: en cok 5 madde.
                "rationale": gerekce[:5],
                "evidence": {
                    "daily_change_pct": _yuzde(asset.get("daily_change_pct")),
                    "weekly_change_pct": _yuzde(asset.get("weekly_change_pct")),
                    "yearly_change_pct": _yuzde(asset.get("yearly_change_pct")),
                    "price_as_of": str(asset.get("price_updated_at") or ""),
                },
                "reference_price": fiyat,
                "expires_at": son_gecerlilik,
                "engine_version": engine_version,
                "published": esik_gecti,
                "suppressed_reason": (None if esik_gecti else f"guven {guven} < esik {threshold}"),
            }
        )

    return sinyaller
