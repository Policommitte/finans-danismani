"""Bulten sayfasi domain servisi.

`rag.documents` zaten RAG ingestion'i icin var olan haber tablosu; bu servis
onu ARAMA degil, duz bir liste olarak bultene sunar (bkz. repositories/base.py
-> RagRepository.list_news).
"""

from __future__ import annotations

import asyncio
import re

from app.repositories.deps import get_market_repository, get_rag_repository
from app.schemas.market import NewsArticle, NewsListResponse
from app.services.pexels import search_photo

#: Ozette gonderilen metin uzunlugu (kart arayuzunde tam metin gerekmez).
EXCERPT_LENGTH = 240
FALLBACK_TITLE_LENGTH = 72

_BYLINE_PREFIX = re.compile(r"^[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ]{2,}\s+")

_TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Dolar/TL", ("dolar/tl",)),
    ("BIST 100", ("bist 100",)),
    ("Ons altın", ("ons altın", "ons fiyat", "spot altın")),
    ("Gram altın", ("gram altın",)),
    ("Altın fiyatları", ("altın", "değerli metal", "ons fiyat")),
    ("Döviz piyasası", ("döviz", "dolar", "euro", "kur ")),
    ("Borsa", ("borsa", "bist", "hisse sen")),
    ("Kripto varlıklar", ("kripto", "bitcoin", "ethereum")),
    ("Petrol fiyatları", ("petrol", "brent", "ham petrol")),
    ("Piyasalar", ("piyasa",)),
    ("Enflasyon", ("enflasyon", "tüfe")),
    ("Faizler", ("faiz",)),
)

