"""RAG alaka esigi (`market_research._alakasiz_kaynaklari_ele`).

AYRI DOSYADA: `test_market_research_agent.py` bastan asagi
`pytestmark = pytest.mark.db` tasiyor ve DB olmadan tamamen atlaniyor.
Buradaki testler saf birim testidir, veritabani ISTEMEZ - o dosyaya
konsalardi CI'da hic kosmazlardi.

NEDEN KAPSAM KRITIK: esik yalnizca SQL deposu devredeyken calisir ve CI'da
`DATABASE_URL` tanimli DEGILDIR (yalnizca `TEST_DATABASE_URL`), yani uctan
uca hicbir test bu kodu tetiklemez. Fonksiyon dogrudan cagrilmazsa tamamen
kapsamsiz kalir.
"""

import pytest


def _skorlu(*skorlar):
    return [{"score": s, "text": "x"} for s in skorlar]


def test_alaka_esigi_sql_yolu_disinda_uygulanmaz(monkeypatch):
    """Bellek ici depo `hits/len(terms)` orani uretir - BASKA BIR OLCEK.

    0.75 esigi o olcekte "terimlerin dortte ucu eslesmeli" demek olur ve
    normal sorgulari eler. Olculdu: bu koruma olmadan dokuz mevcut test
    kirmiziya donuyordu.
    """
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "")  # -> database_enabled False

    chunks = _skorlu(0.5, 0.4)
    assert mr._alakasiz_kaynaklari_ele(chunks) == chunks


@pytest.mark.parametrize(
    "skorlar, kalan",
    [
        # Canli Supabase'de olculdu (1 Eylul 2026):
        ((0.5, 0.4, 0.2), 0),  # "portfoyum neden dustu"  -> alakasiz
        ((0.7, 0.5, 0.4), 0),  # "savunma sanayi/aselsan" -> alakasiz
        ((0.9, 0.9, 0.7), 3),  # "enflasyon ve faiz"      -> alakali
        ((1.9, 0.7, 0.7), 3),  # "altin fiyatlari"        -> alakali
    ],
)
def test_alaka_esigi_setin_tamamina_uygulanir(monkeypatch, skorlar, kalan):
    """Eleme tek tek chunk'lara DEGIL, setin tamamina uygulanir.

    Bir konu gercekten eslesiyorsa kuyruktaki dusuk skorlu parcalar da o
    konuya aittir ("altin" sorgusunda 1.9'un ardindaki 0.7'ler gercek altin
    haberleri). Elenmesi gereken sey satirlar degil, HICBIR SEYIN
    eslesmedigi durumdur.
    """
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "postgresql://x/y")

    assert len(mr._alakasiz_kaynaklari_ele(_skorlu(*skorlar))) == kalan


def test_alaka_esigi_rrf_olceginde_atlanir(monkeypatch):
    """Hibrit arama acilinca skorlar RRF'e doner (~0.016).

    BM25'e gore secilmis esik orada TUM kaynaklari elerdi. Yanlis esik,
    esiksizlikten daha kotudur.
    """
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "postgresql://x/y")

    chunks = _skorlu(0.0164, 0.0161)
    assert mr._alakasiz_kaynaklari_ele(chunks) == chunks


def test_alaka_esigi_skor_yoksa_eleme_yapmaz(monkeypatch):
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "postgresql://x/y")

    chunks = [{"text": "skor alani yok"}, {"text": "yine yok"}]
    assert mr._alakasiz_kaynaklari_ele(chunks) == chunks
