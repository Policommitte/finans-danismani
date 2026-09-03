"""`app.ingestion.chunking` - iki asamali bolme.

SOZLESME: bir chunk icin nihai metni hangi bolucu uretiyorsa YALNIZCA o
kaydedilir. Tasan bir semantik parca TAMAMEN atilir ve yerine
`recursive_split` alt-parcalari konur - ikisi birden asla saklanmaz.
Aksi halde ayni metin RAG indeksinde iki kez yer alir ve arama sonucu
kendini tekrarlar.
"""

from __future__ import annotations

import pytest

from app.ingestion.chunking import (
    DEFAULT_MAX_CHUNK_CHARS,
    chunk_document,
    recursive_split,
    semantic_split,
)

# --- semantic_split -------------------------------------------------------


def test_paragraflar_konu_siniri_sayilir():
    assert semantic_split("Birinci paragraf.\n\nIkinci paragraf.") == [
        "Birinci paragraf.",
        "Ikinci paragraf.",
    ]


def test_paragraf_araligindaki_bosluk_toleranslidir():
    """Kaynak metinlerde "\\n   \\n" yaygin."""
    assert len(semantic_split("A\n   \nB")) == 2


def test_paragraf_yoksa_metin_tek_parca_kalir():
    assert semantic_split("Tek satirlik metin") == ["Tek satirlik metin"]


@pytest.mark.parametrize("girdi", ["", "   ", "\n\n\n"])
def test_bos_metin_parca_uretmez(girdi):
    assert semantic_split(girdi) == []


def test_bos_paragraflar_atilir():
    assert semantic_split("A\n\n\n\n\n\nB") == ["A", "B"]


# --- recursive_split ------------------------------------------------------


def test_sinira_uyan_metin_bolunmez():
    assert recursive_split("kisa metin", 100) == ["kisa metin"]


def test_her_parca_sinira_uyar():
    metin = ". ".join(f"cumle numara {i}" for i in range(200))
    for parca in recursive_split(metin, 120):
        assert len(parca) <= 120


def test_ayirici_kalmayinca_sert_kesime_dusulur():
    """Bosluksuz tek kelime - hicbir ayirici ise yaramaz."""
    parcalar = recursive_split("x" * 250, 100)
    assert [len(p) for p in parcalar] == [100, 100, 50]


def _harfler(metin: str) -> str:
    """Bosluk/satir sonu farklarini yok sayar - ayiricilar bolmede kaybolur
    ya da chunk icinde kalir, iddia ICERIK uzerinedir."""
    return "".join(metin.split())


def test_bolme_icerigi_kaybetmez():
    metin = "\n\n".join(f"paragraf {i} icerigi biraz uzun" for i in range(40))
    assert _harfler("".join(recursive_split(metin, 80))) == _harfler(metin)


def test_tek_basina_tasan_parca_daha_ince_ayiriciyla_bolunur():
    """Ilk ayirici ise yaramazsa bir sonrakine gecilir."""
    metin = "kelime " * 60  # "\n\n" yok, " " var
    parcalar = recursive_split(metin, 100)
    assert len(parcalar) > 1
    assert all(len(p) <= 100 for p in parcalar)


# --- chunk_document -------------------------------------------------------


def test_sinira_uyan_paragraflar_oldugu_gibi_gecer():
    metin = "Kisa paragraf bir.\n\nKisa paragraf iki."
    assert chunk_document(metin, max_chars=100) == [
        "Kisa paragraf bir.",
        "Kisa paragraf iki.",
    ]


def test_tasan_paragraf_atilir_yerine_alt_parcalari_konur():
    """ASIL SOZLESME. Tasan parcanin KENDISI ciktida OLMAMALI."""
    tasan = "cumle. " * 60
    kisa = "kisa paragraf"
    parcalar = chunk_document(f"{tasan.strip()}\n\n{kisa}", max_chars=100)

    assert tasan.strip() not in parcalar
    assert kisa in parcalar
    assert all(len(p) <= 100 for p in parcalar)
    assert len(parcalar) > 2  # tasan parca birden fazla alt-parcaya bolundu


def test_bos_dokuman_chunk_uretmez():
    assert chunk_document("") == []


def test_varsayilan_sinir_uygulanir():
    metin = "kelime " * 1000
    assert all(len(p) <= DEFAULT_MAX_CHUNK_CHARS for p in chunk_document(metin))


def test_ayni_metin_ayni_chunk_larini_uretir():
    """Yeniden indeksleme mukerrer kayit uretmemeli."""
    metin = "A" * 50 + "\n\n" + "kelime " * 300
    assert chunk_document(metin) == chunk_document(metin)
