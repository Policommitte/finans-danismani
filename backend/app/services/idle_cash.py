"""İşlem merkezi için kurallı atıl bakiye/sepet önerisi.

Bu servis emir üretmez. Güncel piyasa verisini, kullanıcının risk profilini,
atıl bakiyesini ve mevcut pozisyonlarını kullanarak açıklanabilir bir öneri
hazırlar. Aynı girdiler aynı sıralamayı üretir; LLM finansal hesap yapmaz.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from math import ceil, sqrt
from statistics import mean, median, stdev

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.quantity import adet_yuvarla
from app.repositories.deps import get_recommendation_repository
from app.schemas.idle_cash import (
    IdleCashBasketBacktest,
    IdleCashBasketCatalog,
    IdleCashBasketMetrics,
    IdleCashBasketOption,
    IdleCashSuggestion,
    IdleCashSuggestionItem,
)
from app.services.recommendation import SPK_UYARISI, VARSAYILAN_PROFIL

_HEDEF_ACIKLAMALARI = {
    "LONG_TERM": "uzun vadeli birikim",
    "GROWTH": "büyüme odaklı yatırım",
    "MOMENTUM": "momentum",
    "LOW_VOLATILITY": "düşük oynaklık",
}

_SEPET_BASLIKLARI = {
    "LONG_TERM": ("İstikrarlı Birikim", "Birikim Alternatifi", "Geniş Perspektif"),
    "GROWTH": ("Güçlü Büyüme", "Büyüme Alternatifi", "Geniş Potansiyel"),
    "MOMENTUM": ("Güçlü Momentum", "Trend Takibi", "Momentum Alternatifi"),
    "LOW_VOLATILITY": ("Sakin Seyir", "Dengeli Savunma", "Düşük Dalgalanma"),
}

_SEPET_OZETLERI = (
    "Hedef puanlamasında üst sırada yer alan varlıklardan oluşturuldu.",
    "Aynı hedef için farklı varlıklara ve ağırlıklara yer veren bir alternatiftir.",
    "Aday havuzunun devamındaki varlıklarla çeşitlendirilmiş bir alternatiftir.",
)

_YATIRIM_SINIFLARI = frozenset(
    {"STOCK", "USA_STOCK", "EU_STOCK", "ETF", "GOLD", "COMMODITY", "FOREX", "CRYPTO"}
)

_SINIF_ADLARI = {
    "STOCK": "BIST hissesi",
    "USA_STOCK": "ABD hissesi",
    "EU_STOCK": "Avrupa hissesi",
    "ETF": "ETF",
    "GOLD": "altın",
    "COMMODITY": "emtia",
    "FOREX": "döviz",
    "CRYPTO": "kripto varlık",
}

_PROFIL_SINIF_PUANI = {
    "LOW": {
        "FOREX": 12,
        "GOLD": 12,
        "ETF": 8,
        "STOCK": 2,
        "USA_STOCK": 2,
        "EU_STOCK": 2,
        "COMMODITY": -8,
        "CRYPTO": -40,
    },
    "MEDIUM": {
        "ETF": 8,
        "STOCK": 5,
        "USA_STOCK": 5,
        "EU_STOCK": 5,
        "GOLD": 5,
        "FOREX": 2,
        "COMMODITY": 0,
        "CRYPTO": -8,
    },
    "HIGH": {
        "CRYPTO": 12,
        "COMMODITY": 7,
        "USA_STOCK": 7,
        "EU_STOCK": 7,
        "STOCK": 6,
        "ETF": 4,
        "GOLD": 0,
        "FOREX": -4,
    },
}

_HEDEF_SINIF_PUANI = {
    "LONG_TERM": {"ETF": 10, "STOCK": 6, "USA_STOCK": 6, "EU_STOCK": 6, "GOLD": 3, "CRYPTO": -10},
    "GROWTH": {"USA_STOCK": 8, "EU_STOCK": 8, "STOCK": 6, "ETF": 4, "CRYPTO": 2},
    "MOMENTUM": {"CRYPTO": 4, "COMMODITY": 2},
    "LOW_VOLATILITY": {"GOLD": 15, "FOREX": 12, "ETF": 8, "CRYPTO": -30, "COMMODITY": -5},
}

_YENIDEN_DENGELEME_POLITIKASI = {
    "LONG_TERM": {
        "review": timedelta(days=7),
        "minimum_hold": timedelta(days=30),
        "confirmations": 2,
        "score_gap": 8.0,
        "label": "Haftalık değerlendirme · en erken aylık üyelik değişimi",
    },
    "GROWTH": {
        "review": timedelta(days=7),
        "minimum_hold": timedelta(days=14),
        "confirmations": 2,
        "score_gap": 7.0,
        "label": "Haftalık değerlendirme · en az iki haftalık kalma süresi",
    },
    "MOMENTUM": {
        "review": timedelta(hours=6),
        "minimum_hold": timedelta(days=1),
        "confirmations": 1,
        "score_gap": 4.0,
        "label": "6 saatte bir değerlendirme · günlük üyelik değişimi",
    },
    "LOW_VOLATILITY": {
        "review": timedelta(days=1),
        "minimum_hold": timedelta(days=3),
        "confirmations": 2,
        "score_gap": 5.0,
        "label": "Günlük değerlendirme · oynaklık artışı iki kontrolde doğrulanır",
    },
}


_FIYAT_TAZELIK_LIMITI = {"CRYPTO": timedelta(hours=1)}
_VARSAYILAN_FIYAT_TAZELIK_LIMITI = timedelta(hours=96)
_MINIMUM_OYNAKLIK_GOZLEMI = 20

_SEPET_STRATEJILERI = (
    {
        "key": "CORE",
        "label": "Dengeli Çekirdek",
        "description": "Hedef puanı, risk ve çeşitlendirmeyi birlikte dengeler.",
        "volatility_penalty": 0.20,
        "return_tilt": 0.00,
        "max_correlation": 0.75,
        "inverse_volatility_power": 0.55,
        "max_weight": 0.30,
        "sector_ratio": 0.40,
        "region_ratio": 0.67,
    },
    {
        "key": "DEFENSIVE",
        "label": "Risk Kontrollü",
        "description": "Daha düşük oynaklık ve korelasyona öncelik verir.",
        "volatility_penalty": 1.50,
        "return_tilt": -0.05,
        "max_correlation": 0.60,
        "inverse_volatility_power": 1.00,
        "max_weight": 0.27,
        "sector_ratio": 0.34,
        "region_ratio": 0.60,
    },
    {
        "key": "OPPORTUNITY",
        "label": "Getiri Potansiyeli",
        "description": "Hedefe uygun güçlü performansı öne çıkarırken risk sınırlarını korur.",
        "volatility_penalty": 0.05,
        "return_tilt": 0.18,
        "max_correlation": 0.85,
        "inverse_volatility_power": 0.25,
        "max_weight": 0.35,
        "sector_ratio": 0.50,
        "region_ratio": 0.75,
    },
)
_SEPET_BENZERLIK_SINIRI = 0.60
_DUSUK_OYNAKLIK_ADAY_ORANI = 0.60
_DUSUK_OYNAKLIK_GECMIS_CARPANI = 1.50
_DUSUK_OYNAKLIK_GECMIS_TOLERANSI = 5.0
_BUYUME_VARLIK_SINIFLARI = frozenset({"STOCK", "USA_STOCK", "EU_STOCK", "ETF"})

_GERI_TEST_SURUMU = "basket-backtest-v1"
_GERI_TEST_GUN_SINIRI = 252
_GERI_TEST_MINIMUM_GOZLEM = 20
_GERI_TEST_YETERLI_GOZLEM = 120
_GERI_TEST_YENIDEN_DENGELEME_GUNLERI = {
    "LONG_TERM": 21,
    "GROWTH": 10,
    "MOMENTUM": 1,
    "LOW_VOLATILITY": 3,
}
_ISLEM_MALIYETI_BAZ_PUAN = {
    "STOCK": 15.0,
    "USA_STOCK": 15.0,
    "EU_STOCK": 15.0,
    "ETF": 10.0,
    "GOLD": 10.0,
    "COMMODITY": 15.0,
    "FOREX": 5.0,
    "CRYPTO": 25.0,
}


def _sayi(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _puan(asset: dict, profil: str, hedef: str, elde_var: bool) -> float:
    gunluk = max(-20.0, min(20.0, _sayi(asset.get("daily_change_pct"))))
    haftalik = max(-40.0, min(40.0, _sayi(asset.get("weekly_change_pct"))))
    yillik = max(-100.0, min(150.0, _sayi(asset.get("yearly_change_pct"))))
    oynaklik_tahmini = abs(gunluk) + abs(haftalik) * 0.35
    gerceklesen_oynaklik = _sayi(asset.get("volatility_20d_pct"))
    oynaklik = gerceklesen_oynaklik if gerceklesen_oynaklik > 0 else oynaklik_tahmini
    sinif = str(asset.get("asset_class") or "").upper()

    # Hedef ana sıralama eksenidir. Risk profili bunun üstüne güvenlik
    # ayarı ekler; böylece LOW profil tüm hedefleri tek sepete ezmez.
    if hedef == "LOW_VOLATILITY":
        sonuc = yillik * 0.06 - oynaklik * 1.20
    elif hedef == "MOMENTUM":
        sonuc = yillik * 0.12 + haftalik * 0.85 + gunluk * 0.35
    elif hedef == "GROWTH":
        sonuc = yillik * 0.42 + haftalik * 0.25 + gunluk * 0.10 - oynaklik * 0.08
    elif hedef == "LONG_TERM":
        sonuc = yillik * 0.65 + haftalik * 0.10 - oynaklik * 0.25

    if profil == "LOW":
        sonuc -= oynaklik * 0.45
    elif profil == "HIGH":
        sonuc += haftalik * 0.10 + gunluk * 0.05

    sonuc += _PROFIL_SINIF_PUANI.get(profil, {}).get(sinif, 0)
    sonuc += _HEDEF_SINIF_PUANI.get(hedef, {}).get(sinif, 0)

    # Aynı varlıklara yığılmak yerine çeşitlendirmeyi öne çıkarır.
    return sonuc - (4.0 if elde_var else 0.0)


def _puan_bilesenleri(asset: dict, profil: str, hedef: str, elde_var: bool) -> dict[str, float]:
    gunluk = max(-20.0, min(20.0, _sayi(asset.get("daily_change_pct"))))
    haftalik = max(-40.0, min(40.0, _sayi(asset.get("weekly_change_pct"))))
    yillik = max(-100.0, min(150.0, _sayi(asset.get("yearly_change_pct"))))
    tahmini_oynaklik = abs(gunluk) + abs(haftalik) * 0.35
    gerceklesen_oynaklik = _sayi(asset.get("volatility_20d_pct"))
    oynaklik = gerceklesen_oynaklik if gerceklesen_oynaklik > 0 else tahmini_oynaklik
    sinif = str(asset.get("asset_class") or "").upper()

    if hedef == "LOW_VOLATILITY":
        sonuc = {
            "yillik_performans": yillik * 0.06,
            "oynaklik": -oynaklik * 1.20,
        }
    elif hedef == "MOMENTUM":
        sonuc = {
            "yillik_performans": yillik * 0.12,
            "haftalik_momentum": haftalik * 0.85,
            "gunluk_momentum": gunluk * 0.35,
        }
    elif hedef == "GROWTH":
        sonuc = {
            "yillik_performans": yillik * 0.42,
            "haftalik_momentum": haftalik * 0.25,
            "gunluk_momentum": gunluk * 0.10,
            "oynaklik": -oynaklik * 0.08,
        }
    else:
        sonuc = {
            "yillik_performans": yillik * 0.65,
            "haftalik_momentum": haftalik * 0.10,
            "oynaklik": -oynaklik * 0.25,
        }

    sonuc["risk_profili"] = (
        -oynaklik * 0.45
        if profil == "LOW"
        else haftalik * 0.10 + gunluk * 0.05
        if profil == "HIGH"
        else 0.0
    )
    sonuc["profil_sinif_uyumu"] = float(_PROFIL_SINIF_PUANI.get(profil, {}).get(sinif, 0))
    sonuc["hedef_sinif_uyumu"] = float(_HEDEF_SINIF_PUANI.get(hedef, {}).get(sinif, 0))
    sonuc["mevcut_portfoy"] = -4.0 if elde_var else 0.0
    return {anahtar: round(deger, 2) for anahtar, deger in sonuc.items()}


def _tarih(value: object) -> datetime | None:
    if isinstance(value, datetime):
        sonuc = value
    elif isinstance(value, str):
        try:
            sonuc = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return sonuc if sonuc.tzinfo else sonuc.replace(tzinfo=timezone.utc)


def _bayat_veri(asset: dict, now: datetime) -> bool:
    guncellenme = _tarih(asset.get("price_updated_at"))
    if guncellenme is None or guncellenme > now + timedelta(minutes=5):
        return True
    sinif = str(asset.get("asset_class") or "").upper()
    limit = _FIYAT_TAZELIK_LIMITI.get(sinif, _VARSAYILAN_FIYAT_TAZELIK_LIMITI)
    return now - guncellenme > limit


def _yetersiz_oynaklik_gecmisi(asset: dict) -> bool:
    return int(_sayi(asset.get("volatility_observation_count"))) < _MINIMUM_OYNAKLIK_GOZLEMI


def _uygunluk_seviyesi(sira: int, aday_sayisi: int) -> str:
    oran = (sira - 1) / max(aday_sayisi - 1, 1)
    if oran <= 0.20:
        return "HIGH"
    if oran <= 0.50:
        return "MEDIUM"
    return "LOW"


def _gunluk_getiriler(asset: dict) -> dict[str, float]:
    raw = asset.get("daily_returns_252d") or asset.get("daily_returns_60d") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(day): _sayi(value) for day, value in raw.items() if value is not None}


def _tl_bazli_getiriler(asset: dict, assets: list[dict]) -> dict[str, float]:
    """Varlığın günlük getirisini yatırım tutarının para birimi olan TL'ye çevirir."""
    getiriler = _gunluk_getiriler(asset)
    currency = str(asset.get("currency") or "TRY").upper()
    if currency == "TRY":
        return getiriler

    fx_symbol = f"{currency}/TRY"
    fx_asset = next(
        (candidate for candidate in assets if str(candidate.get("symbol")).upper() == fx_symbol),
        None,
    )
    if fx_asset is None:
        return {}
    fx_returns = _gunluk_getiriler(fx_asset)
    return {
        day: ((1 + value / 100) * (1 + fx_returns[day] / 100) - 1) * 100
        for day, value in getiriler.items()
        if day in fx_returns
    }


