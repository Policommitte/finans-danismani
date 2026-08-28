"""Paylasilan Pexels arama istemcisi.

Once `news.py` icinde ozel olarak yasiyordu; artik hem bulten (RSS haberleri)
hem de baska yerlerin (portfoy varliklarinin kapak gorseli, Yatirim Oyunu
magaza kartlari) AYNI arama/onbellek mantigini kullanmasi icin buraya
tasindi - iki ayri Pexels entegrasyonu birbirinden bagimsiz ve tutarsiz
davranmasin diye.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.pexels.com/v1/search"
_TIMEOUT_SECONDS = 6.0

#: Bir sayfa yuklemesinde tek seferde ucretsiz Pexels kotasini tuketmemek
#: icin ayni anda en fazla bu kadar istek yollanir.
_semaphore = asyncio.Semaphore(5)

#: Ayni arama terimini paylasan kayitlar (orn. hepsi "altin" kategorisi)
#: Pexels'ten TEK sonuc istenirse hepsi ayni fotografi alir - tam da
#: istenmeyen "paylasilan gorsel" sonucu. Bunun yerine bu kadar aday istenip
#: bir seed'e gore FARKLI (ama o kayit icin hep AYNI) bir aday secilir.
#: Pexels kotasini ETKILEMEZ: hala tek istek, sadece per_page buyur.
CANDIDATE_COUNT = 80

#: Suresiz cache: process yasadigi surece AYNI sorgu icin bir daha Pexels'e
#: gidilmez. Kalici (DB) degil - haber gorselleri icin ayri, DB'ye yazan bir
#: onbellek zaten var (bkz. news.py resolve_image); bu sadece "generic
#: sorgu -> URL" eslemesi icin process-ici, basit bir onbellek.
_query_cache: dict[str, str] = {}


async def search_photo(query: str, seed: int = 0) -> str | None:
    """Pexels'te arama yapar; basarili olursa `seed`e gore sabit bir aday secer.

    API anahtari tanimsizsa veya istek basarisiz olursa None doner - cagiran
    taraf bunu "gorsel bulunamadi" olarak yorumlayip kendi geri dususune
    (yerel ikon/gradyan) duser. Hata ASLA firlatilmaz.
    """
    if not settings.pexels_api_key:
        return None

    async with _semaphore:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    _SEARCH_URL,
                    params={
                        "query": query,
                        "per_page": CANDIDATE_COUNT,
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


async def cached_photo(query: str) -> str | None:
    """`search_photo`nun basit, sorgu-anahtarli onbellekli hali.

    Genel amacli fotograf istekleri (portfoy varligi kapak gorseli, oyun
    magaza karti gibi) icin: ayni sorgu ayni surecte bir daha Pexels'e
    gitmez. Basarisiz sonuc ONBELLEKLENMEZ (gecici bir ag hatasi olabilir,
    bir sonraki istekte tekrar denenir).
    """
    normalized = query.strip().lower()
    if not normalized:
        return None

    cached = _query_cache.get(normalized)
    if cached is not None:
        return cached

    url = await search_photo(normalized, seed=0)
    if url:
        _query_cache[normalized] = url
    return url
