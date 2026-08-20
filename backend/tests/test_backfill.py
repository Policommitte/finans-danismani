"""`app/ingestion/backfill.py` testleri.

`_group_documents_by_chunk_budget` saf bir fonksiyondur, agsiz/DB'siz test
edilir. `run_backfill` gercek bir PostgreSQL ister (`@pytest.mark.db`); her
test kendi gecici dokumanlarini ekler ve sonunda siler (`rag.chunks` ilgili
satirlari `ON DELETE CASCADE` ile otomatik temizlenir).

`get_embedder()` her DB testinde SAHTE bir embedder ile monkeypatch'lenir -
hicbir test gercek Cohere API'sine cikmaz.

Kritik davranislar:
  * Bir dokumanin chunk'lari ASLA iki grup arasinda bolunmez.
  * Gruplar TEK TEK commit edilir: bir grup basarisiz olursa ONCEKI gruplar
    zaten kalicidir (tek buyuk transaction DEGIL).
  * Ikinci calistirma zaten chunk'lanmis dokumanlari tekrar islemez (idempotent).
  * `raw_text` NULL/bos olan dokumanlar aday listesine hic girmez.
  * Embedder yoksa (`EMBEDDING_API_KEY` tanimsiz) chunk'lar yine de NULL
    embedding ile kaydedilir - islem durmaz.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db.session import get_session_factory
from app.ingestion import backfill
from app.ingestion.backfill import _group_documents_by_chunk_budget

# ---------------------------------------------------------------------------
# _group_documents_by_chunk_budget - saf mantik, DB gerektirmez
# ---------------------------------------------------------------------------


def test_bos_liste_bos_grup_listesi_doner():
    assert _group_documents_by_chunk_budget([], max_texts=96) == []


def test_tek_dokuman_tek_grupta():
    assert _group_documents_by_chunk_budget([(1, ["a", "b"])], max_texts=96) == [[(1, ["a", "b"])]]


def test_bir_dokuman_iki_grup_arasinda_asla_bolunmez():
    """Tek basina siniri asan bir dokuman (200 > 96) kendi grubunda kalir -
    `embeddings.py` bunu kendi ici 96'lik dongusuyle guvenle isler."""
    dev_dokuman = (3, ["parca"] * 200)

    gruplar = _group_documents_by_chunk_budget([dev_dokuman], max_texts=96)

    assert gruplar == [[dev_dokuman]]


def test_toplam_sinir_asilinca_yeni_grup_acilir():
    doc_a = (1, ["x"] * 60)
    doc_b = (2, ["y"] * 60)  # 60 + 60 = 120 > 96, ayni grupta OLAMAZ

    gruplar = _group_documents_by_chunk_budget([doc_a, doc_b], max_texts=96)

    assert gruplar == [[doc_a], [doc_b]]


def test_siniri_asmayan_dokumanlar_ayni_grupta_birlesir():
    doc_a = (1, ["x"] * 10)
    doc_b = (2, ["y"] * 10)  # 10 + 10 = 20 <= 96, AYNI grupta olmali

    gruplar = _group_documents_by_chunk_budget([doc_a, doc_b], max_texts=96)

    assert gruplar == [[doc_a, doc_b]]


def test_her_dokuman_tam_olarak_bir_kez_gorunur():
    dokumanlar = [(i, ["parca"] * (i % 5 + 1)) for i in range(1, 21)]

    gruplar = _group_documents_by_chunk_budget(dokumanlar, max_texts=10)

    gorulen_idler = sorted(doc_id for grup in gruplar for doc_id, _ in grup)
    assert gorulen_idler == list(range(1, 21))


def test_tam_sinirdaki_toplam_yeni_grup_acmaz():
    """Toplam TAM `max_texts`e esitse (asmiyorsa) ayni grupta kalir."""
    doc_a = (1, ["x"] * 48)
    doc_b = (2, ["y"] * 48)  # 48 + 48 = 96, siniri ASMAZ

    gruplar = _group_documents_by_chunk_budget([doc_a, doc_b], max_texts=96)

    assert gruplar == [[doc_a, doc_b]]


# ---------------------------------------------------------------------------
# run_backfill - gercek DB, sahte embedder
# ---------------------------------------------------------------------------


class _SahteEmbedder:
    """Cagrilan metinleri kaydeden, gercek API'ye cikmayan sahte embedder.

    `patlat_kacinci_cagride` verilirse o sirali cagrida `RuntimeError` firlatir -
    grup-basina-commit'in dayanikliligini test etmek icin.
    """

    def __init__(self, *, patlat_kacinci_cagride: int | None = None):
        self.cagrilar: list[list[str]] = []
        self._patlat_kacinci_cagride = patlat_kacinci_cagride

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.cagrilar.append(list(texts))
        if (
            self._patlat_kacinci_cagride is not None
            and len(self.cagrilar) == self._patlat_kacinci_cagride
        ):
            raise RuntimeError("sahte embedder hatasi")
        return [[0.1] * 1024 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.1] * 1024


