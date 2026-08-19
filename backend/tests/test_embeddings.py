"""Cohere embedding sarmalayicisinin testleri (`app/ingestion/embeddings.py`).

BU TESTLER GERCEK COHERE API'SINE CIKMAZ: `cohere.AsyncClientV2.embed`
sahte (fake) bir coroutine ile degistirilir, `asyncio.sleep` de gercekten
beklemesin diye no-op'a cevrilir (aksi halde retry testleri dakikalarca
surerdi - trial anahtarin backoff'u 65s).

Kritik davranislar:
  * `embed_documents` / `embed_query` FARKLI `input_type` gonderir - yanlis
    tarafta yanlis deger arama kalitesini olculebilir sekilde dusurur (bkz.
    modul docstring'i).
  * Bos girdi API'ye HIC cagri yapmaz.
  * 96'dan fazla metin birden fazla cagriya bolunur, vektorler GIRDI
    SIRASIYLA birlestirilir.
  * 429 (`TooManyRequestsError`) `_MAX_RATE_LIMIT_RETRIES` kez denenip son
    denemede de basarisizsa YENIDEN FIRLATILIR (sessizce yutulmaz).
  * 429 DISINDAKI bir hata HIC denenmeden hemen yukselir.
"""

from __future__ import annotations

import asyncio

import pytest
from cohere.errors import TooManyRequestsError

from app.ingestion.embeddings import CohereEmbedder, get_embedder


def _fake_response(n: int):
    """Cohere'in `EmbedByTypeResponse`'unu taklit eden minimal nesne."""

    class _Embeddings:
        float_ = [[0.1] * 1024 for _ in range(n)]

    class _Response:
        embeddings = _Embeddings()

    return _Response()


@pytest.fixture(autouse=True)
def _sleep_beklemez(monkeypatch):
    """Retry testleri gercekte 65s beklemesin diye `asyncio.sleep` no-op'lanir."""

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


@pytest.fixture
def embedder() -> CohereEmbedder:
    return CohereEmbedder(api_key="sahte-anahtar", model="embed-v4.0", output_dimension=1024)


# ---------------------------------------------------------------------------
# get_embedder
# ---------------------------------------------------------------------------


def test_anahtar_yoksa_none_doner(override_settings):
    override_settings(embedding_api_key="")
    assert get_embedder() is None


def test_anahtar_varsa_cohere_embedder_uretilir(override_settings):
    override_settings(
        embedding_api_key="sahte-anahtar", embedding_model="embed-v4.0", embedding_dim=1024
    )
    assert isinstance(get_embedder(), CohereEmbedder)


# ---------------------------------------------------------------------------
# embed_documents / embed_query - input_type ayrimi
# ---------------------------------------------------------------------------


async def test_bos_liste_api_cagirmaz(embedder):
    cagrildi = False

    async def _fail_if_called(**kwargs):
        nonlocal cagrildi
        cagrildi = True
        return _fake_response(0)

    embedder._client.embed = _fail_if_called

    sonuc = await embedder.embed_documents([])

    assert sonuc == []
    assert cagrildi is False


async def test_embed_documents_search_document_gonderir(embedder):
    gorulen_input_type = None

    async def _fake_embed(**kwargs):
        nonlocal gorulen_input_type
        gorulen_input_type = kwargs["input_type"]
        return _fake_response(len(kwargs["texts"]))

    embedder._client.embed = _fake_embed

    await embedder.embed_documents(["metin bir", "metin iki"])

    assert gorulen_input_type == "search_document"


async def test_embed_query_search_query_gonderir(embedder):
    gorulen_input_type = None

    async def _fake_embed(**kwargs):
        nonlocal gorulen_input_type
        gorulen_input_type = kwargs["input_type"]
        return _fake_response(1)

    embedder._client.embed = _fake_embed

    await embedder.embed_query("sorgu metni")

    assert gorulen_input_type == "search_query"


