"""Risk skorlama - sayinin TEK kaynagi.

Hem `RiskStrategyAgent` hem `GET /api/risk/profile` bu fonksiyonu cagirir.
Skor iki yerde hesaplansaydi dashboard ile sohbet farkli sayi gosterirdi
(mimari v4 bolum 5.5).

Skor DETERMINISTIKTIR: LLM kullanmaz, ayni girdi her zaman ayni sayiyi verir.
Ajan yalnizca sonucu yorumlar.

SKOR BILESENLERI (0-100, yuksek = riskli)
    yogunlasma  (0-40)  Tek varlik siniftaki agirlik - cesitlendirme eksikligi
    varlik tipi (0-35)  Sinif bazli temel risk (kripto > hisse > altin > tahvil)
    oynaklik    (0-15)  Olculebilen varliklarin gecmis oynakligi
    tek pozisyon(0-10)  En buyuk TEK varligin portfoydeki payi

Bu agirliklar bir sektor standardi degil, projenin acikladigi ve savunabildigi
basit bir modeldir; degistirilirse tek yer burasidir.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

#: Varlik sinifi -> 0-1 arasi temel risk katsayisi.
ASSET_CLASS_RISK: dict[str, float] = {
    "CRYPTO": 1.00,
    "USA_STOCK": 0.65,
    "EU_STOCK": 0.65,
    "STOCK": 0.60,
    "FOREX": 0.40,
    "GOLD": 0.30,
    "BOND": 0.10,
}

#: Beyan edilen tolerans -> skorun "rahat" kabul edilen ust siniri.
TOLERANCE_LIMITS: dict[str, int] = {"LOW": 35, "MEDIUM": 60, "HIGH": 80}

RISK_LEVELS = (
    (35, "dusuk"),
    (60, "orta"),
    (80, "yuksek"),
    (101, "cok yuksek"),
)

#: Oynaklik olcumunun penceresi (gun) ve kac varlikta olculecegi.
#:
#: SAYININ TEK KAYNAGI BURASI: hem `RiskStrategyAgent` (sohbet yolu) hem
#: `risk_profili_getir` (dashboard yolu) bu degerleri kullanir. Ayri ayri
#: tanimlansalardi iki taraf farkli sayida varlik olcup FARKLI SKOR uretirdi -
#: kullanici ekranda 70, sohbette 77 gorurdu (27 Agustos 2026'da tam olarak
#: bu yasandi, o zaman dashboard oynakligi HIC olcmuyordu).
VOLATILITY_WINDOW_DAYS = 30
MAX_VOLATILITY_LOOKUPS = 3

ASSET_CLASS_LABELS_TR: dict[str, str] = {
    "CRYPTO": "Kripto",
    "USA_STOCK": "ABD hissesi",
    "EU_STOCK": "Avrupa hissesi",
    "STOCK": "Hisse",
    "FOREX": "Döviz",
    "GOLD": "Altın",
    "BOND": "Tahvil",
}


def oynaklik_yuzdesi(prices: list[float]) -> float:
    """Fiyat serisinin oynakligi: ortalamaya gore standart sapmanin yuzdesi.

    HEM MCP tool'u (`market_get_history`) HEM dashboard servisi bu fonksiyonu
    cagirir. Formul iki yerde ayri yazilsaydi, ayni portfoy icin iki farkli
    oynaklik - dolayisiyla iki farkli risk skoru - uretilebilirdi.
    """
    if not prices:
        return 0.0
    ortalama = sum(prices) / len(prices)
    if not ortalama:
        return 0.0
    varyans = sum((p - ortalama) ** 2 for p in prices) / len(prices)
    return (varyans**0.5) / ortalama * 100


def risk_profili_hesapla(
    holdings: list[dict],
    allocation: list[dict],
    risk_tolerance: str | None = None,
    volatility_by_symbol: dict[str, float] | None = None,
) -> dict:
    """Portfoy risk profilini hesaplar.

    Args:
        holdings: `market_value_try` ve `asset_class` alanlarini tasiyan
            varlik satirlari (MCP tool ciktisi ya da repository satiri).
        allocation: Varlik sinifi bazinda dagilim (`asset_class`, `class_pct`).
        risk_tolerance: Kullanicinin beyani (LOW | MEDIUM | HIGH).
        volatility_by_symbol: Olculebilmis oynakliklar (yuzde).

    Returns:
        `risk_score`, `risk_level`, bilesen kirilimi, gerekceler ve oneriler.
        Portfoy bossa skor 0 doner - "veri yok" ile "risksiz" karisMasin diye
        `holding_count` de dondurulur.
    """
    volatility_by_symbol = volatility_by_symbol or {}
    toplam = sum(float(h.get("market_value_try") or 0) for h in holdings)

    if not holdings or toplam <= 0:
        return {
            "risk_score": 0,
            "risk_level": "hesaplanamadi",
            "risk_tolerance": risk_tolerance,
            "holding_count": 0,
            "components": {},
            "top_class": None,
            "top_class_pct": None,
            "reasons": ["Portföyde değer taşıyan varlık bulunmadığı için risk hesaplanamadı."],
            "suggestions": [],
            "tolerance_alignment": "bilinmiyor",
        }

    # --- 1) Yogunlasma: en buyuk varlik sinifinin payi ---
    dagilim = allocation or _dagilim_uret(holdings, toplam)
    en_buyuk = max(dagilim, key=lambda d: float(d.get("class_pct") or 0))
    en_buyuk_pct = float(en_buyuk.get("class_pct") or 0)
    # %100 tek sinif -> 40 puan, %25 ve alti -> 0 puan (dengeli kabul).
    yogunlasma = _kirp((en_buyuk_pct - 25) / 75 * 40, 0, 40)

    # --- 2) Varlik tipi: sinif risklerinin deger agirlikli ortalamasi ---
    agirlikli = sum(
        ASSET_CLASS_RISK.get(str(d.get("asset_class") or "").upper(), 0.5)
        * float(d.get("class_pct") or 0)
        for d in dagilim
    )
    tip_riski = _kirp(agirlikli / 100 * 35, 0, 35)

    # --- 3) Oynaklik: olculebilenlerin ortalamasi (%8 ve ustu tam puan) ---
    if volatility_by_symbol:
        ortalama_oynaklik = sum(volatility_by_symbol.values()) / len(volatility_by_symbol)
        oynaklik_puani = _kirp(ortalama_oynaklik / 8 * 15, 0, 15)
    else:
        ortalama_oynaklik = None
        oynaklik_puani = 0.0

    # --- 4) Tek pozisyon yogunlugu ---
    en_buyuk_varlik = max(holdings, key=lambda h: float(h.get("market_value_try") or 0))
    tek_pozisyon_pct = float(en_buyuk_varlik.get("market_value_try") or 0) / toplam * 100
    tek_pozisyon = _kirp((tek_pozisyon_pct - 30) / 70 * 10, 0, 10)

    skor = round(yogunlasma + tip_riski + oynaklik_puani + tek_pozisyon)
    seviye = next(ad for sinir, ad in RISK_LEVELS if skor < sinir)

    gerekceler = _gerekceler(
        en_buyuk_sinif=str(en_buyuk.get("asset_class")),
        en_buyuk_pct=en_buyuk_pct,
        en_buyuk_varlik=str(en_buyuk_varlik.get("symbol")),
        tek_pozisyon_pct=tek_pozisyon_pct,
        ortalama_oynaklik=ortalama_oynaklik,
        holding_count=len(holdings),
    )
    uyum, oneriler = _tolerans_uyumu(skor, risk_tolerance, en_buyuk.get("asset_class"))

    return {
        "risk_score": skor,
        "risk_level": seviye,
        "risk_tolerance": risk_tolerance,
        "holding_count": len(holdings),
        "components": {
            "concentration": round(yogunlasma, 1),
            "asset_type": round(tip_riski, 1),
            "volatility": round(oynaklik_puani, 1),
            "single_position": round(tek_pozisyon, 1),
        },
        "top_class": en_buyuk.get("asset_class"),
        "top_class_pct": round(en_buyuk_pct, 2),
        "avg_volatility_pct": round(ortalama_oynaklik, 2) if ortalama_oynaklik else None,
        "reasons": gerekceler,
        "suggestions": oneriler,
        "tolerance_alignment": uyum,
    }


def _dagilim_uret(holdings: list[dict], toplam: float) -> list[dict]:
    """Dagilim verilmediyse varlik satirlarindan uretir."""
    by_class: dict[str, float] = {}
    for holding in holdings:
        sinif = str(holding.get("asset_class") or "DIGER").upper()
        by_class[sinif] = by_class.get(sinif, 0.0) + float(holding.get("market_value_try") or 0)

    return [
        {"asset_class": sinif, "class_pct": deger / toplam * 100}
        for sinif, deger in by_class.items()
    ]


def _gerekceler(
    en_buyuk_sinif: str,
    en_buyuk_pct: float,
    en_buyuk_varlik: str,
    tek_pozisyon_pct: float,
    ortalama_oynaklik: float | None,
    holding_count: int,
) -> list[str]:
    sinif_etiketi = ASSET_CLASS_LABELS_TR.get(en_buyuk_sinif.upper(), en_buyuk_sinif)
    gerekceler = [
        f"Portföyün %{en_buyuk_pct:.0f}'i {sinif_etiketi} sınıfında.",
    ]
    if tek_pozisyon_pct >= 40:
        gerekceler.append(
            f"Tek bir varlık ({en_buyuk_varlik}) portföyün %{tek_pozisyon_pct:.0f}'ini oluşturuyor."
        )
    if holding_count <= 3:
        gerekceler.append(f"Portföyde yalnızca {holding_count} varlık var.")
    if ortalama_oynaklik is not None and ortalama_oynaklik >= 4:
        gerekceler.append(f"Ölçülen ortalama günlük oynaklık %{ortalama_oynaklik:.1f} ile yüksek.")
    return gerekceler


def _tolerans_uyumu(skor: int, risk_tolerance: str | None, en_buyuk_sinif) -> tuple[str, list[str]]:
    """Skoru kullanicinin beyan ettigi toleransla karsilastirir."""
    oneriler: list[str] = []
    sinif_kodu = str(en_buyuk_sinif or "")
    sinif_etiketi = ASSET_CLASS_LABELS_TR.get(sinif_kodu.upper(), sinif_kodu)

    if skor >= 60:
        oneriler.append(
            f"{sinif_etiketi} ağırlığını düşürüp daha düşük riskli sınıflara "
            "(tahvil, altın) pay ayırmak çeşitlendirmeyi artırır."
        )

    if not risk_tolerance:
        return "bilinmiyor", oneriler

    sinir = TOLERANCE_LIMITS.get(str(risk_tolerance).upper())
    if sinir is None:
        return "bilinmiyor", oneriler

    if skor > sinir:
        oneriler.append(
            f"Portföy riski beyan edilen '{risk_tolerance}' toleransın üstünde; "
            "yeniden dengeleme değerlendirilebilir."
        )
        return "tolerans ustu", oneriler

    if skor < sinir - 25:
        return "tolerans alti", oneriler

    return "uyumlu", oneriler


def _kirp(value: float, alt: float, ust: float) -> float:
    return max(alt, min(value, ust))


# ---------------------------------------------------------------------------
# Servis katmani - endpoint ve ajan AYNI fonksiyonu cagirir
# ---------------------------------------------------------------------------


async def risk_profili_getir(user_id: int, portfolio_id: int | None = None) -> dict:
    """Kullanicinin risk profilini uretir (`GET /api/risk/profile`).

    Ayni hesap `RiskStrategyAgent` icinde de kullanilir; ajan verileri MCP
    tool'lari uzerinden alir, bu fonksiyon repository'den okur - SONUC AYNIDIR,
    cunku skor `risk_profili_hesapla` icinde tek yerde hesaplanir.
    """
    from app.repositories.deps import get_portfolio_repository, get_user_repository

    portfolio_repository = get_portfolio_repository()
    holdings = await portfolio_repository.get_holdings(user_id, portfolio_id)
    allocation = await portfolio_repository.get_allocation(user_id, portfolio_id)
    user = await get_user_repository().get_by_id(user_id)
    oynakliklar = await _oynakliklari_olc(holdings)

    return risk_profili_hesapla(
        holdings=[
            {
                "symbol": h.get("symbol"),
                "asset_class": h.get("asset_class"),
                "market_value_try": h.get("market_value_try"),
            }
            for h in holdings
        ],
        allocation=[
            {"asset_class": a.get("asset_class"), "class_pct": a.get("class_pct")}
            for a in allocation
        ],
        risk_tolerance=(user or {}).get("risk_tolerance"),
        volatility_by_symbol=oynakliklar,
    )


async def _oynakliklari_olc(holdings: list[dict]) -> dict[str, float]:
    """En buyuk pozisyonlarin gecmis oynakligini olcer.

    ⚠️ AJAN YOLUYLA BIREBIR AYNI OLMAK ZORUNDA. Burasi eskiden HIC olcmuyordu
    ("dashboard ilk yuklemesini yavaslatmamak icin" denmisti) ve sonucu su
    oldu: skorun 0-15 puanlik oynaklik bileseni dashboard'da hep 0 kaliyor,
    ayni portfoy icin ekranda 70, sohbette 77 goruluyordu. Kullanici "ekrandaki
    risk skorum kac?" diye sordugunda asistan kendi hesapladigi 77'yi
    "ekrandaki skor" diye sunuyordu - yani yanlis bir atif uretiliyordu.

    Ayni sirayi ve pencereyi kullanmak SART: `portfolio_get_holdings` MCP
    tool'u da ayni repository metodunu (deger sirali) cagirir, bu yuzden
    `[:MAX_VOLATILITY_LOOKUPS]` iki tarafta ayni varliklari secer.

    Tek bir sembolun gecmisi okunamazsa o sembol ATLANIR; risk profili
    tamamen dusmez (ajan tarafindaki davranisin aynisi).
    """
    from app.repositories.deps import get_market_repository

    market_repository = get_market_repository()
    semboller = [str(h["symbol"]) for h in holdings[:MAX_VOLATILITY_LOOKUPS] if h.get("symbol")]
    if not semboller:
        return {}

    # PARALEL: sorgular birbirinden bagimsiz. Sirayla calistirildiginda uzak
    # veritabaninda (Supabase ap-south-1) sorgu basina ~645 ms gidis-donus
    # birikiyordu; olculdu: 3 sembol sirayla 1.935 ms, paralel ~700 ms.
    # `dashboard.ozet_getir` de zaten ayni deseni (gather) kullaniyor.
    seriler = await asyncio.gather(
        *(market_repository.get_history(s, days=VOLATILITY_WINDOW_DAYS) for s in semboller),
        # Tek sembolun gecmisi okunamazsa TUM risk profili dusmemeli;
        # hata nesne olarak doner ve asagida atlanir (ajan yolundaki
        # `except: continue` davranisinin aynisi).
        return_exceptions=True,
    )

    sonuc: dict[str, float] = {}
    for sembol, seri in zip(semboller, seriler, strict=True):
        if isinstance(seri, BaseException):
            logger.debug("oynaklik olculemedi", extra={"symbol": sembol, "hata": str(seri)[:120]})
            continue
        if seri:
            sonuc[sembol] = round(oynaklik_yuzdesi([float(p["price"]) for p in seri]), 2)

    return sonuc
