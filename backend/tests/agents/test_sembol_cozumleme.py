"""Sorgudan varlik sembolu cozme (`app/agents/market_research.py::resolve_symbol`).

NEDEN AYRI DOSYA: `resolve_symbol` SAF bir fonksiyondur - veritabani istemez.
`test_market_research_agent.py` ise `pytest.mark.db` tasidigi icin DB'siz
ortamda tamamen atlanir; bu testler orada dursaydi CI'da hic calismazdi.

GERCEK BIR HATADAN TURETILDI (27 Agustos 2026)
    Kullanici ekranin ust seridinde dolar kurunu 48,2409 olarak GORURKEN
    asistana "dolar kuru ne olur?" diye sordu ve su yaniti aldi:

        "Verilen kaynaklarda dolar kuru hakkinda bilgi bulunmamaktadir."

    Fiyat veritabaninda HAZIRDI. Sorun sembol cozumlemesindeydi: sembol
    bulunamayinca canli fiyat yolu hic acilmiyor, ajan haber indeksine
    dusuyordu. Denetimde 42 varligin 11'inde ayni kor nokta cikti.

UC AYRI KUSUR VARDI
    1. AYIRAC KARAKTERLI KODLAR: sorgu `[a-z0-9]+` ile token'lara ayrildigi
       icin "usd/try" ve "brk-b" hicbir zaman tek bir token'a esit olamaz -
       bu kodlarla eslesme YAPISAL OLARAK imkansizdi.
    2. KISA KODLAR: `_ASGARI_SEMBOL_UZUNLUGU = 3` altindaki kodlar (KO, T)
       tamamen eleniyordu.
    3. AD ESLESMESI: ilk kelimeden en az 5 harf isteniyordu; "BIM", "Koc",
       "Turk" gibi ilk kelimeler bu esigin altinda kaliyordu. Ayrica USD/TRY'nin
       adi "Amerikan Dolari" - kullanici "dolar" der, ilk kelime "amerikan".
"""

import pytest

from app.agents.market_research import (
    MarketResearchAgent,
    _dokuman_bazinda_tekille,
    _icerikten_baslik,
    resolve_symbol,
)

#: Gercek `assets` tablosundaki adlarla ayni - kisaltilmis katalog.
KATALOG = [
    {"symbol": "USD/TRY", "ad": "Amerikan Doları"},
    {"symbol": "EUR/TRY", "ad": "Euro"},
    {"symbol": "GRAM_ALTIN", "ad": "Gram Altın"},
    {"symbol": "GUMUS", "ad": "Gram Gümüş"},
    {"symbol": "THYAO", "ad": "Türk Hava Yolları"},
    {"symbol": "BIMAS", "ad": "BIM Birlesik Magazalar"},
    {"symbol": "KCHOL", "ad": "Koc Holding"},
    {"symbol": "ASELS", "ad": "Aselsan"},
    {"symbol": "SASA", "ad": "Sasa Polyester"},
    {"symbol": "BTC", "ad": "Bitcoin"},
    {"symbol": "BRK-B", "ad": "Berkshire Hathaway Inc."},
    {"symbol": "KO", "ad": "Coca-Cola Company"},
    {"symbol": "T", "ad": "AT&T Inc."},
    {"symbol": "LLY", "ad": "Eli Lilly and Company"},
    {"symbol": "BRENT", "ad": "Ham Petrol (BRENT)"},
    {"symbol": "US10Y", "ad": "US 10 Yil Tahvil Getirisi"},
]


