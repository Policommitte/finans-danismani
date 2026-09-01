"""Chatbot için kurallı atıl bakiye/sepet önerisi.

Bu servis emir üretmez. Güncel piyasa verisini, kullanıcının risk profilini,
atıl bakiyesini ve mevcut pozisyonlarını kullanarak açıklanabilir bir öneri
hazırlar. Aynı girdiler aynı sıralamayı üretir; LLM finansal hesap yapmaz.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.quantity import adet_yuvarla
from app.repositories.deps import get_recommendation_repository
from app.schemas.idle_cash import (
    IdleCashBasketCatalog,
    IdleCashBasketOption,
    IdleCashSuggestion,
    IdleCashSuggestionItem,
)
from app.services.recommendation import SPK_UYARISI, VARSAYILAN_PROFIL

_OLUMSUZ_KALIPLAR = ("önerme", "onerme", "oluşturma", "olusturma", "istemiyorum")
_NIYET_KALIPLARI = (
    r"at[ıi]l\s+bakiye",
    r"bo[sş]ta\s+(?:duran\s+)?(?:para|nakit)",
    r"(?:nakdimi|nakitimi|bakiyemi|param[ıi])\s+(?:nas[ıi]l\s+)?(?:de[gğ]erlendir|kullan|yat[ıi]r)",
    r"ne\s+(?:almal[ıi]y[ıi]m|alay[ıi]m)",
    r"bakiyem(?:\s+ne\s+kadar|\s+nedir|\s+hakk[ıi]nda)",
    r"hisse\s+sepeti.*(?:[oö]ner|olu[sş]tur|haz[ıi]rla)",
    r"(?:bakiye|nakit).*(?:hisse|sepet|yat[ıi]r[ıi]m).*(?:[oö]ner|olu[sş]tur|haz[ıi]rla)",
)

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
    "LOW": {"FOREX": 12, "GOLD": 12, "ETF": 8, "STOCK": 2, "USA_STOCK": 2,
            "EU_STOCK": 2, "COMMODITY": -8, "CRYPTO": -40},
    "MEDIUM": {"ETF": 8, "STOCK": 5, "USA_STOCK": 5, "EU_STOCK": 5, "GOLD": 5,
               "FOREX": 2, "COMMODITY": 0, "CRYPTO": -8},
    "HIGH": {"CRYPTO": 12, "COMMODITY": 7, "USA_STOCK": 7, "EU_STOCK": 7,
             "STOCK": 6, "ETF": 4, "GOLD": 0, "FOREX": -4},
}

_HEDEF_SINIF_PUANI = {
    "LONG_TERM": {"ETF": 10, "STOCK": 6, "USA_STOCK": 6, "EU_STOCK": 6,
                  "GOLD": 3, "CRYPTO": -10},
    "GROWTH": {"USA_STOCK": 8, "EU_STOCK": 8, "STOCK": 6, "ETF": 4, "CRYPTO": 2},
    "MOMENTUM": {"CRYPTO": 4, "COMMODITY": 2},
    "LOW_VOLATILITY": {"GOLD": 15, "FOREX": 12, "ETF": 8, "CRYPTO": -30,
                       "COMMODITY": -5},
}


def idle_cash_request_mi(message: str) -> bool:
    """Serbest metindeki atıl bakiye/sepet niyetini yakalar."""
    metin = message.casefold().strip()
    if any(kalip in metin for kalip in _OLUMSUZ_KALIPLAR):
        return False
    return any(re.search(kalip, metin) for kalip in _NIYET_KALIPLARI)


def hedef_belirle(message: str) -> str:
    metin = message.casefold()
    if any(k in metin for k in ("uzun vade", "uzun vadeli", "emeklilik", "birikim")):
        return "LONG_TERM"
    koruma_kelimeleri = (
        "sermayemi koru",
        "korumacı",
        "korumaci",
        "düşük risk",
        "dusuk risk",
        "düşük oynaklık",
        "dusuk oynaklik",
    )
    if any(k in metin for k in koruma_kelimeleri):
        return "LOW_VOLATILITY"
    if any(k in metin for k in ("momentum", "kısa vadeli", "kisa vadeli", "trend")):
        return "MOMENTUM"
    if any(k in metin for k in ("büyüme", "buyume", "yüksek getiri", "yuksek getiri", "agresif")):
        return "GROWTH"
    return "LONG_TERM"


def _sayi(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _puan(asset: dict, profil: str, hedef: str, elde_var: bool) -> float:
    gunluk = max(-20.0, min(20.0, _sayi(asset.get("daily_change_pct"))))
    haftalik = max(-40.0, min(40.0, _sayi(asset.get("weekly_change_pct"))))
    yillik = max(-100.0, min(150.0, _sayi(asset.get("yearly_change_pct"))))
    oynaklik = abs(gunluk) + abs(haftalik) * 0.35
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


def _adaylari_filtrele(context: dict, assets: list[dict]) -> list[dict]:
    izinli = {str(c).upper() for c in context.get("allowed_asset_classes") or []}
    return [
        asset
        for asset in assets
        if str(asset.get("asset_class") or "").upper() in _YATIRIM_SINIFLARI
        and (not izinli or str(asset.get("asset_class") or "").upper() in izinli)
        and _sayi(asset.get("current_price")) > 0
    ]


def _sinif_limiti(profil: str, hedef: str, sinif: str, hedef_adet: int) -> int:
    if sinif == "CRYPTO":
        if profil == "LOW" or hedef == "LOW_VOLATILITY":
            return 0
        return 1 if profil == "MEDIUM" else 2
    if sinif in {"GOLD", "FOREX", "COMMODITY"}:
        return 1
    return min(2, hedef_adet)


def suggestion_build(
    context: dict,
    assets: list[dict],
    holdings: dict[int, float],
    goal: str,
    *,
    now: datetime | None = None,
    candidate_offset: int = 0,
) -> IdleCashSuggestion:
    profil = str(context.get("risk_tolerance") or VARSAYILAN_PROFIL).upper()
    if profil not in {"LOW", "MEDIUM", "HIGH"}:
        profil = VARSAYILAN_PROFIL

    idle_balance = _sayi(context.get("idle_balance_try"))
    paper_cash = _sayi(context.get("available_balance"))
    bakiye = idle_balance if idle_balance > 0 else paper_cash
    kaynak = "idle_balance" if idle_balance > 0 else "paper_cash"
    if bakiye <= 0:
        raise BusinessRuleError("Öneri oluşturmak için kullanılabilir bakiye bulunmuyor.")

    izinli = {str(c).upper() for c in context.get("allowed_asset_classes") or []}
    adaylar = _adaylari_filtrele(context, assets)
    if not adaylar:
        raise NotFoundError("Yatırım sepeti için uygun güncel piyasa verisi alınamadı.")

    yatirilabilir = round(bakiye * 0.90, 2)
    sirali = sorted(
        adaylar,
        key=lambda a: (
            -_puan(a, profil, goal, _sayi(holdings.get(int(a["asset_id"]))) > 0),
            str(a.get("symbol", "")),
        ),
    )
    uygun = [
        a for a in sirali
        if adet_yuvarla(
            yatirilabilir / _sayi(a["current_price"]),
            str(a.get("asset_class") or ""),
        ) > 0
    ]
    if not uygun:
        raise BusinessRuleError(
            "Bakiye, uygun varlıklardan alınabilecek en küçük miktar için yetersiz."
        )

    # İşlem merkezindeki alternatif kartlar aynı sıralamanın farklı noktalarından
    # başlar. Sohbet akışı varsayılan 0 değeriyle en yüksek puanlı sepeti korur.
    kaydirma = candidate_offset % len(uygun)
    if kaydirma:
        uygun = uygun[kaydirma:] + uygun[:kaydirma]

    hedef_adet = min(_hedef_varlik_adedi(profil, goal), len(uygun))
    mevcut_siniflar = {str(a.get("asset_class") or "").upper() for a in uygun}
    secilenler: list[dict] = []
    for denenen_adet in range(hedef_adet, 0, -1):
        agirlik_adaylari = _agirliklar(denenen_adet, goal)
        aday_secimler: list[dict] = []
        sinif_sayilari: dict[str, int] = {}
        for asset in uygun:
            sinif = str(asset.get("asset_class") or "").upper()
            limit = (
                denenen_adet
                if len(mevcut_siniflar) == 1
                else _sinif_limiti(profil, goal, sinif, denenen_adet)
            )
            if sinif_sayilari.get(sinif, 0) >= limit:
                continue
            agirlik = agirlik_adaylari[len(aday_secimler)]
            if adet_yuvarla(
                yatirilabilir * agirlik / _sayi(asset["current_price"]), sinif
            ) <= 0:
                continue
            aday_secimler.append(asset)
            sinif_sayilari[sinif] = sinif_sayilari.get(sinif, 0) + 1
            if len(aday_secimler) == denenen_adet:
                break
        if len(aday_secimler) == denenen_adet:
            secilenler = aday_secimler
            break

    if not secilenler:
        raise BusinessRuleError("Bakiye, seçilen dağılımla yatırım yapmaya yeterli değil.")

    agirliklar = _agirliklar(len(secilenler), goal)
    kalemler: list[IdleCashSuggestionItem] = []
    hedef_adi = _HEDEF_ACIKLAMALARI[goal]
    for asset, agirlik in zip(secilenler, agirliklar):
        fiyat = _sayi(asset["current_price"])
        sinif = str(asset.get("asset_class") or "").upper()
        miktar = adet_yuvarla(yatirilabilir * agirlik / fiyat, sinif)
        tutar = round(miktar * fiyat, 2)
        elde_var = _sayi(holdings.get(int(asset["asset_id"]))) > 0
        kalemler.append(
            IdleCashSuggestionItem(
                asset_id=int(asset["asset_id"]),
                symbol=str(asset["symbol"]),
                name=str(asset.get("name") or asset["symbol"]),
                asset_class=sinif,
                quantity=round(miktar, 6),
                reference_price=round(fiyat, 2),
                estimated_amount=tutar,
                weight_pct=round(agirlik * 100, 1),
                rationale=[
                    f"{profil} risk profili, {hedef_adi} hedefi ve "
                    f"{_SINIF_ADLARI.get(sinif, sinif)} özellikleriyle uyumlu puanlandı.",
                    "Mevcut portföyünüzde bulunmadığı için çeşitlendirmeye katkı sağlayabilir."
                    if not elde_var else
                    "Mevcut pozisyonunuz dikkate alınarak daha düşük öncelikle değerlendirildi.",
                ],
            )
        )

    toplam = round(sum(k.estimated_amount for k in kalemler), 2)
    izin_ozeti = (
        ", ".join(sorted(_SINIF_ADLARI.get(sinif, sinif) for sinif in izinli))
        if izinli else "tüm işlem yapılabilir varlık sınıfları"
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
        generated_at=(now or datetime.now(timezone.utc)).isoformat(),
    )


def basket_catalog_build(
    context: dict,
    assets: list[dict],
    holdings: dict[int, float],
    goal: str,
    *,
    now: datetime | None = None,
) -> IdleCashBasketCatalog:
    """Aynı hedef için en fazla üç, gerçekten farklı sepet alternatifi üretir."""
    profil = str(context.get("risk_tolerance") or VARSAYILAN_PROFIL).upper()
    if profil not in {"LOW", "MEDIUM", "HIGH"}:
        profil = VARSAYILAN_PROFIL

    hedef_adet = _hedef_varlik_adedi(profil, goal)
    oncelikli_kaydirmalar = [0, hedef_adet, hedef_adet * 2]
    kaydirmalar = list(dict.fromkeys(oncelikli_kaydirmalar + list(range(len(assets)))))
    secenekler: list[IdleCashBasketOption] = []
    gorulenler: set[tuple[tuple[int, float], ...]] = set()

    for kaydirma in kaydirmalar:
        suggestion = suggestion_build(
            context,
            assets,
            holdings,
            goal,
            now=now,
            candidate_offset=kaydirma,
        )
        imza = tuple((item.asset_id, item.weight_pct) for item in suggestion.items)
        if imza in gorulenler:
            continue
        gorulenler.add(imza)

        sira = len(secenekler)
        secenekler.append(
            IdleCashBasketOption(
                id=f"{goal.lower()}-{sira + 1}",
                title=_SEPET_BASLIKLARI[goal][sira],
                summary=_SEPET_OZETLERI[sira],
                suggestion=suggestion,
            )
        )
        if len(secenekler) == 3:
            break

    return IdleCashBasketCatalog(
        goal=goal,
        universe_size=len(assets),
        eligible_asset_count=len(_adaylari_filtrele(context, assets)),
        options=secenekler,
    )


async def idle_cash_suggestion_getir(user_id: int, message: str) -> IdleCashSuggestion:
    return await idle_cash_suggestion_for_goal(user_id, hedef_belirle(message))


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
    return basket_catalog_build(context, assets, holdings, goal)
