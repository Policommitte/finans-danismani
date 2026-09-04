"""RAG alaka esigi (`market_research._drop_irrelevant_sources`).

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


def _scored(*skorlar):
    return [{"score": s, "text": "x"} for s in skorlar]


def test_relevance_threshold_not_applied_outside_sql_path(monkeypatch):
    """Bellek ici depo `hits/len(terms)` orani uretir - BASKA BIR OLCEK.

    0.75 esigi o olcekte "terimlerin dortte ucu eslesmeli" demek olur ve
    normal sorgulari eler. Olculdu: bu koruma olmadan dokuz mevcut test
    kirmiziya donuyordu.
    """
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "")  # -> database_enabled False

    chunks = _scored(0.5, 0.4)
    assert mr._drop_irrelevant_sources(chunks) == chunks


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
def test_relevance_threshold_applied_to_whole_set(monkeypatch, skorlar, kalan):
    """Eleme tek tek chunk'lara DEGIL, setin tamamina uygulanir.

    Bir konu gercekten eslesiyorsa kuyruktaki dusuk skorlu parcalar da o
    konuya aittir ("altin" sorgusunda 1.9'un ardindaki 0.7'ler gercek altin
    haberleri). Elenmesi gereken sey satirlar degil, HICBIR SEYIN
    eslesmedigi durumdur.
    """
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "postgresql://x/y")

    assert len(mr._drop_irrelevant_sources(_scored(*skorlar))) == kalan


def test_relevance_threshold_skipped_on_rrf_scale(monkeypatch):
    """Hibrit arama acilinca skorlar RRF'e doner (~0.016).

    BM25'e gore secilmis esik orada TUM kaynaklari elerdi. Yanlis esik,
    esiksizlikten daha kotudur.
    """
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "postgresql://x/y")

    chunks = _scored(0.0164, 0.0161)
    assert mr._drop_irrelevant_sources(chunks) == chunks


def test_relevance_threshold_does_not_filter_without_score(monkeypatch):
    from app.agents import market_research as mr

    monkeypatch.setattr(mr.settings, "rag_min_score", 0.75)
    monkeypatch.setattr(mr.settings, "database_url", "postgresql://x/y")

    chunks = [{"text": "skor alani yok"}, {"text": "yine yok"}]
    assert mr._drop_irrelevant_sources(chunks) == chunks


# ---------------------------------------------------------------------------
# Kalibrasyon log satiri
# ---------------------------------------------------------------------------


def test_alaka_skorlari_log_satiri_skorlari_ve_filtreyi_yazar(caplog):
    """Esik kalibrasyonunun TEK gorunur kaynagi bu satirdir.

    ⚠️ `caplog.set_level` SART: fonksiyon `logger.isEnabledFor(INFO)` ile
    erken doner. Ortam log seviyesine guvenen bir test, seviye INFO'nun
    ustune cikinca govdeyi hic calistirmadan yesil kalirdi - migrasyon
    sirasinda olculdu: 5 satir sessizce kapsamsiz kaldi.
    """
    import logging

    from app.agents.market_research import _alaka_skorlarini_logla

    caplog.set_level(logging.INFO, logger="app.agents.market_research")
    _alaka_skorlarini_logla(
        "aselsan haberleri",
        [
            {"cos_sim": 0.4213, "baslik": "Aselsan bilanco"},
            {"cos_sim": None, "source": "BM25 kaydi"},
        ],
        {"symbol": "ASELS"},
        arama="aselsan savunma sanayi",
    )

    (kayit,) = [k for k in caplog.records if "rag alaka skorlari" in k.getMessage()]
    metin = kayit.getMessage()
    assert "0.421 Aselsan bilanco" in metin
    # `cos_sim` yoksa (BM25 yolu) skor yerine "-" yazilir.
    assert "- BM25 kaydi" in metin
    # Filtre ve damitilmis arama metni de gorunmeli - "sonuc yok" un sebebi
    # esik mi yoksa daraltilmis filtre mi, ayirt edilebilsin.
    assert "'symbol': 'ASELS'" in metin
    assert "aselsan savunma sanayi" in metin


def test_alaka_skorlari_log_satiri_INFO_kapaliyken_calismaz(caplog):
    """Erken donus: INFO kapaliysa bicimleme maliyeti odenmemeli."""
    import logging

    from app.agents.market_research import _alaka_skorlarini_logla

    caplog.set_level(logging.WARNING, logger="app.agents.market_research")
    _alaka_skorlarini_logla("x", [{"cos_sim": 0.5, "baslik": "y"}])

    assert not [k for k in caplog.records if "rag alaka skorlari" in k.getMessage()]