def _maksimum_dusus(values: list[float]) -> float:
    peak = values[0] if values else 1.0
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst * 100


def _sepet_geri_testi(
    selected_assets: list[dict],
    weights: list[float],
    benchmark_assets: list[dict],
    all_assets: list[dict],
    goal: str,
) -> IdleCashBasketBacktest:
    """Bugünkü üyelik/ağırlıkların geçmiş günlük getirilerdeki simülasyonu.

    Üyelik geçmişe dönük yeniden seçilmez. Sonuç yalnızca mevcut sepetin
    tarihsel davranışını gösterir; gelecek performansı veya seçim başarısını
    kanıtlayan bir strateji testi değildir.
    """
    benchmark_label = "Uygun varlık evreni (eşit ağırlık)"
    normalized_total = sum(weights)
    normalized_weights = (
        [weight / normalized_total for weight in weights] if normalized_total > 0 else []
    )
    return_maps = [_tl_bazli_getiriler(asset, all_assets) for asset in selected_assets]
    common_days = (
        sorted(set.intersection(*(set(values) for values in return_maps)))
        if return_maps and all(return_maps)
        else []
    )[-_GERI_TEST_GUN_SINIRI:]
    observation_count = len(common_days)
    if observation_count < _GERI_TEST_MINIMUM_GOZLEM:
        return IdleCashBasketBacktest(
            status="INSUFFICIENT",
            methodology_version=_GERI_TEST_SURUMU,
            observation_count=observation_count,
            rebalance_count=0,
            benchmark_label=benchmark_label,
            note=(
                "Güvenilir simülasyon için en az 20 ortak günlük getiri gerekiyor. "
                "Bu sonuç yatırım kararı için kullanılmamalıdır."
            ),
        )

    target_weights = normalized_weights
    gross_positions = list(target_weights)
    weighted_cost_bps = sum(
        weight * _ISLEM_MALIYETI_BAZ_PUAN.get(str(asset.get("asset_class") or "").upper(), 15.0)
        for asset, weight in zip(selected_assets, target_weights)
    )
    entry_cost_rate = weighted_cost_bps / 10_000
    net_positions = [weight * (1 - entry_cost_rate) for weight in target_weights]
    gross_values = [1.0]
    net_values = [1.0, sum(net_positions)]
    net_daily_returns: list[float] = []
    rebalance_every = _GERI_TEST_YENIDEN_DENGELEME_GUNLERI[goal]
    rebalance_count = 0

    for day_index, day in enumerate(common_days, start=1):
        previous_net = sum(net_positions)
        for index, values in enumerate(return_maps):
            factor = max(0.0, 1 + values[day] / 100)
            gross_positions[index] *= factor
            net_positions[index] *= factor

        if day_index < observation_count and day_index % rebalance_every == 0:
            gross_total = sum(gross_positions)
            net_total = sum(net_positions)
            current_weights = [position / net_total for position in net_positions]
            turnover = (
                sum(
                    abs(current - target)
                    for current, target in zip(current_weights, target_weights)
                )
                / 2
            )
            cost = net_total * turnover * weighted_cost_bps / 10_000
            gross_positions = [gross_total * weight for weight in target_weights]
            net_positions = [max(0.0, net_total - cost) * weight for weight in target_weights]
            if turnover > 0.000001:
                rebalance_count += 1

        current_net = sum(net_positions)
        gross_values.append(sum(gross_positions))
        net_values.append(current_net)
        if previous_net > 0:
            net_daily_returns.append(current_net / previous_net - 1)

    benchmark_maps = [
        values for asset in benchmark_assets if (values := _tl_bazli_getiriler(asset, all_assets))
    ]
    benchmark_value = 1.0
    benchmark_day_count = 0
    minimum_benchmark_breadth = max(1, ceil(len(benchmark_maps) * 0.50))
    for day in common_days:
        day_returns = [values[day] for values in benchmark_maps if day in values]
        if len(day_returns) >= minimum_benchmark_breadth:
            benchmark_value *= 1 + mean(day_returns) / 100
            benchmark_day_count += 1

    net_return = (net_values[-1] - 1) * 100
    gross_return = (gross_values[-1] - 1) * 100
    benchmark_return = (
        (benchmark_value - 1) * 100 if benchmark_day_count == observation_count else None
    )
    daily_stdev = stdev(net_daily_returns) if len(net_daily_returns) >= 2 else 0.0
    annualized_volatility = daily_stdev * sqrt(252) * 100
    risk_adjusted = mean(net_daily_returns) / daily_stdev * sqrt(252) if daily_stdev > 0 else None
    status = "SUFFICIENT" if observation_count >= _GERI_TEST_YETERLI_GOZLEM else "LIMITED"
    return IdleCashBasketBacktest(
        status=status,
        methodology_version=_GERI_TEST_SURUMU,
        observation_count=observation_count,
        start_date=common_days[0],
        end_date=common_days[-1],
        gross_return_pct=round(gross_return, 2),
        net_return_pct=round(net_return, 2),
        benchmark_return_pct=(round(benchmark_return, 2) if benchmark_return is not None else None),
        excess_return_pct=(
            round(net_return - benchmark_return, 2) if benchmark_return is not None else None
        ),
        annualized_volatility_pct=round(annualized_volatility, 2),
        max_drawdown_pct=round(_maksimum_dusus(net_values), 2),
        risk_adjusted_return=(round(risk_adjusted, 2) if risk_adjusted is not None else None),
        transaction_cost_impact_pct=round(max(0.0, gross_values[-1] - net_values[-1]) * 100, 3),
        rebalance_count=rebalance_count,
        benchmark_label=benchmark_label,
        note=(
            "Mevcut sepet üyeleri ve hedef ağırlıkları geçmiş günlük getirilerde "
            "simüle edildi; işlem maliyeti düşüldü. Bu bir gelecek tahmini değildir."
            if status == "SUFFICIENT"
            else "Geçmiş veri 120 işlem gününden kısa olduğu için sonuç sınırlı "
            "güvene sahiptir; mevcut üyeliğin geçmiş simülasyonudur, gelecek "
            "tahmini değildir."
        ),
    )


