"""Tek seferlik geriye-doldurma: chunk'i olmayan `rag.documents` satirlarini bolup,
embedding'leyip kaydeder.

    python -m app.ingestion.backfill

Once `backend/.env` icinde DATABASE_URL ve EMBEDDING_API_KEY tanimli olmali.

Ileride bu ayni `run_backfill` fonksiyonu, scraper her yeni haber ekledikten
sonra bir scheduler/webhook'tan da cagrilabilir (bkz. `app/market/scheduler.py`
deki periyodik gorev deseni) - bugunku tek seferlik calistirma ile gelecekteki
pipeline arasinda kod tekrari olmasin diye chunking/embedding mantigi ayri
modullerde (`chunking.py`, `embeddings.py`) tutuluyor.

Akis: tum adaylari bul -> her biri icin (bellekte) bol -> dokumanlari, toplam
chunk sayisi 96'yi (Cohere'in cagri basina siniri) asmayacak sekilde
gruplara ayir - bir dokumanin chunk'lari ASLA iki grup arasinda bolunmez.
Her grup: embed -> insert -> commit, sirayla. Boylece bir grup basarisiz
olursa (429, ag hatasi, ...) onceki gruplar zaten kalicidir - script
yeniden calistirildiginda `_FIND_UNCHUNKED_SQL` onlari otomatik disarida
birakir, kaldigi yerden devam eder. Semantik/recursive ara sonuclar hicbir
zaman ayri ayri yazilmaz (bkz. `chunking.py`); tek riskli olan, bir grubun
TAMAMININ (birden fazla dokuman) tek commit'te birlikte yazilmasidir - bu
da bilerek boyle: bir dokumanin chunk'lari hep tek parca kalir.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from app.config import settings
from app.db.session import get_session_factory
from app.ingestion.chunking import DEFAULT_MAX_CHUNK_CHARS, chunk_document
from app.ingestion.embeddings import get_embedder

logger = logging.getLogger(__name__)

#: Cohere'in cagri basina metin siniriyla ayni (bkz. `embeddings.py`) - her
#: grup boylece tam olarak bir Cohere cagrisina/commit'e karsilik gelir.
_MAX_TEXTS_PER_BATCH = 96


def _group_documents_by_chunk_budget(
    doc_chunks: list[tuple[int, list[str]]], max_texts: int
) -> list[list[tuple[int, list[str]]]]:
    """(document_id, chunk_metinleri) ciftlerini gruplar - bir dokuman ASLA
    iki grup arasinda bolunmez (tek dev dokuman `max_texts`i tek basina
    asarsa kendi grubunda kalir; `embeddings.py` bunu kendi ici 96'lik
    dongusuyle zaten guvenle isler)."""
    batches: list[list[tuple[int, list[str]]]] = []
    current: list[tuple[int, list[str]]] = []
    current_count = 0
    for document_id, texts in doc_chunks:
        if current and current_count + len(texts) > max_texts:
            batches.append(current)
            current, current_count = [], 0
        current.append((document_id, texts))
        current_count += len(texts)
    if current:
        batches.append(current)
    return batches


_FIND_UNCHUNKED_SQL = text(
    """
    SELECT d.id, d.raw_text
    FROM rag.documents d
    LEFT JOIN rag.chunks c ON c.document_id = d.id
    WHERE c.id IS NULL
      AND d.raw_text IS NOT NULL
      AND btrim(d.raw_text) <> ''
    ORDER BY d.id
    """
)

#: `document_ids` verildiginde tarama TUM `rag.documents` yerine yalnizca bu
#: id'lerle sinirlanir - testler (`@pytest.mark.db`) kendi gecici
#: dokumanlarinin disina asla tasmasin diye (bkz. `tests/test_backfill.py`).
#: Ayri sorgu olarak tutuluyor: `document_ids=None` icin `= ANY(:document_ids)`
#: NULL parametreyle calismaz (Postgres'te NULL ile ANY karsilastirmasi hep
#: NULL/false doner, tum satirlar elenirdi) - iki sorguyu birlestirip
#: `:document_ids IS NULL OR ...` yazmak yerine, hicbir sartla calisan
#: orijinal sorgu degistirilmeden birebir korunuyor.
_FIND_UNCHUNKED_SQL_SCOPED = text(
    """
    SELECT d.id, d.raw_text
    FROM rag.documents d
    LEFT JOIN rag.chunks c ON c.document_id = d.id
    WHERE c.id IS NULL
      AND d.raw_text IS NOT NULL
      AND btrim(d.raw_text) <> ''
      AND d.id = ANY(:document_ids)
    ORDER BY d.id
    """
)

_START_RUN_SQL = text(
    """
    INSERT INTO rag.ingestion_runs (embedding_model, status)
    VALUES (:embedding_model, 'running')
    RETURNING id
    """
)

_FINISH_RUN_SQL = text(
    """
    UPDATE rag.ingestion_runs
    SET finished_at = now(), status = :status, chunk_count = :chunk_count
    WHERE id = :run_id
    """
)

_INSERT_CHUNK_SQL = text(
    """
    INSERT INTO rag.chunks (document_id, chunk_index, content, embedding)
    VALUES (:document_id, :chunk_index, :content, :embedding)
    ON CONFLICT (document_id, chunk_index) DO NOTHING
    """
)


async def run_backfill(
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    limit: int | None = None,
    document_ids: list[int] | None = None,
) -> int:
    """Chunk'siz tum dokumanlari boler, embedding'ler ve kaydeder.

    `limit` verilirse yalnizca ilk N aday dokuman islenir - tam calistirmadan
    once kucuk olcekte dogrulamak icin (bkz. Cohere trial kota/rate limit).

    `document_ids` verilirse tarama yalnizca bu id'lerle sinirlanir - normal
    calistirmada KULLANILMAZ (varsayilan `None`, tum `rag.documents` taranir);
    yalnizca testlerin gercek DB'deki alakasiz/prod dokumanlara asla
    dokunmamasi icin var (bkz. `_FIND_UNCHUNKED_SQL_SCOPED`).

    Toplam yazilan chunk sayisini dondurur.
    """
    embedder = get_embedder()
    if embedder is None:
        logger.warning(
            "EMBEDDING_API_KEY tanimli degil - chunk'lar embedding'siz (NULL) kaydedilecek"
        )

    session_factory = get_session_factory()
    async with session_factory() as session:
        run_id = (
            await session.execute(_START_RUN_SQL, {"embedding_model": settings.embedding_model})
        ).scalar_one()
        # run kaydi hemen kalici olsun - sonraki batch'ler cakilirsa bile gorunur kalir
        await session.commit()

        total_chunks = 0
        try:
            if document_ids is not None:
                rows = (
                    (
                        await session.execute(
                            _FIND_UNCHUNKED_SQL_SCOPED, {"document_ids": document_ids}
                        )
                    )
                    .mappings()
                    .all()
                )
            else:
                rows = (await session.execute(_FIND_UNCHUNKED_SQL)).mappings().all()
            if limit is not None:
                rows = rows[:limit]
            logger.info("chunk'siz dokuman bulundu", extra={"count": len(rows), "limit": limit})

            doc_chunks = [
                (row["id"], chunk_document(row["raw_text"], max_chunk_chars)) for row in rows
            ]
            doc_chunks = [(doc_id, texts) for doc_id, texts in doc_chunks if texts]
            batches = _group_documents_by_chunk_budget(doc_chunks, _MAX_TEXTS_PER_BATCH)

            for batch_num, batch in enumerate(batches, start=1):
                flat = [
                    (document_id, index, content)
                    for document_id, texts in batch
                    for index, content in enumerate(texts)
                ]
                if embedder is not None:
                    vectors = await embedder.embed_documents([content for _, _, content in flat])
                else:
                    vectors = [None] * len(flat)

                grup_eklenen = 0
                for (document_id, chunk_index, content), embedding in zip(
                    flat, vectors, strict=True
                ):
                    sonuc = await session.execute(
                        _INSERT_CHUNK_SQL,
                        {
                            "document_id": document_id,
                            "chunk_index": chunk_index,
                            "content": content,
                            "embedding": embedding,
                        },
                    )
                    # `ON CONFLICT ... DO NOTHING` (bkz. `_INSERT_CHUNK_SQL`) satiri
                    # atlarsa rowcount 0 olur - `len(flat)` bunu kacirir, gercekte
                    # kaydedilenden FAZLA sayardi.
                    grup_eklenen += sonuc.rowcount
                await session.commit()  # bu grup kalici - sonraki grup basarisiz olsa da kaybolmaz

                total_chunks += grup_eklenen
                logger.info(
                    "grup islendi",
                    extra={
                        "batch": f"{batch_num}/{len(batches)}",
                        "documents_in_batch": len(batch),
                        "chunks_so_far": total_chunks,
                    },
                )
        except Exception:
            # `run_id` satiri START'ta commit edilmisti - burada yakalamazsak
            # 'running' durumunda SONSUZA KADAR kalir (hicbir sey onu
            # 'failed'e cevirmez). Onceki gruplar zaten commit edildi, o
            # yuzden rollback yalnizca son (commit'lenmemis) grubu geri alir.
            await session.rollback()
            await session.execute(
                _FINISH_RUN_SQL,
                {"run_id": run_id, "status": "failed", "chunk_count": total_chunks},
            )
            await session.commit()
            logger.exception(
                "backfill basarisiz - run 'failed' olarak isaretlendi",
                extra={"run_id": run_id, "chunks_before_failure": total_chunks},
            )
            raise

        await session.execute(
            _FINISH_RUN_SQL,
            {"run_id": run_id, "status": "completed", "chunk_count": total_chunks},
        )
        await session.commit()

    logger.info("backfill tamamlandi", extra={"documents": len(rows), "chunks": total_chunks})
    return total_chunks


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Yalnizca ilk N aday dokumani isle (kucuk olcekte test icin)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if not settings.database_enabled:
        raise SystemExit(
            "DATABASE_URL tanimli degil - backend/.env icinde ayarlayip tekrar deneyin."
        )
    written = asyncio.run(run_backfill(limit=args.limit))
    print(f"{written} chunk yazildi.")