@pytest.fixture(autouse=True)
async def _ingestion_runs_temizle(request):
    """Her `db`-isaretli testten SONRA o test sirasinda `run_backfill`in
    yazdigi `rag.ingestion_runs` satirlarini siler.

    `run_backfill` her cagrildiginda kalici bir satir ekler ve kendisi hicbir
    zaman silmez (uretimde bu BILEREK boyle - gecmis calistirma kaydi kalici
    kalmali). Testler bunu birakirsa DB'de sonsuza kadar yigilir; o yuzden
    temizlik sorumlulugu burada, `gecici_dokuman`'da degil (o fixture'i
    kullanmayan testler de var, orn. `test_bos_raw_text_islenmez`).
    """
    if "db" not in request.keywords:
        yield
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        baslangic_id = (
            await session.execute(text("SELECT COALESCE(max(id), 0) FROM rag.ingestion_runs"))
        ).scalar_one()

    yield

    async with session_factory() as session:
        await session.execute(
            text("DELETE FROM rag.ingestion_runs WHERE id > :baslangic_id"),
            {"baslangic_id": baslangic_id},
        )
        await session.commit()


@pytest.fixture
async def gecici_dokuman():
    """Chunk'siz test dokumanlari ekleyen bir fabrika fixture'i doner, testten
    sonra ekledigi her seyi siler.

    Kullanim: `idler = await gecici_dokuman(["metin bir", "metin iki"])`
    """
    olusturulan_idler: list[int] = []
    session_factory = get_session_factory()

    async def _olustur(raw_texts: list[str]) -> list[int]:
        async with session_factory() as session:
            idler = []
            for raw_text in raw_texts:
                sonuc = await session.execute(
                    text(
                        """
                        INSERT INTO rag.documents (external_id, baslik, tip, raw_text)
                        VALUES (:external_id, 'Test dokumani', 'haber', :raw_text)
                        RETURNING id
                        """
                    ),
                    {"external_id": f"TEST-{uuid.uuid4()}", "raw_text": raw_text},
                )
                idler.append(sonuc.scalar_one())
            await session.commit()
        olusturulan_idler.extend(idler)
        return idler

    yield _olustur

    async with session_factory() as session:
        if olusturulan_idler:
            await session.execute(
                text("DELETE FROM rag.documents WHERE id = ANY(:ids)"),
                {"ids": olusturulan_idler},
            )
            await session.commit()


@pytest.mark.db
async def test_chunksiz_dokuman_islenir_ve_embedding_alir(gecici_dokuman, monkeypatch):
    idler = await gecici_dokuman(["Kisa bir haber metni burada duruyor."])
    sahte = _SahteEmbedder()
    monkeypatch.setattr(backfill, "get_embedder", lambda: sahte)

    yazilan = await backfill.run_backfill(document_ids=idler)

    assert yazilan >= 1
    assert sahte.cagrilar  # en az bir embed cagrisi yapildi

    session_factory = get_session_factory()
    async with session_factory() as session:
        sonuc = await session.execute(
            text("SELECT count(*), count(embedding) FROM rag.chunks WHERE document_id = ANY(:ids)"),
            {"ids": idler},
        )
        toplam, embedli = sonuc.one()
        assert toplam > 0
        assert embedli == toplam  # HEPSI embedding almis


