"""Chunk/sorgu embedding'i - Cohere embed-v4.

Postgres/pgvector embedding URETMEZ - yalnizca verilen vektoru saklar ve
indeksler (HNSW). `content_tsv`'nin aksine `embedding` GENERATED bir kolon
degildir; vektoru hesaplamak uygulamanin isidir.

Cohere'in `input_type` parametresi ASIMETRIKTIR: ingestion sirasinda
"search_document", sorgu sirasinda "search_query" kullanilmalidir - ikisi
FARKLI vektor uretir. Yanlis tarafta yanlis degeri kullanmak arama
kalitesini olculebilir sekilde dusurur; bu yuzden `embed_documents` ve
`embed_query` bilerek iki ayri fonksiyon, tek bir "embed" degil.

Baglanti async'tir (`cohere.AsyncClientV2`): app'in geri kalani async
(FastAPI, SQLAlchemy async engine - bkz. `app/db/session.py`), senkron bir
HTTP cagrisi olay dongusunu bloklardi.

`app/core/llm.py`'deki desenle ayni: `EMBEDDING_API_KEY` tanimlanana kadar
`get_embedder()` `None` doner ve arama BM25/`content_tsv` uzerinden
calismaya devam eder.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)

#: Cohere embed API siniri: cagri basina en fazla 96 metin.
_MAX_TEXTS_PER_CALL = 96

#: Trial anahtarlarda "100000 token/dakika" siniri var - 429 alinca bir
#: dakikaya yakin beklemek limitin sifirlanmasi icin yeterli.
_RATE_LIMIT_BACKOFF_SECONDS = 65
_MAX_RATE_LIMIT_RETRIES = 5


class Embedder(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


class CohereEmbedder:
    """`cohere.AsyncClientV2` uzerinden ince bir sarmalayici.

    `model`/`output_dimension` konfigurasyondan gelir; saglayici degisirse
    yalnizca bu sinif degisir (bkz. `app/core/llm.py`'deki ayni gerekce).
    """

    def __init__(self, api_key: str, model: str, output_dimension: int) -> None:
        import cohere  # gecikmeli import: paket sadece gercekten kullanildiginda gerekli

        self._client = cohere.AsyncClientV2(api_key=api_key)
        self._model = model
        self._output_dimension = output_dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, input_type="search_document")

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text], input_type="search_query")
        return vectors[0]

    async def _embed(self, texts: list[str], *, input_type: str) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), _MAX_TEXTS_PER_CALL):
            batch = texts[start : start + _MAX_TEXTS_PER_CALL]
            vectors.extend(await self._embed_batch_with_retry(batch, input_type=input_type))
        return vectors

    async def _embed_batch_with_retry(
        self, batch: list[str], *, input_type: str
    ) -> list[list[float]]:
        """Tek Cohere cagrisi - trial anahtarin 429'unda bekleyip tekrar dener.

        Retry burada, `backfill.py`'de degil: boylece ileride sorgu zamaninda
        `embed_query` cagiran her yer (bkz. Faz 4 - `SqlRagRepository`) ayni
        korumadan otomatik yararlanir, saglayiciya ozel hata tipini bilmeden.
        """
        import cohere

        for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1):
            try:
                response = await self._client.embed(
                    model=self._model,
                    input_type=input_type,
                    texts=batch,
                    output_dimension=self._output_dimension,
                    embedding_types=["float"],
                    truncate="END",
                )
                return response.embeddings.float_
            except cohere.errors.too_many_requests_error.TooManyRequestsError:
                if attempt == _MAX_RATE_LIMIT_RETRIES:
                    raise
                logger.warning(
                    "Cohere rate limit - %ss bekleniyor",
                    _RATE_LIMIT_BACKOFF_SECONDS,
                    extra={"attempt": attempt, "max_retries": _MAX_RATE_LIMIT_RETRIES},
                )
                await asyncio.sleep(_RATE_LIMIT_BACKOFF_SECONDS)

        raise AssertionError("unreachable")  # pragma: no cover


def get_embedder() -> Embedder | None:
    """Ajana ozel LLM istemcisi uretimindeki desenin ayni: anahtar tanimli
    degilse `None` doner - bu bir hata DEGILDIR, "embedding'siz calis"
    demektir (bkz. `app/core/llm.py::get_llm_client`).
    """
    if not settings.embedding_api_key:
        logger.info("embedding baglanmadi, embedding_api_key tanimli degil")
        return None

    return CohereEmbedder(
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        output_dimension=settings.embedding_dim,
    )