def _korelasyon(first: dict, second: dict) -> float | None:
    first_returns = _gunluk_getiriler(first)
    second_returns = _gunluk_getiriler(second)
    common_days = sorted(set(first_returns) & set(second_returns))
    if len(common_days) < 20:
        return None
    x = [first_returns[day] for day in common_days]
    y = [second_returns[day] for day in common_days]
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    x_variance = sum((a - x_mean) ** 2 for a in x)
    y_variance = sum((b - y_mean) ** 2 for b in y)
    denominator = sqrt(x_variance * y_variance)
    if denominator <= 0:
        return None
    return max(-1.0, min(1.0, numerator / denominator))


def _strateji_puani(
    asset: dict,
    profil: str,
    goal: str,
    elde_var: bool,
    strategy: dict,
) -> float:
    temel = _puan(asset, profil, goal, elde_var)
    oynaklik = max(0.0, _sayi(asset.get("volatility_20d_pct")))
    yillik = max(-100.0, min(150.0, _sayi(asset.get("yearly_change_pct"))))
    return (
        temel
        - oynaklik * float(strategy["volatility_penalty"])
        + yillik * float(strategy["return_tilt"])
    )


def _agirlik_tavanli(raw_weights: list[float], max_weight: float) -> list[float]:
    if not raw_weights:
        return []
    weights = [0.0] * len(raw_weights)
    active = set(range(len(raw_weights)))
    remaining = 1.0
    while active:
        raw_total = sum(raw_weights[index] for index in active)
        if raw_total <= 0:
            equal = remaining / len(active)
            for index in active:
                weights[index] = equal
            break
        newly_capped = {
            index for index in active if remaining * raw_weights[index] / raw_total > max_weight
        }
        if not newly_capped:
            for index in active:
                weights[index] = remaining * raw_weights[index] / raw_total
            break
        for index in newly_capped:
            weights[index] = max_weight
            remaining -= max_weight
        active -= newly_capped
    total = sum(weights)
    return [weight / total for weight in weights] if total > 0 else weights