# Fiyat sonucundan önce haberin asıl olayını anlatan kurallar denenir. Kurallar
# belge ID'sine değil metindeki olay türüne bağlıdır; aynı türdeki yeni haberler
# de otomatik olarak uygun başlığı alır.
_CONTENT_TITLE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("tüfe", "altın piyasası"), "TÜFE verisi öncesinde altın piyasası"),
    (
        ("değerli metal", "orta doğu", "fed"),
        "Fed ve Orta Doğu gelişmeleri değerli metalleri şekillendiriyor",
    ),
    (("altın", "gümüş", "haftalık"), "Altın ve gümüşte haftalık piyasa görünümü"),
    (("yükseliş serisini", "fed"), "Altında yükseliş serisi ve Fed beklentileri"),
    (("kilogram fiyatı", "işlem hacmi"), "Kıymetli madenler piyasasında fiyat ve işlem hacmi"),
    (("iki ayın en yüksek", "enflasyon"), "Enflasyon verileri sonrası altının seyri"),
    (("enflasyon verileri", "kâr realizasyonu"), "ABD enflasyon verileri ve altın fiyatları"),
    (("spot altın", "gram altın", "çeyrek altın"), "Ons ve gram altında güncel görünüm"),
    (("dolar/tl", "rekor kır"), "Dolar/TL rekor seviyeyi test etti"),
    (("dolar endeksi", "dar bant"), "Dolar endeksi ve TL kurlarında dar bant görünümü"),
    (
        ("dolar/tl", "üretici enflasyonu", "eylül toplantısı"),
        "ABD enflasyon verileri Fed beklentilerini öteledi",
    ),
    (
        ("dolar/tl", "perakende satışlar", "tüketici güven"),
        "ABD verileri Fed beklentilerini değiştirdi",
    ),
    (("dolar/tl", "orta doğu", "fed"), "Fed ve Orta Doğu gelişmeleri döviz piyasasının odağında"),
    (("dolar/tl", "fed"), "Fed beklentileri döviz piyasasını şekillendiriyor"),
    (("dolar/tl", "euro/tl", "sterlin/tl"), "Dolar/TL ve çapraz kurlarda güncel görünüm"),
    (("bist 100", "haftayı"), "BIST 100 ve sektörlerin haftalık görünümü"),
    (("bist 100", "günün ilk yarısında"), "BIST 100'de gün ortası sektör görünümü"),
    (("bist 100", "14.000 puan"), "BIST 100'de alımlar ve 14 bin puan eşiği"),
    (("vadeli endeks kontratı", "açılış"), "Vadeli piyasada endeks kontratı görünümü"),
    (
        ("ticaret bakanlığı", "ilan", "denetim"),
        "Ticaret Bakanlığı ilan denetiminin sonuçlarını açıkladı",
    ),
    (
        ("elektronik gürültü filtresi", "projesi geliştirildi"),
        "Elektronik Gürültü Filtresi projesi geliştirildi",
    ),
    (("tgfe",), "TCMB ticari gayrimenkul fiyat verilerini açıkladı"),
    (("motorlu kara taşıtları", "temmuz"), "TÜİK temmuz ayı taşıt istatistiklerini açıkladı"),
    (("aile ve gençlik fonu", "madencilik"), "Aile ve Gençlik Fonu'nun kaynak yapısı açıklandı"),
    (("insansız deniz aracı", "deniz mayınlama"), "MARLİN insansız deniz aracına yeni kabiliyet"),
    (
        ("elektronik haberleşme sektörü", "işletmeci sayısı"),
        "Elektronik haberleşme sektörünün güncel görünümü",
    ),
    (("bütçe uygulama sonuçları", "temmuz"), "Temmuz ayı bütçe uygulama sonuçları açıklandı"),
    (("çamlıhemşin tünelli geçişi", "açılış"), "Çamlıhemşin Tünelli Geçişi hizmete açıldı"),
    (("hamsi", "ihracat"), "Türkiye'nin hamsi ihracatında yedi aylık görünüm"),
    (("mehmet şimşek", "mali disiplin"), "Şimşek'ten mali disiplin ve bütçe mesajı"),
    (("oyak çimento", "yeni yapılanma"), "OYAK Çimento'dan yeni yapılanma açıklaması"),
    (
        ("kayseri şeker", "sermaye avansı"),
        "Kayseri Şeker bağlı ortaklığına sermaye avansı aktaracak",
    ),
    (
        ("küresel piyasalar", "orta doğu", "temkinli"),
        "Orta Doğu belirsizliği küresel piyasaların odağında",
    ),
    (
        ("jeopolitik gelişmeler", "piyasaların yönü"),
        "Jeopolitik gelişmeler piyasaların yönünü belirliyor",
    ),
    (("anma pulu", "ilk gün zarfı"), "Anma pulu ve ilk gün zarfı satışa çıktı"),
    (("brent petrol", "hürmüz boğazı"), "Hürmüz Boğazı gelişmeleri petrol piyasasının odağında"),
    (("inşaat üretim endeksi", "haziran"), "TÜİK haziran ayı inşaat üretim verilerini açıkladı"),
    (
        ("türkiye buluşması", "diaspora"),
        "DTİK Türkiye Buluşması diaspora temsilcilerini bir araya getirdi",
    ),
    (
        ("piyasa katılımcıları anketi", "ağustos"),
        "TCMB ağustos ayı piyasa beklentilerini yayımladı",
    ),
    (
        ("küresel piyasalarda", "risk iştahı", "orta doğu"),
        "Enflasyon ve Orta Doğu gündemi risk iştahını şekillendiriyor",
    ),
    (("uzay kampı türkiye", "crew dragon"), "Uzay Kampı Türkiye'de Crew Dragon deneyimi"),
    (("kurumlar vergisi", "ilk 100"), "Kurumlar vergisinde ilk 100 mükellefin sektör dağılımı"),
    (
        ("petrol fiyatları", "enerji üreticileri", "trump"),
        "Petrol fiyatları ABD enerji politikasını zorluyor",
    ),
    (("tbb risk merkezi", "nakdi krediler"), "TBB haziran ayı kredi görünümünü yayımladı"),
    (("son 25 yılda", "ticarette", "dönüşüm"), "Türkiye'nin ticarette 25 yıllık dönüşümü"),
    (("indirimli bilet", "kktc"), "KKTC uçuşları için indirimli bilet kampanyası"),
    (("araç almak isteyen", "kredi faizleri"), "Otomobil alımında fiyat ve finansman ikilemi"),
    (("fitch", "kredi notu", "aa+"), "Fitch ABD'nin kredi notunu ve görünümünü teyit etti"),
)


