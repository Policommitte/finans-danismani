"""Chunking mantiginin saf testleri (`app/ingestion/chunking.py`).

BU TESTLER AGA/DB'YE CIKMAZ: `semantic_split`/`recursive_split`/`chunk_document`
tamamen saf fonksiyonlardir, hicbir yan etkileri yoktur.

Kritik davranislar:
  * KURAL: nihai chunk metnini hangi bolucu URETIYORSA yalnizca o saklanir -
    asiri buyuk bir semantik parca TAMAMEN atilir; pre-split hali asla
    recursive alt-parcalarla birlikte sonuc listesinde yer almaz.
  * `recursive_split`'in urettigi hicbir parca `max_chars`i asmaz - ayirici
    tukenirse bile (hard slice) sinir korunur, sonsuz donguye girmez.
  * Bos/bosluk-only girdi bos liste doner, hata firlatmaz.
"""

from app.ingestion.chunking import (
    DEFAULT_MAX_CHUNK_CHARS,
    chunk_document,
    recursive_split,
    semantic_split,
)

# ---------------------------------------------------------------------------
# semantic_split
# ---------------------------------------------------------------------------


def test_paragraflari_bos_satirdan_ayirir():
    metin = "Birinci paragraf.\n\nIkinci paragraf."
    assert semantic_split(metin) == ["Birinci paragraf.", "Ikinci paragraf."]


def test_tek_paragraf_tek_elemanli_liste_doner():
    assert semantic_split("Tek paragraf, ayirici yok.") == ["Tek paragraf, ayirici yok."]


def test_bos_metin_bos_liste_doner():
    assert semantic_split("") == []


def test_sadece_bosluk_bos_liste_doner():
    assert semantic_split("   \n\n   ") == []


def test_coklu_bos_satir_tek_ayirici_gibi_davranir():
    """`\\n\\s*\\n` iki veya daha fazla bos satiri da tek sinir sayar."""
    assert semantic_split("Birinci.\n\n\n\nIkinci.") == ["Birinci.", "Ikinci."]


def test_paragraf_kenar_bosluklari_temizlenir():
    metin = "  Birinci paragraf.  \n\n  Ikinci paragraf.  "
    assert semantic_split(metin) == ["Birinci paragraf.", "Ikinci paragraf."]


def test_bos_paragraflar_atlanir():
    """Iki ayirici arasinda sadece bosluk olan 'paragraf' sonuca girmez."""
    metin = "Birinci.\n\n   \n\nIkinci."
    assert semantic_split(metin) == ["Birinci.", "Ikinci."]


# ---------------------------------------------------------------------------
# recursive_split
# ---------------------------------------------------------------------------


def test_sinir_altindaki_metin_bolunmez():
    assert recursive_split("kisa metin", max_chars=100) == ["kisa metin"]


def test_tam_sinirdaki_metin_bolunmez():
    """`<=` kontrolu: tam sinira esit uzunluk bolme tetiklemez."""
    metin = "a" * 50
    assert recursive_split(metin, max_chars=50) == [metin]


def test_uretilen_hicbir_parca_siniri_asmaz():
    metin = ("Cumle bir. " * 50) + "\n\n" + ("Cumle iki. " * 50)
    parcalar = recursive_split(metin, max_chars=100)

    assert all(len(p) <= 100 for p in parcalar)
    assert len(parcalar) > 1


def test_kucuk_parcalar_ac_gozlu_birlestirilir():
    """Verimlilik: siniri asmayan ardisik parcalar mumkun oldugunca TEK
    chunk'ta birlesir - her kelime kendi chunk'ina dusmez."""
    kelimeler = [f"kelime{i}" for i in range(30)]
    metin = ". ".join(kelimeler) + "."

    parcalar = recursive_split(metin, max_chars=40)

    assert all(len(p) <= 40 for p in parcalar)
    assert len(parcalar) < len(kelimeler)


def test_ayirici_tukenince_karakter_bazli_kesilir():
    """Hicbir ayirici bulunamayan (bosluksuz) tek bir 'kelime' icin son care:
    sabit uzunlukta hard slice - sonsuz donguye girmez."""
    metin = "a" * 250
    parcalar = recursive_split(metin, max_chars=100, separators=())

    assert parcalar == ["a" * 100, "a" * 100, "a" * 50]