def _risk_agirliklari(
    assets: list[dict],
    strategy: dict,
    profil: str,
) -> list[float]:
    power = float(strategy["inverse_volatility_power"])
    if profil == "LOW":
        power *= 1.15
    elif profil == "HIGH":
        power *= 0.80
    raw = [1.0 / max(_sayi(asset.get("volatility_20d_pct")), 0.25) ** power for asset in assets]
    return _agirlik_tavanli(raw, float(strategy["max_weight"]))


def _ayni_deger_sayisi(assets: list[dict], field: str, value: str) -> int:
    return sum(str(asset.get(field) or "OTHER") == value for asset in assets)


def _aday_eklenebilir(
    asset: dict,
    selected: list[dict],
    target_count: int,
    strategy: dict,
    profil: str,
    goal: str,
    available_assets: list[dict],
) -> bool:
    asset_class = str(asset.get("asset_class") or "").upper()
    available_classes = {
        str(candidate.get("asset_class") or "").upper() for candidate in available_assets
    }
    class_limit = (
        target_count
        if len(available_classes) == 1
        else _sinif_limiti(profil, goal, asset_class, target_count)
    )
    if _ayni_deger_sayisi(selected, "asset_class", asset_class) >= class_limit:
        return False

    sector = str(asset.get("sector") or asset_class)
    sector_limit = max(1, ceil(target_count * float(strategy["sector_ratio"])))
    available_sectors = {
        str(candidate.get("sector") or candidate.get("asset_class") or "OTHER")
        for candidate in available_assets
    }
    if (
        len(available_sectors) > 1
        and _ayni_deger_sayisi(selected, "sector", sector) >= sector_limit
    ):
        return False

    region = str(asset.get("region") or "GLOBAL")
    region_limit = max(1, ceil(target_count * float(strategy["region_ratio"])))
    available_regions = {str(candidate.get("region") or "GLOBAL") for candidate in available_assets}
    if (
        len(available_regions) > 1
        and _ayni_deger_sayisi(selected, "region", region) >= region_limit
    ):
        return False

    currency = str(asset.get("currency") or "TRY")
    available_currencies = {
        str(candidate.get("currency") or "TRY") for candidate in available_assets
    }
    if (
        len(available_currencies) > 1
        and _ayni_deger_sayisi(selected, "currency", currency) >= region_limit
    ):
        return False

    correlations = [
        correlation
        for existing in selected
        if (correlation := _korelasyon(asset, existing)) is not None
    ]
    return not correlations or max(correlations) <= float(strategy["max_correlation"])


def _sepet_benzerligi(first: set[int], second: set[int]) -> float:
    union = first | second
    return len(first & second) / len(union) if union else 1.0


def _sepet_metrikleri(assets: list[dict], weights: list[float]) -> IdleCashBasketMetrics:
    variance = 0.0
    correlations: list[float] = []
    for first_index, first in enumerate(assets):
        first_vol = max(0.0, _sayi(first.get("volatility_20d_pct")))
        for second_index, second in enumerate(assets):
            second_vol = max(0.0, _sayi(second.get("volatility_20d_pct")))
            if first_index == second_index:
                correlation = 1.0
            else:
                measured = _korelasyon(first, second)
                correlation = measured if measured is not None else 0.0
                if first_index < second_index and measured is not None:
                    correlations.append(measured)
            variance += (
                weights[first_index] * weights[second_index] * first_vol * second_vol * correlation
            )
    expected_volatility = sqrt(max(0.0, variance))
    average_correlation = sum(correlations) / len(correlations) if correlations else None
    count = max(len(assets), 1)
    class_ratio = len({asset.get("asset_class") for asset in assets}) / count
    sector_ratio = len({asset.get("sector") for asset in assets}) / count
    correlation_quality = 1.0 - max(0.0, average_correlation or 0.0)
    breadth_factor = min(1.0, count / 5)
    diversification = min(
        100.0,
        max(
            0.0,
            (class_ratio * 40 + sector_ratio * 30 + correlation_quality * 30) * breadth_factor,
        ),
    )
    risk_level = "LOW" if expected_volatility < 1.0 else "MEDIUM"
    if expected_volatility >= 2.5:
        risk_level = "HIGH"
    return IdleCashBasketMetrics(
        expected_volatility_20d_pct=round(expected_volatility, 2),
        average_correlation=(
            round(average_correlation, 2) if average_correlation is not None else None
        ),
        diversification_score=round(diversification, 1),
        risk_level=risk_level,
        asset_class_count=len({asset.get("asset_class") for asset in assets}),
        sector_count=len({asset.get("sector") for asset in assets}),
        region_count=len({asset.get("region") for asset in assets}),
        largest_weight_pct=round(max(weights, default=0.0) * 100, 1),
    )


def _agirliklar(adet: int, hedef: str) -> list[float]:
    dagilimlar = {
        1: [1.0],
        2: [0.60, 0.40],
        3: [0.45, 0.33, 0.22],
        4: [0.35, 0.27, 0.22, 0.16],
        5: [0.28, 0.23, 0.19, 0.16, 0.14],
        6: [0.24, 0.20, 0.17, 0.15, 0.13, 0.11],
    }
    return dagilimlar[adet]


def _hedef_varlik_adedi(profil: str, hedef: str) -> int:
    if hedef == "LOW_VOLATILITY":
        return 4 if profil == "LOW" else 5
    return {"LOW": 4, "MEDIUM": 5, "HIGH": 6}.get(profil, 5)


def _yuzdelik(degerler: list[float], oran: float) -> float | None:
    """Harici kutuphane gerektirmeyen yakin-sira yuzdeligi."""
    sirali = sorted(degerler)
    if not sirali:
        return None
    index = max(0, min(len(sirali) - 1, ceil(len(sirali) * oran) - 1))
    return sirali[index]


def _buyume_sinyali(asset: dict) -> bool:
    """Kalici buyume veya belirgin bir toparlanma sinyali arar."""
    yillik = _sayi(asset.get("yearly_change_pct"))
    haftalik = _sayi(asset.get("weekly_change_pct"))
    gunluk = _sayi(asset.get("daily_change_pct"))
    return yillik > 0 or (haftalik >= 3.0 and gunluk >= -2.0)