def _content_title(context: str) -> str | None:
    return next(
        (
            title
            for keywords, title in _CONTENT_TITLE_RULES
            if all(keyword in context for keyword in keywords)
        ),
        None,
    )


def _specific_title(context: str, topic: str) -> str | None:
    """Haberdeki tek bir ayırt edici ayrıntıyla kısa başlık oluşturur."""
    if "enflasyon" in context and "piyasa" in context and "hareketlen" in context:
        return "ABD enflasyon verileri piyasaları hareketlendirdi"

    if "yükselişi destek" in context and topic in {"Ons altın", "Gram altın", "Altın fiyatları"}:
        return "Küresel gelişmeler değerli metallerdeki yükselişi destekliyor"

    period = r"(\d+|bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on)"
    match = re.search(rf"son\s+{period}\s+ayın\s+en\s+güçlü\s+performans", context)
    if match:
        return f"{topic} son {match.group(1)} ayın en güçlü performansını gösterdi"

    match = re.search(rf"{period}\s+ayın\s+en\s+yüksek\s+seviye", context)
    if match:
        return f"{topic} son {match.group(1)} ayın zirvesine yaklaştı"

    match = re.search(r"yükseliş\s+serisini\s+([^,.]{1,24}güne)\s+taşıdı", context)
    if match:
        return f"{topic} yükselişini {match.group(1)} taşıdı"

    if "tüfe" in context and "yukarı yönlü ivme" in context:
        return "TÜFE öncesi altındaki yükseliş hızlandı"

    match = re.search(
        r"yüzde\s+(\d+(?:,\d+)?)\s+(?:artışla|yükselerek|artarak|değer kazan)", context
    )
    if match:
        if "kilogram fiyatı" in context and "altın" in context:
            return f"Altının kilogram fiyatı yüzde {match.group(1)} yükseldi"
        return f"{topic} yüzde {match.group(1)} yükseldi"

    match = re.search(
        r"yüzde\s+(\d+(?:,\d+)?)\s+(?:azalışla|düşerek|gerileyerek|değer kay)", context
    )
    if match:
        return f"{topic} yüzde {match.group(1)} geriledi"

    if "rekor kır" in context:
        return f"{topic} rekor tazeledi"

    if "yatay sey" in context:
        return f"{topic} yatay seyretti"

    return None


_CATEGORY_TOPICS = {
    "altin": "Altın fiyatları",
    "doviz": "Döviz piyasası",
    "hisse": "Borsa",
    "kripto": "Kripto varlıklar",
    "ekonomi": "Ekonomi",
    "piyasa": "Piyasalar",
}

_TREND_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rekor seviyelerde", ("rekor",)),
    (
        "yükselişte",
        ("yükseli", "yüksel", "artış", "arttı", "artarak", "güçlen", "yukarı yön", "en yüksek"),
    ),
    (
        "geriliyor",
        (
            "düşüş",
            "düştü",
            "azalış",
            "azaldı",
            "geriledi",
            "geriliyor",
            "gerileyerek",
            "değer kayb",
        ),
    ),
    ("hareketli seyrediyor", ("dalgal", "oynak", "hareketli", "hareketlen")),
    ("için riskler gündemde", ("risk", "endişe", "belirsiz")),
)


