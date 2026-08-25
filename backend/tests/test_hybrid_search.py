"""`SqlRagRepository.hybrid_search()` entegrasyon testleri.

BU TESTLER GERCEK BIR VERITABANI ISTER (bkz. `test_sql_repositories.py`
docstring'i - ayni `TEST_DATABASE_URL` mekanizmasi, ayni calistirma sekli).

BURADA SINANAN SEY: dense (embedding) ayagin GERCEKTEN devreye girdigi,
embedder yoklugunda/hata/zaman asiminda `search()`'e (BM25) SESSIZCE
dustugu ve `sirket`/`tip`/tarih filtrelerinin `rag.hybrid_search()` SQL
fonksiyonuna dogru gectigi. Gercek bir Cohere API cagrisi YAPILMAZ - sahte
bir `Embedder` enjekte edilir (bkz. `test_embeddings.py` ile ayni desen).
"""

import os

import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="TEST_DATABASE_URL tanimli degil (Postgres gerektiren entegrasyon testi)",
    ),
]


class _SahteEmbedder:
    """Sabit bir vektor donen ya da bilerek bozuk davranan sahte embedder."""

    def __init__(self, vector=None, exception=None, sleep_seconds=None):
        self._vector = vector
        self._exception = exception
        self._sleep_seconds = sleep_seconds

    async def embed_query(self, text: str) -> list[float]:
        import asyncio

        if self._sleep_seconds is not None:
            await asyncio.sleep(self._sleep_seconds)
        if self._exception is not None:
            raise self._exception
        return self._vector

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]


@pytest.fixture
def rag_repo_factory(monkeypatch):
    """`SqlRagRepository`'yi istenen sahte embedder ile kurar.

    `deps.get_rag_repository()` `lru_cache`'li oldugu icin dogrudan
    kullanilamaz (embedder testler arasi degismeli); bunun yerine ayni
    `_session_factory()`'yi paylasan yeni bir `SqlRagRepository` orneklenir -
    `deps.py::get_rag_repository`'nin gercek kod yolunun aynisi (bkz. o
    fonksiyonun `SqlRagRepository(_session_factory(), embedder=...)` cagrisi).
    """
    from app.config import settings
    from app.repositories import deps
    from app.repositories.sql import SqlRagRepository

    monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    deps.reset_repositories()

    def _factory(embedder=None) -> SqlRagRepository:
        return SqlRagRepository(deps._session_factory(), embedder=embedder)

    yield _factory
    deps.reset_repositories()