def _adaylari_filtrele(
    context: dict,
    assets: list[dict],
    goal: str,
    now: datetime,
) -> list[dict]:
    izinli = {str(c).upper() for c in context.get("allowed_asset_classes") or []}
    adaylar = [
        asset
        for asset in assets
        if str(asset.get("asset_class") or "").upper() in _YATIRIM_SINIFLARI
        and (not izinli or str(asset.get("asset_class") or "").upper() in izinli)
        and _sayi(asset.get("current_price")) > 0
        and not _bayat_veri(asset, now)
        and (goal != "LOW_VOLATILITY" or not _yetersiz_oynaklik_gecmisi(asset))
    ]
    if goal == "GROWTH":
        return [asset for asset in adaylar if _buyume_sinyali(asset)]
    if goal == "MOMENTUM":
        return [asset for asset in adaylar if _sayi(asset.get("weekly_change_pct")) > 0]
    if goal == "LOW_VOLATILITY":
        esik = _yuzdelik(
            [
                _sayi(asset.get("volatility_20d_pct"))
                for asset in adaylar
                if _sayi(asset.get("volatility_20d_pct")) > 0
            ],
            _DUSUK_OYNAKLIK_ADAY_ORANI,
        )
        if esik is not None:
            return [
                asset for asset in adaylar if 0 < _sayi(asset.get("volatility_20d_pct")) <= esik
            ]
    return adaylar


def _hedefe_uygun_sepet(
    goal: str,
    suggestion: IdleCashSuggestion,
    selected_assets: list[dict],
    metrics: IdleCashBasketMetrics,
) -> bool:
    """Farkliligi korurken hedef anlaminin strateji varyantinda kaybolmasini onler."""
    if not selected_assets:
        return False

    if goal == "MOMENTUM":
        return all(_sayi(asset.get("weekly_change_pct")) > 0 for asset in selected_assets)

    if goal == "GROWTH":
        buyume_varliklari = sum(
            str(asset.get("asset_class") or "").upper() in _BUYUME_VARLIK_SINIFLARI
            for asset in selected_assets
        )
        return buyume_varliklari >= ceil(len(selected_assets) * 0.50) and all(
            _buyume_sinyali(asset) for asset in selected_assets
        )

    if goal == "LOW_VOLATILITY":
        return metrics.risk_level == "LOW"

    return True


def _dusuk_oynaklik_gecmis_filtresi(
    secenekler: list[IdleCashBasketOption],
) -> list[IdleCashBasketOption]:
    """Guncel olarak sakin ama tarihsel olarak bariz riskli aykiri sepetleri eler."""
    oynakliklar = [
        option.backtest.annualized_volatility_pct
        for option in secenekler
        if option.backtest.annualized_volatility_pct is not None
    ]
    if len(oynakliklar) < 2:
        return secenekler
    taban = min(oynakliklar)
    esik = max(
        taban * _DUSUK_OYNAKLIK_GECMIS_CARPANI,
        taban + _DUSUK_OYNAKLIK_GECMIS_TOLERANSI,
    )
    return [
        option
        for option in secenekler
        if option.backtest.annualized_volatility_pct is None
        or option.backtest.annualized_volatility_pct <= esik
    ]


def _sinif_limiti(profil: str, hedef: str, sinif: str, hedef_adet: int) -> int:
    if sinif == "CRYPTO":
        if profil == "LOW" or hedef == "LOW_VOLATILITY":
            return 0
        return 1 if profil == "MEDIUM" else 2
    if sinif in {"GOLD", "FOREX", "COMMODITY"}:
        return 1
    return min(2, hedef_adet)


def _sabit_uyelik_sec(
    uygun: list[dict],
    asset_ids: list[int],
    profil: str,
    hedef: str,
    yatirilabilir: float,
    strategy: dict,
) -> list[dict]:
    """Kayitli uyeligi guncel fiyat ve risk kurallariyla yeniden dogrular."""
    harita = {int(asset["asset_id"]): asset for asset in uygun}
    secilenler = [harita[asset_id] for asset_id in asset_ids if asset_id in harita]
    if len(secilenler) != len(asset_ids) or not secilenler:
        return []

    dogrulananlar: list[dict] = []
    agirliklar = _risk_agirliklari(secilenler, strategy, profil)
    for asset, agirlik in zip(secilenler, agirliklar):
        sinif = str(asset.get("asset_class") or "").upper()
        if not _aday_eklenebilir(
            asset,
            dogrulananlar,
            len(secilenler),
            strategy,
            profil,
            hedef,
            uygun,
        ):
            return []
        if adet_yuvarla(yatirilabilir * agirlik / _sayi(asset["current_price"]), sinif) <= 0:
            return []
        dogrulananlar.append(asset)
    return secilenler