@pytest.mark.parametrize(
    "sorgu, beklenen",
    [
        # ⚠️ RAPOR EDILEN HATA: bu satir kirmiziya donerse hata geri gelmis
        # demektir - kullanici ekranda kuru gorurken asistan "bilgi yok" der.
        ("dolar kuru ne olur", "USD/TRY"),
        ("dolar ne kadar", "USD/TRY"),
        ("doları kaç lira", "USD/TRY"),
        ("usd try kuru ne", "USD/TRY"),
        ("euro ne kadar", "EUR/TRY"),
        ("altin ne kadar", "GRAM_ALTIN"),
        ("gram altin ne kadar", "GRAM_ALTIN"),
        # Adin ilk kelimesi 5 harften kisa
        ("bim ne kadar", "BIMAS"),
        ("koc holding ne kadar", "KCHOL"),
        ("thy ne kadar", "THYAO"),
        ("lilly ne kadar", "LLY"),
        ("petrol ne kadar", "BRENT"),
        ("berkshire ne kadar", "BRK-B"),
        ("coca cola ne kadar", "KO"),
        ("tahvil getirisi ne", "US10Y"),
        # Zaten calisanlar - regresyon korumasi
        ("THYAO ne kadar", "THYAO"),
        ("aselsan nasil gidiyor", "ASELS"),
        ("sasa neden dustu", "SASA"),
        ("turk hava yollari nasil", "THYAO"),
    ],
)
def test_gunluk_dilde_sorulan_varliklar_cozulur(sorgu, beklenen):
    assert resolve_symbol(sorgu, KATALOG) == beklenen


@pytest.mark.parametrize(
    "sorgu, beklenen",
    [
        # AYIRAC KARAKTERLI KODLAR - sorgu token'lara bolununce parcalanir.
        ("USD/TRY kuru ne", "USD/TRY"),
        ("EUR/TRY ne kadar", "EUR/TRY"),
        ("BRK-B fiyati", "BRK-B"),
        ("brkb ne kadar", "BRK-B"),
        ("usdtry kac", "USD/TRY"),
        ("GRAM_ALTIN ne kadar", "GRAM_ALTIN"),
        # KISA KODLAR - `_ASGARI_SEMBOL_UZUNLUGU` esiginin altinda.
        ("KO ne kadar", "KO"),
        ("T hissesi ne kadar", "T"),
    ],
)
def test_kod_birebir_yazildiginda_cozulur(sorgu, beklenen):
    assert resolve_symbol(sorgu, KATALOG) == beklenen


@pytest.mark.parametrize(
    "sorgu",
    [
        # ⚠️ "altin" EKLI eslesmeyle aransaydi "altinda" da yakalanirdi.
        # Takma adlar bu yuzden TAM TOKEN ile eslesir.
        "portfoyumun altinda ne var",
        "masanin altindaki dosya",
        # ⚠️ "eli" (LLY'nin ad ilk kelimesi) Turkce bir kelimedir - kok olarak
        # EKLENMEDI, yalnizca "lilly" takma ad listesinde.
        "elinde ne kadar var",
        # ⚠️ Kisa kodlar YALNIZCA BUYUK HARFLE kabul edilir; kucuk harfli
        # gunluk kelimeler sembol sanilmamali.
        "ko ne demek",
        "t harfi nedir",
        # Sembol icermeyen normal sorular
        "portfoyum nasil",
        "riskim ne durumda",
        "merhaba nasilsin",
        "kocaelispor mac skoru",
    ],
)
def test_gunluk_kelimeler_sembol_sanilmaz(sorgu):
    assert resolve_symbol(sorgu, KATALOG) is None


def test_katalogda_olmayan_takma_ad_uretilmez():
    """Takma ad tablosu KATALOGU EZEMEZ.

    `resolve_symbol`'un temel kurali: veritabaninda gercekten var olmayan hicbir
    sey sembol sayilmaz. USD/TRY katalogdan cikarilirsa "dolar" da cozulmemeli -
    aksi halde tablo, silinmis bir varlik icin sessizce sembol uretmeye devam
    ederdi ve fiyat sorgusu bos donerdi.
    """
    dolarsiz = [k for k in KATALOG if k["symbol"] != "USD/TRY"]

    assert resolve_symbol("dolar kuru ne olur", dolarsiz) is None


def test_bos_katalogda_sembol_uretilmez():
    assert resolve_symbol("dolar kuru ne olur", []) is None


