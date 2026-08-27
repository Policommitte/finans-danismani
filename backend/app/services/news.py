"""Bulten sayfasi domain servisi.

`rag.documents` zaten RAG ingestion'i icin var olan haber tablosu; bu servis
onu ARAMA degil, duz bir liste olarak bultene sunar (bkz. repositories/base.py
-> RagRepository.list_news).
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import settings
from app.repositories.deps import get_market_repository, get_rag_repository
from app.schemas.market import NewsArticle, NewsListResponse

logger = logging.getLogger(__name__)

#: Ozette gonderilen metin uzunlugu (kart arayuzunde tam metin gerekmez).
EXCERPT_LENGTH = 240

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

_PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
_PEXELS_TIMEOUT_SECONDS = 6.0

#: Bir sayfa yuklemesinde tek seferde ucretsiz Pexels kotasini tuketmemek
#: icin ayni anda en fazla bu kadar istek yollanir; onbellege (image_url)
#: dustukten sonra ayni haber icin bir daha hic istek atilmaz.
_pexels_semaphore = asyncio.Semaphore(5)


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


#: Ayni arama terimini paylasan haberler (orn. hepsi "altin" kategorisi)
#: Pexels'ten TEK sonuc istenirse hepsi ayni fotografi alir - tam da
#: istemedigimiz "paylasilan gorsel" sonucu. Bunun yerine bu kadar aday
#: istenip haber ID'sine gore FARKLI (ama o haber icin hep AYNI) bir aday
#: secilir. Pexels kotasini ETKILEMEZ: hala tek istek, sadece per_page buyur.
#: 80 = Pexels'in izin verdigi ust sinir; en kalabalik kategoride (doviz,
#: ~66 haber) bile her habere farkli bir aday dusmesi icin gerekli.
_PEXELS_CANDIDATE_COUNT = 80


async def _pexels_search(query: str, seed: int) -> str | None:
    if not settings.pexels_api_key:
        return None

    async with _pexels_semaphore:
        try:
            async with httpx.AsyncClient(timeout=_PEXELS_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    _PEXELS_SEARCH_URL,
                    params={
                        "query": query,
                        "per_page": _PEXELS_CANDIDATE_COUNT,
                        "orientation": "landscape",
                    },
                    headers={"Authorization": settings.pexels_api_key},
                )
        except httpx.HTTPError as exc:
            logger.warning(
                "pexels istegi hata verdi",
                extra={"hata": f"{type(exc).__name__}: {exc}", "query": query},
            )
            return None

    if response.status_code != 200:
        logger.warning(
            "pexels istegi basarisiz",
            extra={"status": response.status_code, "query": query},
        )
        return None

    photos = response.json().get("photos") or []
    if not photos:
        return None

    photo = photos[seed % len(photos)]
    src = photo.get("src") or {}
    return src.get("landscape") or src.get("medium") or src.get("original")


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
    photo_url = await _pexels_search(query, document_id)
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
    baslik = row.get("baslik") or ""
    kategori = row.get("kategori")
    document_id = row["id"]
    paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()] or ([raw_text] if raw_text else [])

    image_url = row.get("image_url") or await resolve_image(document_id, kategori, baslik)

    related_symbol = _related_symbol(kategori, baslik)
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
        related_change_pct=None if related_change_pct is None else round(float(related_change_pct), 4),
        body=paragraphs,
        image_url=image_url,
    )