def suggestion_build(
    context: dict,
    assets: list[dict],
    holdings: dict[int, float],
    goal: str,
    *,
    now: datetime | None = None,
    candidate_offset: int = 0,
    strategy_index: int = 0,
    fixed_asset_ids: list[int] | None = None,
) -> IdleCashSuggestion:
    profil = str(context.get("risk_tolerance") or VARSAYILAN_PROFIL).upper()
    if profil not in {"LOW", "MEDIUM", "HIGH"}:
        profil = VARSAYILAN_PROFIL
    strategy = _SEPET_STRATEJILERI[strategy_index % len(_SEPET_STRATEJILERI)]

    bakiye = _sayi(context.get("available_balance"))
    kaynak = "cash_account"
    if bakiye <= 0:
        raise BusinessRuleError("Öneri oluşturmak için kullanılabilir bakiye bulunmuyor.")

    izinli = {str(c).upper() for c in context.get("allowed_asset_classes") or []}
    an = now or datetime.now(timezone.utc)
    adaylar = _adaylari_filtrele(context, assets, goal, an)
    if not adaylar:
        raise NotFoundError("Yatırım sepeti için uygun güncel piyasa verisi alınamadı.")

    yatirilabilir = round(bakiye * 0.90, 2)
    sirali = sorted(
        adaylar,
        key=lambda a: (
            -_strateji_puani(
                a,
                profil,
                goal,
                _sayi(holdings.get(int(a["asset_id"]))) > 0,
                strategy,
            ),
            str(a.get("symbol", "")),
        ),
    )
    hedef_siralari = {int(asset["asset_id"]): sira for sira, asset in enumerate(sirali, start=1)}
    aday_sayisi = len(sirali)
    uygun = [
        a
        for a in sirali
        if adet_yuvarla(
            yatirilabilir / _sayi(a["current_price"]),
            str(a.get("asset_class") or ""),
        )
        > 0
    ]
    if not uygun:
        raise BusinessRuleError(
            "Bakiye, uygun varlıklardan alınabilecek en küçük miktar için yetersiz."
        )

    secilenler = (
        _sabit_uyelik_sec(uygun, fixed_asset_ids or [], profil, goal, yatirilabilir, strategy)
        if fixed_asset_ids is not None
        else []
    )

    if not secilenler:
        # Alternatif kartlar ayni siralamanin farkli noktalarindan baslar.
        kaydirma = candidate_offset % len(uygun)
        if kaydirma:
            uygun = uygun[kaydirma:] + uygun[:kaydirma]

        hedef_adet = min(_hedef_varlik_adedi(profil, goal), len(uygun))
        for denenen_adet in range(hedef_adet, 0, -1):
            aday_secimler: list[dict] = []
            for asset in uygun:
                if not _aday_eklenebilir(
                    asset,
                    aday_secimler,
                    denenen_adet,
                    strategy,
                    profil,
                    goal,
                    uygun,
                ):
                    continue
                aday_secimler.append(asset)
                if len(aday_secimler) == denenen_adet:
                    break
            if len(aday_secimler) == denenen_adet:
                risk_agirliklari = _risk_agirliklari(aday_secimler, strategy, profil)
                if all(
                    adet_yuvarla(
                        yatirilabilir * agirlik / _sayi(asset["current_price"]),
                        str(asset.get("asset_class") or ""),
                    )
                    > 0
                    for asset, agirlik in zip(aday_secimler, risk_agirliklari)
                ):
                    secilenler = aday_secimler
                    break

    if not secilenler:
        raise BusinessRuleError("Bakiye, seçilen dağılımla yatırım yapmaya yeterli değil.")

    agirliklar = _risk_agirliklari(secilenler, strategy, profil)
    kalemler: list[IdleCashSuggestionItem] = []
    hedef_adi = _HEDEF_ACIKLAMALARI[goal]
    for asset, agirlik in zip(secilenler, agirliklar):
        fiyat = _sayi(asset["current_price"])
        sinif = str(asset.get("asset_class") or "").upper()
        miktar = adet_yuvarla(yatirilabilir * agirlik / fiyat, sinif)
        tutar = round(miktar * fiyat, 2)
        elde_var = _sayi(holdings.get(int(asset["asset_id"]))) > 0
        puan_bilesenleri = _puan_bilesenleri(asset, profil, goal, elde_var)
        hedef_sirasi = hedef_siralari[int(asset["asset_id"])]
        kalemler.append(
            IdleCashSuggestionItem(
                asset_id=int(asset["asset_id"]),
                symbol=str(asset["symbol"]),
                name=str(asset.get("name") or asset["symbol"]),
                asset_class=sinif,
                currency=str(asset.get("currency") or "TRY"),
                sector=str(asset.get("sector") or sinif),
                region=str(asset.get("region") or "GLOBAL"),
                quantity=round(miktar, 6),
                reference_price=round(fiyat, 2),
                estimated_amount=tutar,
                weight_pct=round(agirlik * 100, 1),
                goal_rank=hedef_sirasi,
                candidate_count=aday_sayisi,
                suitability_level=_uygunluk_seviyesi(hedef_sirasi, aday_sayisi),
                score_components=puan_bilesenleri,
                rationale=[
                    f"{profil} risk profili, {hedef_adi} hedefi ve "
                    f"{_SINIF_ADLARI.get(sinif, sinif)} özellikleriyle uyumlu puanlandı.",
                    "Mevcut portföyünüzde bulunmadığı için çeşitlendirmeye katkı sağlayabilir."
                    if not elde_var
                    else (
                        "Mevcut pozisyonunuz dikkate alınarak daha düşük öncelikle "
                        "değerlendirildi."
                    ),
                ],
            )
        )

    toplam = round(sum(k.estimated_amount for k in kalemler), 2)
    izin_ozeti = (
        ", ".join(sorted(_SINIF_ADLARI.get(sinif, sinif) for sinif in izinli))
        if izinli
        else "tüm işlem yapılabilir varlık sınıfları"
    )
    return IdleCashSuggestion(
        mode="basket" if len(kalemler) > 1 else "single",
        balance_source=kaynak,
        available_balance=round(bakiye, 2),
        investable_amount=yatirilabilir,
        estimated_total=toplam,
        unallocated_balance=round(max(0, bakiye - toplam), 2),
        risk_profile=profil,
        goal=goal,
        preference_summary=(
            f"{len(assets)} varlık tarandı; {profil} risk profili, {hedef_adi} hedefi ve "
            f"{izin_ozeti} içinden {len(adaylar)} uygun aday değerlendirildi."
        ),
        items=kalemler,
        disclaimer=SPK_UYARISI,
        generated_at=an.isoformat(),
    )


def basket_catalog_build(
    context: dict,
    assets: list[dict],
    holdings: dict[int, float],
    goal: str,
    *,
    now: datetime | None = None,
    memberships: list[list[int]] | None = None,
    evaluated_at: datetime | None = None,
    changed_at: datetime | None = None,
    membership_changed: bool = False,
) -> IdleCashBasketCatalog:
    """Aynı hedef için en fazla üç, gerçekten farklı sepet alternatifi üretir."""
    profil = str(context.get("risk_tolerance") or VARSAYILAN_PROFIL).upper()
    if profil not in {"LOW", "MEDIUM", "HIGH"}:
        profil = VARSAYILAN_PROFIL

    an = now or datetime.now(timezone.utc)
    secenekler: list[IdleCashBasketOption] = []
    secilen_kumeler: list[set[int]] = []
    asset_map = {int(asset["asset_id"]): asset for asset in assets}
    benchmark_assets = _adaylari_filtrele(context, assets, goal, an)

    for strategy_index, strategy in enumerate(_SEPET_STRATEJILERI):
        kayitli_uyelik = (
            memberships[strategy_index]
            if memberships and strategy_index < len(memberships)
            else None
        )
        sabit_uyelik = kayitli_uyelik or None
        offsets = [0] if sabit_uyelik is not None else list(range(max(len(assets), 1)))
        minimum_asset_count = min(3, len(_adaylari_filtrele(context, assets, goal, an)))
        chosen_suggestion: IdleCashSuggestion | None = None
        chosen_ids: set[int] = set()
        chosen_assets: list[dict] = []
        chosen_weights: list[float] = []
        chosen_metrics: IdleCashBasketMetrics | None = None
        for offset in offsets:
            suggestion = suggestion_build(
                context,
                assets,
                holdings,
                goal,
                now=an,
                candidate_offset=offset,
                strategy_index=strategy_index,
                fixed_asset_ids=sabit_uyelik,
            )
            ids = {item.asset_id for item in suggestion.items}
            if len(ids) < minimum_asset_count:
                continue
            if sabit_uyelik is None and any(
                _sepet_benzerligi(ids, previous) > _SEPET_BENZERLIK_SINIRI
                for previous in secilen_kumeler
            ):
                continue
            selected_assets = [
                asset_map[item.asset_id] for item in suggestion.items if item.asset_id in asset_map
            ]
            weights = [item.weight_pct / 100 for item in suggestion.items]
            metrics = _sepet_metrikleri(selected_assets, weights)
            if not _hedefe_uygun_sepet(goal, suggestion, selected_assets, metrics):
                continue
            chosen_suggestion = suggestion
            chosen_ids = ids
            chosen_assets = selected_assets
            chosen_weights = weights
            chosen_metrics = metrics
            break
        if chosen_suggestion is None or chosen_metrics is None:
            continue

        secenekler.append(
            IdleCashBasketOption(
                id=f"{goal.lower()}-{strategy_index + 1}",
                title=_SEPET_BASLIKLARI[goal][strategy_index],
                summary=str(strategy["description"]),
                strategy_key=strategy["key"],
                strategy_label=str(strategy["label"]),
                strategy_description=str(strategy["description"]),
                metrics=chosen_metrics,
                backtest=_sepet_geri_testi(
                    chosen_assets,
                    chosen_weights,
                    benchmark_assets,
                    assets,
                    goal,
                ),
                suggestion=chosen_suggestion,
            )
        )
        secilen_kumeler.append(chosen_ids)

    if goal == "LOW_VOLATILITY":
        secenekler = _dusuk_oynaklik_gecmis_filtresi(secenekler)

    if not secenekler:
        raise NotFoundError(
            "Secilen hedefe uygun ve yeterince farkli bir sepet alternatifi bulunamadi."
        )

    politika = _YENIDEN_DENGELEME_POLITIKASI[goal]
    son_degerlendirme = evaluated_at or an
    son_degisiklik = changed_at or an
    return IdleCashBasketCatalog(
        goal=goal,
        universe_size=len(assets),
        eligible_asset_count=len(_adaylari_filtrele(context, assets, goal, an)),
        stale_asset_count=sum(_bayat_veri(asset, an) for asset in assets),
        insufficient_history_asset_count=sum(_yetersiz_oynaklik_gecmisi(asset) for asset in assets),
        evaluation_frequency=str(politika["label"]),
        evaluated_at=son_degerlendirme.isoformat(),
        last_changed_at=son_degisiklik.isoformat(),
        next_evaluation_at=(son_degerlendirme + politika["review"]).isoformat(),
        membership_changed=membership_changed,
        stability_note=(
            "Sepet üyeliği bu değerlendirmede değişti."
            if membership_changed
            else "Fiyat ve adetler güncellendi; üyelik değişim eşiği aşılmadığı için korundu."
        ),
        options=secenekler,
    )