@pytest.mark.db
async def test_bos_raw_text_islenmez(monkeypatch):
    """`raw_text` NULL/bos olan dokumanlar aday listesine hic girmez."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        sonuc = await session.execute(
            text(
                """
                INSERT INTO rag.documents (external_id, baslik, tip, raw_text)
                VALUES (:external_id, 'Bos dokuman', 'haber', '')
                RETURNING id
                """
            ),
            {"external_id": f"TEST-{uuid.uuid4()}"},
        )
        doc_id = sonuc.scalar_one()
        await session.commit()

    try:
        sahte = _SahteEmbedder()
        monkeypatch.setattr(backfill, "get_embedder", lambda: sahte)

        await backfill.run_backfill(document_ids=[doc_id])

        async with session_factory() as session:
            sonuc = await session.execute(
                text("SELECT count(*) FROM rag.chunks WHERE document_id = :id"),
                {"id": doc_id},
            )
            assert sonuc.scalar_one() == 0
    finally:
        async with session_factory() as session:
            await session.execute(text("DELETE FROM rag.documents WHERE id = :id"), {"id": doc_id})
            await session.commit()


@pytest.mark.db
async def test_embedder_yoksa_null_embedding_ile_kaydedilir(gecici_dokuman, monkeypatch):
    """`EMBEDDING_API_KEY` tanimli degilse (`get_embedder` `None` doner) chunk'lar
    yine de kaydedilir - yalnizca embedding NULL kalir, islem durmaz."""
    idler = await gecici_dokuman(["Baska bir haber metni burada duruyor."])
    monkeypatch.setattr(backfill, "get_embedder", lambda: None)

    yazilan = await backfill.run_backfill(document_ids=idler)

    assert yazilan >= 1

    session_factory = get_session_factory()
    async with session_factory() as session:
        sonuc = await session.execute(
            text("SELECT count(embedding) FROM rag.chunks WHERE document_id = ANY(:ids)"),
            {"ids": idler},
        )
        assert sonuc.scalar_one() == 0  # hic embedding yok


@pytest.mark.db
async def test_limit_parametresi_islem_sayisini_sinirlar(gecici_dokuman, monkeypatch):
    idler = await gecici_dokuman(
        ["Birinci haber metni burada duruyor.", "Ikinci haber metni burada duruyor."]
    )
    sahte = _SahteEmbedder()
    monkeypatch.setattr(backfill, "get_embedder", lambda: sahte)

    await backfill.run_backfill(document_ids=idler, limit=1)

    session_factory = get_session_factory()
    async with session_factory() as session:
        sonuc = await session.execute(
            text("SELECT DISTINCT document_id FROM rag.chunks WHERE document_id = ANY(:ids)"),
            {"ids": idler},
        )
        islenen_dokumanlar = {row[0] for row in sonuc.all()}
        assert len(islenen_dokumanlar) == 1  # yalnizca BIR dokuman islendi


@pytest.mark.db
async def test_ikinci_calistirma_ayni_dokumani_tekrar_islemez(gecici_dokuman, monkeypatch):
    """Idempotency: bir kez chunk'lanan dokuman, script tekrar calistirilinca
    yeniden islenmez - `_FIND_UNCHUNKED_SQL` onu otomatik disarida birakir."""
    idler = await gecici_dokuman(["Idempotency testi icin haber metni."])
    sahte = _SahteEmbedder()
    monkeypatch.setattr(backfill, "get_embedder", lambda: sahte)

    ilk_yazilan = await backfill.run_backfill(document_ids=idler)
    assert ilk_yazilan > 0

    ikinci_yazilan = await backfill.run_backfill(document_ids=idler)

    assert ikinci_yazilan == 0


@pytest.mark.db
async def test_ingestion_run_kaydi_dogru_olusturulur(gecici_dokuman, monkeypatch):
    idler = await gecici_dokuman(["Run kaydi testi icin haber metni."])
    sahte = _SahteEmbedder()
    monkeypatch.setattr(backfill, "get_embedder", lambda: sahte)

    yazilan = await backfill.run_backfill(document_ids=idler)

    session_factory = get_session_factory()
    async with session_factory() as session:
        sonuc = await session.execute(
            text("SELECT status, chunk_count FROM rag.ingestion_runs ORDER BY id DESC LIMIT 1")
        )
        durum, chunk_sayisi = sonuc.one()
        assert durum == "completed"
        assert chunk_sayisi == yazilan


@pytest.mark.db
async def test_bir_grup_basarisiz_olursa_onceki_grup_kalici_kalir(gecici_dokuman, monkeypatch):
    """KRITIK DAYANIKLILIK OZELLIGI: gruplar TEK TEK commit edilir. Ikinci
    grubun embed cagrisi patlarsa BIRINCI grubun chunk'lari zaten yazilmis ve
    kalici olmali (tek buyuk transaction DEGIL, backfill.py'nin ana tasarim
    kararidir).

    `_MAX_TEXTS_PER_BATCH` 1'e dusurulur ki iki kisa dokuman KESIN olarak iki
    AYRI gruba dussun - gercek chunk sayisi tahminine bagli kalinmaz.
    """
    monkeypatch.setattr(backfill, "_MAX_TEXTS_PER_BATCH", 1)
    idler = await gecici_dokuman(["Birinci kisa haber.", "Ikinci kisa haber."])

    sahte = _SahteEmbedder(patlat_kacinci_cagride=2)
    monkeypatch.setattr(backfill, "get_embedder", lambda: sahte)

    with pytest.raises(RuntimeError):
        await backfill.run_backfill(document_ids=idler)

    assert len(sahte.cagrilar) == 2  # ilk grup basarili, ikincide patladi

    session_factory = get_session_factory()
    async with session_factory() as session:
        sonuc = await session.execute(
            text("SELECT count(*) FROM rag.chunks WHERE document_id = ANY(:ids)"),
            {"ids": idler},
        )
        # birinci dokumanin chunk'i kalici kaldi (1), ikincinin hic yazilmadi
        assert sonuc.scalar_one() == 1