def _fallback_title(raw_text: str, kategori: str | None = None) -> str:
    """Başlıksız haber için yarım cümle üretmeden kısa bir özet başlık kurar."""
    text = " ".join(raw_text.split()).strip()
    if not text:
        return "Piyasa haberi"

    text = _BYLINE_PREFIX.sub("", text, count=1)
    sentence_end = re.search(r"[.!?](?=\s|$)", text)
    candidate = text[: sentence_end.end()] if sentence_end else text

    context = text[:1500].casefold()
    content_title = _content_title(context)
    if content_title:
        return content_title

    if len(candidate) <= FALLBACK_TITLE_LENGTH:
        return candidate

    normalized = candidate.casefold()
    topic = next(
        (
            label
            for label, keywords in _TOPIC_RULES
            if any(keyword in normalized for keyword in keywords)
        ),
        _CATEGORY_TOPICS.get((kategori or "").casefold(), "Piyasalar"),
    )

    specific = _specific_title(context, topic)
    if specific:
        return specific

    # Finans haberlerinde sonuç çoğunlukla cümlenin sonunda verilir. Birden
    # fazla sinyal varsa sondaki sinyali seçmek, örneğin "gerilimin azalmasıyla
    # altın yükseldi" cümlesini yanlışlıkla düşüş olarak etiketlemeyi önler.
    trend_matches = [
        (normalized.rfind(keyword), phrase)
        for phrase, keywords in _TREND_RULES
        for keyword in keywords
        if keyword in normalized
    ]
    trend = max(trend_matches, default=(-1, "gündemde"), key=lambda item: item[0])[1]
    return f"{topic} {trend}"


_THY_IMAGE = "/news/thy-plane.jpg.webp"
_SASA_IMAGE = "/news/sasa-factory.jpg.jfif"
_CRYPTO_IMAGE = "/news/crypto-coins.jpg.jfif"
_TCMB_IMAGE = "/news/tcmb-economy.jpg.jpg"
_TBMM_IMAGE = "/news/tbmm-economy.jpg.webp"
_DEFAULT_IMAGE = "/news/finance-coins-chart.jpg.png"

#: Basliktaki ozel/taninan (elle secilmis marka) anahtar kelimeler -> yerel
#: gorsel. Pexels'e istek atmadan ONCE denenir: API kotasi harcamaz, ag
#: gerektirmez ve bu birkac sirket/varlik icin zaten temaya birebir uygundur.
_KEYWORD_IMAGE_RULES: list[tuple[tuple[str, ...], str]] = [
    (("thy", "havayolu", "havacılık", "havacilik", "uçuş", "ucus", "yolcu"), _THY_IMAGE),
    (("kripto", "bitcoin", "btc", "ethereum"), _CRYPTO_IMAGE),
    (("sasa",), _SASA_IMAGE),
]

#: Pexels basarisiz olursa (anahtar tanimsiz, hata, sonuc yok, kota doldu)
#: EN SON CARE olarak dusulen kategori bazli sabit gorseller. Bilerek DB'ye
#: YAZILMAZ (bkz. resolve_image) - kalici hata degil, gecici bir durum olabilir.
_CATEGORY_FALLBACK_IMAGE: dict[str, str] = {
    "doviz": _TCMB_IMAGE,
    "altin": _TCMB_IMAGE,
    "ekonomi": _TBMM_IMAGE,
    "hisse": _DEFAULT_IMAGE,
    "piyasa": _DEFAULT_IMAGE,
}

#: `rag.documents.kategori` gercek degeri -> Pexels'te aranacak Ingilizce
#: terim ADAYLARI (tek sabit terim degil!). Ayni kategorideki onlarca haber
#: (orn. 66 "doviz" haberi) TEK bir terimi paylasirsa, sonuc-indeksi farkli
#: olsa bile hepsi gorsel olarak birbirine cok benzer cikiyordu (ayni dar
#: konudaki stok fotograflar). Haber ID'sine gore bu listeden de FARKLI bir
#: terim secilerek hem arama sonucu hem de secilen aday cesitlendirilir.
#: Kategori kontrollu bir kelime dagarcigi oldugu icin cevirisi guvenilir
#: (bkz. 2026-08-24 kategori dagilimi: doviz, ekonomi, hisse, altin, piyasa).
_KATEGORI_SEARCH_TERMS: dict[str, list[str]] = {
    "altin": ["gold bars", "gold bullion", "gold price chart", "precious metal", "gold jewelry"],
    "doviz": [
        "currency exchange money",
        "foreign currency banknotes",
        "exchange rate board",
        "dollar euro banknotes",
        "money currency close up",
    ],
    "hisse": [
        "stock market trading",
        "stock exchange screen",
        "trading floor",
        "stock chart candlestick",
        "investor analyzing charts",
    ],
    "ekonomi": [
        "economy finance",
        "business economy growth",
        "financial district city",
        "economic report documents",
        "global economy graph",
    ],
    "piyasa": [
        "financial market",
        "market trading floor",
        "financial data screen",
        "global markets",
        "stock ticker display",
    ],
}