def _uyelikler(catalog: IdleCashBasketCatalog) -> list[list[int]]:
    """Eksik alternatiflerde strateji indekslerinin kaymasini onler."""
    indeksler = {str(strategy["key"]): index for index, strategy in enumerate(_SEPET_STRATEJILERI)}
    memberships: list[list[int]] = [[] for _ in _SEPET_STRATEJILERI]
    for option in catalog.options:
        index = indeksler[option.strategy_key]
        memberships[index] = [item.asset_id for item in option.suggestion.items]
    return memberships


def _profil_imzasi(context: dict) -> str:
    profil = str(context.get("risk_tolerance") or VARSAYILAN_PROFIL).upper()
    izinli = sorted(str(c).upper() for c in context.get("allowed_asset_classes") or [])
    return f"basket-v2|{profil}|{','.join(izinli)}"


def _zaman_degeri(value: object, varsayilan: datetime) -> datetime:
    if isinstance(value, datetime):
        sonuc = value
    elif isinstance(value, str):
        try:
            sonuc = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return varsayilan
    else:
        return varsayilan
    return sonuc if sonuc.tzinfo else sonuc.replace(tzinfo=timezone.utc)


def _ortalama_puan(
    asset_ids: set[int],
    asset_map: dict[int, dict],
    profil: str,
    goal: str,
    holdings: dict[int, float],
) -> float:
    puanlar = [
        _puan(asset_map[asset_id], profil, goal, _sayi(holdings.get(asset_id)) > 0)
        for asset_id in asset_ids
        if asset_id in asset_map
    ]
    return sum(puanlar) / len(puanlar) if puanlar else 0.0


def _puan_farki(
    mevcut: list[int],
    aday: list[int],
    asset_map: dict[int, dict],
    profil: str,
    goal: str,
    holdings: dict[int, float],
) -> float:
    cikanlar = set(mevcut) - set(aday)
    girenler = set(aday) - set(mevcut)
    if not cikanlar or not girenler:
        return 0.0
    return _ortalama_puan(girenler, asset_map, profil, goal, holdings) - _ortalama_puan(
        cikanlar, asset_map, profil, goal, holdings
    )


def _oynaklik_acil_cikisi(mevcut: list[int], aday: list[int], asset_map: dict[int, dict]) -> bool:
    olcumler = [
        _sayi(asset.get("volatility_20d_pct"))
        for asset in asset_map.values()
        if _sayi(asset.get("volatility_20d_pct")) > 0
    ]
    if not olcumler:
        return False
    esik = max(4.0, median(olcumler) * 1.5)
    cikanlar = set(mevcut) - set(aday)
    girenler = set(aday) - set(mevcut)
    if not cikanlar or not girenler:
        return False
    cikan_oynaklik = max(
        (_sayi(asset_map[asset_id].get("volatility_20d_pct")) for asset_id in cikanlar),
        default=0.0,
    )
    giren_oynaklik = min(
        (_sayi(asset_map[asset_id].get("volatility_20d_pct")) for asset_id in girenler),
        default=cikan_oynaklik,
    )
    return cikan_oynaklik >= esik and giren_oynaklik < cikan_oynaklik


def _uyelik_anahtari(sepet_sirasi: int, asset_id: int) -> str:
    return f"{sepet_sirasi}:{asset_id}"


def _uyelik_tarihleri(
    state: dict,
    memberships: list[list[int]],
    fallback: datetime,
) -> dict[str, str]:
    kayitli = dict(state.get("membership_since") or {})
    sonuc: dict[str, str] = {}
    for sepet_sirasi, membership in enumerate(memberships):
        for asset_id in membership:
            anahtar = _uyelik_anahtari(sepet_sirasi, asset_id)
            tarih = _tarih(kayitli.get(anahtar)) or fallback
            sonuc[anahtar] = tarih.isoformat()
    return sonuc


def _uyelik_tarihlerini_guncelle(
    onceki_tarihler: dict[str, str],
    yeni_uyelikler: list[list[int]],
    now: datetime,
) -> dict[str, str]:
    return {
        _uyelik_anahtari(sepet_sirasi, asset_id): onceki_tarihler.get(
            _uyelik_anahtari(sepet_sirasi, asset_id), now.isoformat()
        )
        for sepet_sirasi, membership in enumerate(yeni_uyelikler)
        for asset_id in membership
    }


def _degisim_imzasi(mevcut: list[int], aday: list[int]) -> str:
    cikanlar = ",".join(str(asset_id) for asset_id in sorted(set(mevcut) - set(aday)))
    girenler = ",".join(str(asset_id) for asset_id in sorted(set(aday) - set(mevcut)))
    return f"{cikanlar}->{girenler}"