async def test_embed_query_tek_vektor_doner_liste_icinde_liste_degil(embedder):
    """`embed_query`, `embed_documents`'in aksine TEK bir vektor doner."""

    async def _fake_embed(**kwargs):
        return _fake_response(1)

    embedder._client.embed = _fake_embed

    vektor = await embedder.embed_query("sorgu")

    assert isinstance(vektor, list)
    assert isinstance(vektor[0], float)
    assert len(vektor) == 1024


async def test_vektorler_girdi_sirasiyla_eslesir(embedder):
    """Donen vektor listesi, gonderilen metin listesiyle AYNI sirada olmali."""

    async def _fake_embed(**kwargs):
        texts = kwargs["texts"]

        class _Embeddings:
            float_ = [[float(i)] * 4 for i in range(len(texts))]

        class _Response:
            embeddings = _Embeddings()

        return _Response()

    embedder._client.embed = _fake_embed

    vektorler = await embedder.embed_documents(["a", "b", "c"])

    assert vektorler == [[0.0] * 4, [1.0] * 4, [2.0] * 4]


# ---------------------------------------------------------------------------
# 96 metin/cagri siniri - gruplama
# ---------------------------------------------------------------------------


async def test_96dan_fazla_metin_birden_fazla_cagriya_bolunur(embedder):
    cagri_sayisi = 0
    gorulen_boyutlar: list[int] = []

    async def _fake_embed(**kwargs):
        nonlocal cagri_sayisi
        cagri_sayisi += 1
        gorulen_boyutlar.append(len(kwargs["texts"]))
        return _fake_response(len(kwargs["texts"]))

    embedder._client.embed = _fake_embed

    metinler = [f"metin-{i}" for i in range(150)]
    vektorler = await embedder.embed_documents(metinler)

    assert cagri_sayisi == 2
    assert gorulen_boyutlar == [96, 54]
    assert len(vektorler) == 150


async def test_tam_96_metin_tek_cagriyla_gider(embedder):
    cagri_sayisi = 0

    async def _fake_embed(**kwargs):
        nonlocal cagri_sayisi
        cagri_sayisi += 1
        return _fake_response(len(kwargs["texts"]))

    embedder._client.embed = _fake_embed

    await embedder.embed_documents([f"metin-{i}" for i in range(96)])

    assert cagri_sayisi == 1


# ---------------------------------------------------------------------------
# 429 retry/backoff
# ---------------------------------------------------------------------------


async def test_429da_bekleyip_tekrar_dener_ve_basarili_olur(embedder):
    denemeler = {"n": 0}

    async def _fake_embed(**kwargs):
        denemeler["n"] += 1
        if denemeler["n"] < 3:
            raise TooManyRequestsError(body={"message": "rate limited"})
        return _fake_response(1)

    embedder._client.embed = _fake_embed

    sonuc = await embedder.embed_documents(["tek metin"])

    assert denemeler["n"] == 3
    assert len(sonuc) == 1


async def test_tum_denemeler_429_alirsa_istisna_yeniden_firlatilir(embedder):
    async def _hep_429(**kwargs):
        raise TooManyRequestsError(body={"message": "rate limited"})

    embedder._client.embed = _hep_429

    with pytest.raises(TooManyRequestsError):
        await embedder.embed_documents(["tek metin"])


async def test_429_disindaki_hata_hemen_yukselir_retry_denemez(embedder):
    """429 disi bir hata (orn. kimlik dogrulama, 500) HEMEN yukselmeli -
    bosuna 5 kez denenip dakikalarca beklenmemeli."""
    denemeler = {"n": 0}

    async def _baska_hata(**kwargs):
        denemeler["n"] += 1
        raise ValueError("beklenmeyen hata")

    embedder._client.embed = _baska_hata

    with pytest.raises(ValueError):
        await embedder.embed_documents(["tek metin"])

    assert denemeler["n"] == 1