async def _chunk_embedding(deps, external_id: str) -> list[float]:
    """Bir dokumanin GERCEK embedding'ini DB'den okur (test verisi icin)."""
    from sqlalchemy import text

    async with deps._session_factory()() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT c.embedding
                    FROM rag.chunks c JOIN rag.documents d ON d.id = c.document_id
                    WHERE d.external_id = :external_id
                    LIMIT 1
                    """
                ),
                {"external_id": external_id},
            )
        ).first()
    # pgvector kolonu psycopg'de duz METIN olarak doner ("[0.1,0.2,...]"):
    # pgvector-python adaptoru kayitli degil (bkz. app/db/session.py).
    return [float(x) for x in row[0].strip("[]").split(",")]


async def test_embeddersiz_bm25_e_duser(rag_repo_factory):
    """Embedder enjekte edilmediyse (EMBEDDING_API_KEY yok) dogrudan BM25 calisir."""
    repo = rag_repo_factory(embedder=None)

    sonuclar = await repo.hybrid_search("THYAO net kar", top_k=5)

    assert sonuclar
    assert {"doc_id", "baslik", "sirket", "tarih", "tip", "content", "score"} <= set(sonuclar[0])


async def test_embed_hatasinda_bm25_e_duser(rag_repo_factory):
    """Embedding API'si hata verirse istek COKMEZ, BM25'e duser."""
    repo = rag_repo_factory(embedder=_SahteEmbedder(exception=RuntimeError("cohere 500")))

    sonuclar = await repo.hybrid_search("THYAO net kar", top_k=5)

    assert sonuclar, "embed hatasi aramayi tamamen bosa dusurmemeli"


async def test_embed_zaman_asiminda_bm25_e_duser(rag_repo_factory, monkeypatch):
    """Embedding API'si yavassa kisa timeout devreye girip BM25'e duser."""
    from app.config import settings

    monkeypatch.setattr(settings, "rag_query_embedding_timeout_seconds", 0.05)
    repo = rag_repo_factory(embedder=_SahteEmbedder(vector=[0.0] * 1024, sleep_seconds=1))

    sonuclar = await repo.hybrid_search("THYAO net kar", top_k=5)

    assert sonuclar, "yavas embedding tum istegi bloklamamali"


async def test_dense_ayak_gercekten_calisir(rag_repo_factory):
    """Sozel ORTUSMESI OLMAYAN bir sorgu, embedding'i eslesirse yine de bulunmali.

    DOC-005'in GERCEK embedding'i sahte sorgu vektoru olarak kullanilir; sorgu
    metni ("zzqx wobble flurb") ise DOC-005 icerigiyle hicbir kelimeyi
    paylasmaz. BM25 boyle bir sorguda kesinlikle bos doner (bkz.
    `test_sql_repositories.py::test_rag_aramasi_turkce_kelimeleri_ORlar`
    - OR'a cevrilse bile ORTAK kelime yoksa eslesme yoktur); sonucun yine de
    gelmesi dense ayagin GERCEKTEN devrede oldugunun kaniti.
    """
    from app.repositories import deps

    vektor = await _chunk_embedding(deps, "DOC-005")
    repo = rag_repo_factory(embedder=_SahteEmbedder(vector=vektor))

    bm25_kontrolu = await repo.search("zzqx wobble flurb nonsense", top_k=5)
    assert bm25_kontrolu == [], "test varsayimi bozuldu: BM25 bu sorguda zaten bos donmeliydi"

    sonuclar = await repo.hybrid_search("zzqx wobble flurb nonsense", top_k=3)

    assert sonuclar, "dense ayak calismiyorsa sonuc bos doner"
    assert sonuclar[0]["doc_id"] == "DOC-005"


async def test_sirket_filtresi_hybrid_search_ta_da_calisir(rag_repo_factory):
    """`p_sirket` `d.sirket`e degil sembol/unvana bakmali (BM25 yolundaki aynı kural)."""
    repo = rag_repo_factory(embedder=None)

    sonuclar = await repo.hybrid_search("yolcu doluluk", sirket="THYAO")

    assert sonuclar, "sembol ile filtreleme unvanla yazilmis dokumani bulmali"
    assert all(s["symbol"] == "THYAO" for s in sonuclar)


async def test_tip_filtresi_hybrid_search_ta_da_calisir(rag_repo_factory):
    """`query` DOC-001'in gerçek `content`'inden alınır - "THYAO" yalnızca
    başlıkta/sembolde geçer, `content_tsv` üzerinde BM25 ile eşleşmez."""
    repo = rag_repo_factory(embedder=None)

    sonuclar = await repo.hybrid_search("net kar", tip="bilanco", top_k=10)

    assert sonuclar
    assert all(s["tip"] == "bilanco" for s in sonuclar)


async def test_tarih_araligi_search_ta_calisir(rag_repo_factory):
    """`search()`e eklenen date_from/date_to - hybrid_search'un BM25 dustugu yol
    bu filtreleri KAYBETMEMELI (bkz. SqlRagRepository docstring)."""
    repo = rag_repo_factory(embedder=None)

    # DOC-005 (2026-08-01), DOC-006 (2026-08-05), DOC-008 (2026-08-08) bu
    # araliktadir; DOC-001..004/007 (Temmuz ve oncesi) disaridadir.
    sonuclar = await repo.search("piyasa", top_k=20, date_from="2026-08-01")

    assert sonuclar
    assert all(s["tarih"] >= "2026-08-01" for s in sonuclar)


async def test_tarih_araligi_hybrid_search_a_da_gecer(rag_repo_factory):
    """Ayni tarih filtresi dense yolda da (SQL fonksiyonuna) dogru iletilmeli."""
    from app.repositories import deps

    vektor = await _chunk_embedding(deps, "DOC-001")  # 2026-07-28
    repo = rag_repo_factory(embedder=_SahteEmbedder(vector=vektor))

    # DOC-001'in KENDI embedding'iyle arasak bile date_from onu disarida
    # birakmali - filtre SQL fonksiyonunun ICINDE, RRF'den ONCE uygulanir.
    sonuclar = await repo.hybrid_search("THYAO", top_k=5, date_from="2026-08-01")

    assert all(s["doc_id"] != "DOC-001" for s in sonuclar)