async def _kalici_katalog_olustur(
    repository,
    user_id: int,
    context: dict,
    assets: list[dict],
    holdings: dict[int, float],
    goal: str,
    now: datetime,
) -> IdleCashBasketCatalog:
    """Uyelik degisimini politika ve kalici esik sayaclariyla yonetir."""
    aday_katalog = basket_catalog_build(context, assets, holdings, goal, now=now)
    aday_uyelikler = _uyelikler(aday_katalog)
    profil_imzasi = _profil_imzasi(context)
    politika = _YENIDEN_DENGELEME_POLITIKASI[goal]
    state = await repository.get_basket_state(user_id, goal)

    if state is None:
        uyelik_tarihleri = _uyelik_tarihlerini_guncelle({}, aday_uyelikler, now)
        await repository.upsert_basket_state(
            user_id,
            goal,
            {
                "memberships": aday_uyelikler,
                "breach_counts": {},
                "membership_since": uyelik_tarihleri,
                "change_signals": {},
                "profile_signature": profil_imzasi,
                "evaluated_at": now,
                "changed_at": now,
            },
        )
        return basket_catalog_build(
            context,
            assets,
            holdings,
            goal,
            now=now,
            memberships=aday_uyelikler,
            evaluated_at=now,
            changed_at=now,
        )

    mevcut_uyelikler = [
        [int(asset_id) for asset_id in membership] for membership in state.get("memberships") or []
    ]
    son_degerlendirme = _zaman_degeri(state.get("evaluated_at"), now)
    son_degisiklik = _zaman_degeri(state.get("changed_at"), now)
    uyelik_tarihleri = _uyelik_tarihleri(state, mevcut_uyelikler, son_degisiklik)
    degisim_sinyalleri = dict(state.get("change_signals") or {})

    # Migration oncesi satirlarda varlik bazli giris tarihi yoktur. Ilk okumada
    # eski changed_at degerini koruyarak doldur; degerlendirme saatini ilerletme.
    if mevcut_uyelikler and not state.get("membership_since"):
        await repository.upsert_basket_state(
            user_id,
            goal,
            {
                "memberships": mevcut_uyelikler,
                "breach_counts": state.get("breach_counts") or {},
                "membership_since": uyelik_tarihleri,
                "change_signals": degisim_sinyalleri,
                "profile_signature": state.get("profile_signature") or profil_imzasi,
                "evaluated_at": son_degerlendirme,
                "changed_at": son_degisiklik,
            },
        )

    korunan_katalog = basket_catalog_build(
        context,
        assets,
        holdings,
        goal,
        now=now,
        memberships=mevcut_uyelikler,
        evaluated_at=son_degerlendirme,
        changed_at=son_degisiklik,
    )
    korunan_uyelikler = _uyelikler(korunan_katalog)
    uyelik_gecerli = korunan_uyelikler == mevcut_uyelikler
    profil_degisti = state.get("profile_signature") != profil_imzasi

    if profil_degisti or not uyelik_gecerli:
        secilen_uyelikler = aday_uyelikler
        degisti = secilen_uyelikler != mevcut_uyelikler
        yeni_uyelik_tarihleri = _uyelik_tarihlerini_guncelle(
            uyelik_tarihleri, secilen_uyelikler, now
        )
        await repository.upsert_basket_state(
            user_id,
            goal,
            {
                "memberships": secilen_uyelikler,
                "breach_counts": {},
                "membership_since": yeni_uyelik_tarihleri,
                "change_signals": {},
                "profile_signature": profil_imzasi,
                "evaluated_at": now,
                "changed_at": now if degisti else son_degisiklik,
            },
        )
        return basket_catalog_build(
            context,
            assets,
            holdings,
            goal,
            now=now,
            memberships=secilen_uyelikler,
            evaluated_at=now,
            changed_at=now if degisti else son_degisiklik,
            membership_changed=degisti,
        )

    if now < son_degerlendirme + politika["review"]:
        return korunan_katalog

    profil = str(context.get("risk_tolerance") or VARSAYILAN_PROFIL).upper()
    asset_map = {int(asset["asset_id"]): asset for asset in assets}
    yeni_uyelikler: list[list[int]] = []
    yeni_sayaclar: dict[str, int] = {}
    yeni_sinyaller: dict[str, dict] = {}
    degisti = False

    for index, mevcut in enumerate(mevcut_uyelikler):
        aday = aday_uyelikler[index] if index < len(aday_uyelikler) else mevcut
        anahtar = str(index)
        if aday == mevcut:
            yeni_uyelikler.append(mevcut)
            yeni_sayaclar[anahtar] = 0
            continue

        puan_farki = _puan_farki(mevcut, aday, asset_map, profil, goal, holdings)
        esik_asildi = puan_farki >= float(politika["score_gap"])
        imza = _degisim_imzasi(mevcut, aday)
        onceki_sinyal = degisim_sinyalleri.get(anahtar) or {}
        onceki_sayac = (
            int(onceki_sinyal.get("count") or 0) if onceki_sinyal.get("signature") == imza else 0
        )
        sayac = onceki_sayac + 1 if esik_asildi else 0
        cikanlar = set(mevcut) - set(aday)
        minimum_sure_doldu = all(
            now
            >= (_tarih(uyelik_tarihleri.get(_uyelik_anahtari(index, asset_id))) or now)
            + politika["minimum_hold"]
            for asset_id in cikanlar
        )
        acil_cikis = goal == "LOW_VOLATILITY" and _oynaklik_acil_cikisi(mevcut, aday, asset_map)
        degisim_onayli = acil_cikis or (
            minimum_sure_doldu and sayac >= int(politika["confirmations"])
        )
        yeni_uyelikler.append(aday if degisim_onayli else mevcut)
        yeni_sayaclar[anahtar] = 0 if degisim_onayli else sayac
        if esik_asildi and not degisim_onayli:
            yeni_sinyaller[anahtar] = {
                "signature": imza,
                "count": sayac,
                "observed_at": now.isoformat(),
                "score_gap": round(puan_farki, 2),
            }
        degisti = degisti or degisim_onayli

    yeni_degisiklik = now if degisti else son_degisiklik
    yeni_uyelik_tarihleri = _uyelik_tarihlerini_guncelle(uyelik_tarihleri, yeni_uyelikler, now)
    await repository.upsert_basket_state(
        user_id,
        goal,
        {
            "memberships": yeni_uyelikler,
            "breach_counts": yeni_sayaclar,
            "membership_since": yeni_uyelik_tarihleri,
            "change_signals": yeni_sinyaller,
            "profile_signature": profil_imzasi,
            "evaluated_at": now,
            "changed_at": yeni_degisiklik,
        },
    )
    return basket_catalog_build(
        context,
        assets,
        holdings,
        goal,
        now=now,
        memberships=yeni_uyelikler,
        evaluated_at=now,
        changed_at=yeni_degisiklik,
        membership_changed=degisti,
    )


async def idle_cash_suggestion_for_goal(user_id: int, goal: str) -> IdleCashSuggestion:
    """İşlem merkezi gibi mesaj içermeyen yüzeyler için doğrudan hedefle üretir."""
    repository = get_recommendation_repository()
    context, assets = await asyncio.gather(
        repository.user_context(user_id),
        repository.assets_for_scan(),
    )
    if context is None:
        raise NotFoundError("Bakiye ve risk bilgileri alınamadı.")
    holdings = await repository.holdings_map(int(context["portfolio_id"]))
    return suggestion_build(context, assets, holdings, goal)


async def idle_cash_basket_catalog_for_goal(user_id: int, goal: str) -> IdleCashBasketCatalog:
    """İşlem merkezi için aynı hedefte farklı sepet alternatifleri üretir."""
    repository = get_recommendation_repository()
    context, assets = await asyncio.gather(
        repository.user_context(user_id),
        repository.assets_for_scan(),
    )
    if context is None:
        raise NotFoundError("Bakiye ve risk bilgileri alınamadı.")
    holdings = await repository.holdings_map(int(context["portfolio_id"]))
    return await _kalici_katalog_olustur(
        repository,
        user_id,
        context,
        assets,
        holdings,
        goal,
        datetime.now(timezone.utc),
    )