# ---------------------------------------------------------------------------
# Kaynak listesi: ayni haber iki kez gorunmemeli
# ---------------------------------------------------------------------------
#
# GERCEK HATA (27 Agustos 2026): kullanici yanit altindaki kaynak listesinde
# ilk iki satirin AYNI haberi gosterdigini bildirdi.
#
# Iki sebep birden vardi:
#   1. `rag_search` CHUNK dondurur, dokuman degil. Bir haber ortalama 4
#      chunk'a bolunuyor (234 dokuman -> 917 chunk), bu yuzden top_k=5
#      sonucun bir kismi ayni habere ait oluyordu.
#   2. Dokumanlarin %35'inde (82/234) `baslik` BOS. Baslik bos olunca kaynak
#      satiri "(2026-08-13) · BigPara Borsa" seklinde kaliyor ve ayni siteden
#      gelen FARKLI haberler birebir ayni gorunuyordu.


def test_ayni_dokumanin_chunklari_tek_kaynaga_iner():
    chunks = [
        {"doc_id": "d1", "chunk_id": "c1", "score": 0.9},
        {"doc_id": "d1", "chunk_id": "c2", "score": 0.7},
        {"doc_id": "d1", "chunk_id": "c3", "score": 0.5},
        {"doc_id": "d2", "chunk_id": "c4", "score": 0.8},
    ]

    tekil = _dokuman_bazinda_tekille(chunks)

    assert len(tekil) == 2
    # Her dokumandan EN YUKSEK skorlu chunk secilmeli.
    assert {c["chunk_id"] for c in tekil} == {"c1", "c4"}


def test_doc_id_yoksa_chunklar_birlestirilmez():
    """`doc_id` bos gelirse farkli dokumanlar yanlislikla tek satira inmemeli."""
    chunks = [
        {"doc_id": None, "chunk_id": "c1", "score": 0.9},
        {"doc_id": None, "chunk_id": "c2", "score": 0.8},
    ]

    assert len(_dokuman_bazinda_tekille(chunks)) == 2


def test_basliksiz_dokuman_icerikten_okunabilir_baslik_alir():
    """Baslik bossa metnin ilk cumlesi kullanilir - satirlar ayirt edilebilsin."""
    kaynak = MarketResearchAgent._to_source(
        {
            "doc_id": "d1",
            "title": "",
            "content": "BIST 100 endeksi gunun ilk yarisinda yukseldi. Kapanista yatay seyretti.",
            "date": "2026-08-13",
            "source": "BigPara Borsa",
        }
    )

    assert kaynak.baslik == "BIST 100 endeksi gunun ilk yarisinda yukseldi."
    # Eski davranis (yalnizca tarih + site adi) geri gelmemeli.
    assert kaynak.baslik != "BigPara Borsa (2026-08-13)"


def test_baslik_da_icerik_de_yoksa_kaynak_ve_tarihe_dusulur():
    kaynak = MarketResearchAgent._to_source(
        {"doc_id": "d1", "title": "", "content": "", "date": "2026-08-13", "source": "BigPara"}
    )

    assert kaynak.baslik == "BigPara (2026-08-13)"


def test_dokumanin_kendi_basligi_varsa_o_kullanilir():
    """Icerikten uretim yalnizca YEDEKTIR; gercek baslik her zaman kazanir."""
    kaynak = MarketResearchAgent._to_source(
        {
            "doc_id": "d1",
            "title": "Altında kâr realizasyonu",
            "content": "Bambaska bir ilk cumle.",
            "date": "2026-08-14",
        }
    )

    assert kaynak.baslik == "Altında kâr realizasyonu"


def test_uzun_icerik_kelime_sinirinda_kirpilir():
    uzun = "kelime " * 40
    baslik = _icerikten_baslik(uzun)

    assert len(baslik) <= 81  # 80 + kirpma isareti
    assert baslik.endswith("…")