def test_ic_ice_ayiricilara_duser():
    """Paragraf ayiricisi (\\n\\n) tek parcayi bolemezse siradaki (\\n,
    sonra '. ', sonra bosluk) denenir."""
    metin = "Cok uzun tek bir paragraf kelimesi " * 10  # \n yok, yalnizca bosluk
    parcalar = recursive_split(metin, max_chars=50)

    assert all(len(p) <= 50 for p in parcalar)


def test_veri_kaybi_olmaz():
    """Parcalari bosluktan geri birlestirince orijinal kelimeler kaybolmaz."""
    metin = ("kelime " * 30).strip()
    parcalar = recursive_split(metin, max_chars=40)

    birlesik_kelimeler = " ".join(parcalar).split()
    assert birlesik_kelimeler == metin.split()


def test_bos_metin_tek_elemanli_liste_doner():
    """Bos metin de `max_chars` altinda sayilir - `chunk_document` zaten
    onceden `semantic_split` ile bos parcalari eledigi icin buraya normalde
    ulasmaz, ama fonksiyon tek basina cagrilirsa da guvenli olmali."""
    assert recursive_split("", max_chars=10) == [""]


# ---------------------------------------------------------------------------
# chunk_document - iki asamali kural
# ---------------------------------------------------------------------------


def test_sinir_ici_paragraflar_degismeden_gecer():
    metin = "Kisa birinci.\n\nKisa ikinci."
    assert chunk_document(metin, max_chars=100) == ["Kisa birinci.", "Kisa ikinci."]


def test_asiri_buyuk_paragraf_tamamen_atilip_alt_parcalarla_degistirilir():
    """KURAL: pre-split (oversized) hali NIHAI listede asla gorunmez - yalnizca
    `recursive_split`'in urettigi alt-parcalar bulunur, ikisi birden asla
    saklanmaz."""
    kisa = "Kisa paragraf."
    uzun = "Uzun cumle burada tekrarlaniyor. " * 20
    metin = f"{kisa}\n\n{uzun}"

    sonuc = chunk_document(metin, max_chars=100)

    assert kisa in sonuc  # sinir ici parca degismeden kaldi
    assert uzun.strip() not in sonuc  # oversized ORIJINAL asla saklanmadi
    assert all(len(p) <= 100 for p in sonuc)
    assert len(sonuc) > 2  # kisa + birden fazla alt-parca


def test_karisik_belge_sirasini_korur():
    """Sinir ici ve sinir disi paragraflar karisik oldugunda cikti sirasi
    orijinal paragraf sirasini takip eder."""
    metin = "Once kisa.\n\n" + ("Uzun cumle. " * 30) + "\n\nSonra kisa."
    sonuc = chunk_document(metin, max_chars=50)

    assert sonuc[0] == "Once kisa."
    assert sonuc[-1] == "Sonra kisa."


def test_bos_dokuman_bos_liste_doner():
    assert chunk_document("", max_chars=100) == []


def test_sadece_bosluk_dokuman_bos_liste_doner():
    assert chunk_document("   \n\n   ", max_chars=100) == []


def test_varsayilan_max_chars_kullanilir():
    metin = "kisa"
    assert chunk_document(metin) == chunk_document(metin, max_chars=DEFAULT_MAX_CHUNK_CHARS)


def test_birden_fazla_asiri_buyuk_paragraf_hepsi_degistirilir():
    """Iki farkli paragraf da siniri asarsa HER IKISI de kendi alt-parcalariyla
    degistirilir - yalnizca ilki degil."""
    uzun_bir = "Birinci uzun paragraf metni. " * 20
    uzun_iki = "Ikinci uzun paragraf metni. " * 20
    metin = f"{uzun_bir}\n\n{uzun_iki}"

    sonuc = chunk_document(metin, max_chars=100)

    assert uzun_bir.strip() not in sonuc
    assert uzun_iki.strip() not in sonuc
    assert all(len(p) <= 100 for p in sonuc)