#: Basliktaki daha spesifik bir anahtar kelime, kategori eslesmesinden ONCE
#: denenir: "faiz" gecen bir haber "ekonomi" kategorisinde olsa da "interest
#: rate" aramasi "economy finance"den daha isabetli bir fotograf getirir.
_TITLE_SEARCH_TERM_RULES: list[tuple[tuple[str, ...], str]] = [
    (("petrol", "brent", "opec"), "oil rig industry"),
    (("merkez bankası", "merkez bankasi", "tcmb", "faiz"), "central bank interest rate"),
    (("banka", "kredi"), "banking finance"),
    (("enflasyon",), "inflation prices"),
    (("ihracat", "ithalat", "cari açık", "cari acik"), "international trade shipping"),
]

_DEFAULT_SEARCH_TERM = "finance business"

#: Basliktaki sirket adi -> gercek BIST sembolu (bkz. `assets` tablosu).
#: "hisse" kategorisi tek bir endeks varligina karsilik gelmedigi icin (assets
#: tablosunda BIST100/XU100 gibi tek bir endeks satiri YOK), yalnizca ismi
#: basliktan taniyabildigimiz sirketler icin canli rozet gosterilir - genel
#: bir "hisse" varsayilani UYDURULMAZ.
_COMPANY_SYMBOL_RULES: list[tuple[tuple[str, ...], str]] = [
    (("aselsan",), "ASELS"),
    (("erdemir",), "EREGL"),
    (("garanti",), "GARAN"),
    (("sasa",), "SASA"),
    (("turkcell",), "TCELL"),
    (("thy", "türk hava yolları", "turk hava yollari", "thyao"), "THYAO"),
]

#: `kategori` -> canli fiyati okunacak temsili varlik. Yalnizca `assets`
#: tablosunda GERCEKTEN karsiligi olan kategoriler icin tanimli (altin,
#: doviz); "hisse/ekonomi/piyasa" icin tek bir dogru varlik yok, bu yuzden
#: burada YOK - o kategoriler sadece basliktaki sirket/varlik adiyla eslesir.
_KATEGORI_SYMBOL: dict[str, str] = {
    "altin": "GRAM_ALTIN",
    "doviz": "USD/TRY",
}


def _related_symbol(kategori: str | None, baslik: str | None) -> str | None:
    """Haberin canli fiyat rozeti icin hangi varliga bakilacagini cozer.

    Sira: 1) basliktaki bilinen sirket adi (en spesifik - orn. "Garanti"
    gecen bir haber "hisse" kategorisinde olsa da genel bir endeks degil,
    doğrudan GARAN'in kendi degisimini yansitmali), 2) basliktaki doviz/kripto
    ipucu, 3) kategori bazli temsili varlik. Guvenilir bir eslesme yoksa None
    doner - rozet UYDURULMAZ, gosterilmez.
    """
    text = (baslik or "").lower()

    for keywords, symbol in _COMPANY_SYMBOL_RULES:
        if any(keyword in text for keyword in keywords):
            return symbol

    if any(keyword in text for keyword in ("bitcoin", "kripto")) or "btc" in text:
        return "BTC"
    if "ethereum" in text or "eth" in text.split():
        return "ETH"

    if kategori == "doviz":
        if any(keyword in text for keyword in ("euro", "avro")):
            return "EUR/TRY"
        return _KATEGORI_SYMBOL["doviz"]

    if kategori == "altin":
        return _KATEGORI_SYMBOL["altin"]

    return None


def _title_search_term(baslik: str | None) -> str | None:
    text = (baslik or "").lower()
    for keywords, term in _TITLE_SEARCH_TERM_RULES:
        if any(keyword in text for keyword in keywords):
            return term
    return None


def _search_term(document_id: int, kategori: str | None, baslik: str | None) -> str:
    specific = _title_search_term(baslik)
    if specific:
        return specific

    variants = _KATEGORI_SEARCH_TERMS.get(kategori or "")
    if variants:
        return variants[document_id % len(variants)]

    return _DEFAULT_SEARCH_TERM


def _local_keyword_image(baslik: str | None) -> str | None:
    text = (baslik or "").lower()
    for keywords, image in _KEYWORD_IMAGE_RULES:
        if any(keyword in text for keyword in keywords):
            return image
    return None


async def resolve_image(document_id: int, kategori: str | None, baslik: str | None) -> str:
    """Haberin gorseli yoksa Pexels'ten konuyla alakali bir fotograf cozer.

    Sira:
      1. Basliktaki ozel/marka anahtar kelime (yerel, ucretsiz) - THY, kripto,
         SASA gibi zaten dogru temaya sahip birkac ozel durum.
      2. Pexels arama - basliktan/kategoriden turetilen Ingilizce terimle.
         Basarili olursa sonuc `rag.documents.image_url`'e YAZILIR (cache):
         bir sonraki istekte bu satir icin Pexels'e BIR DAHA gidilmez.
      3. Pexels basarisiz olursa (anahtar tanimsiz, hata, sonuc yok, kota
         doldu) kategori bazli sabit gorsel. Bu deger DB'ye YAZILMAZ -
         gecici bir hata (orn. kota) kalici olarak onbelleklenmesin, bir
         sonraki istekte Pexels tekrar denensin.
    """
    local_image = _local_keyword_image(baslik)
    if local_image:
        return local_image

    query = _search_term(document_id, kategori, baslik)
    photo_url = await search_photo(query, document_id)
    if photo_url:
        await get_rag_repository().set_news_image(document_id, photo_url)
        return photo_url

    return _CATEGORY_FALLBACK_IMAGE.get(kategori or "", _DEFAULT_IMAGE)


async def haberler_getir(limit: int = 20, kategori: str | None = None) -> NewsListResponse:
    rows = await get_rag_repository().list_news(limit=limit, kategori=kategori)

    #: Canli fiyatlar TEK seferde cekilir (haber basina degil) - N+1 sorgu
    #: acmadan tum satirlar icin ayni sembol->degisim sozlugu kullanilir.
    assets = await get_market_repository().list_assets()
    change_by_symbol = {a["symbol"]: a.get("daily_change_pct") for a in assets}

    items = await asyncio.gather(*(_haber(row, change_by_symbol) for row in rows))
    return NewsListResponse(items=list(items))


async def _haber(row: dict, change_by_symbol: dict[str, float | None]) -> NewsArticle:
    raw_text = row.get("raw_text") or ""
    stored_baslik = (row.get("baslik") or "").strip()
    baslik = stored_baslik or _fallback_title(raw_text, row.get("kategori"))
    kategori = row.get("kategori")
    document_id = row["id"]
    paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()] or (
        [raw_text] if raw_text else []
    )

    image_url = row.get("image_url") or await resolve_image(document_id, kategori, stored_baslik)

    related_symbol = _related_symbol(kategori, stored_baslik)
    related_change_pct = change_by_symbol.get(related_symbol) if related_symbol else None

    return NewsArticle(
        id=str(document_id),
        baslik=baslik,
        sirket=row.get("sirket"),
        symbol=row.get("symbol"),
        tarih=row.get("tarih"),
        tip=row.get("tip"),
        kategori=kategori,
        kaynak_url=row.get("kaynak_url"),
        excerpt=raw_text[:EXCERPT_LENGTH],
        related_change_pct=(
            None if related_change_pct is None else round(float(related_change_pct), 4)
        ),
        body=paragraphs,
        image_url=image_url,
    )
