# -*- coding: utf-8 -*-
"""Belge/gorsel analiz ajani ve PDF rapor boru hatti testleri.

Bu testler GERCEK dosyalar uretip gercek PDF derler - sahte nesne
kullanmazlar. Sebep: buradaki riskler (Turkce glif kaybi, ReportLab
isaretleme cakismasi, bozuk grafik verisi) yalnizca gercek kutuphane
calistiginda ortaya cikar; mock'lanmis bir test bunlarin hicbirini
yakalayamazdi.
"""

from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

from app.agents.document_analysis import DocumentAnalysisAgent
from app.documents import charts, parser, report
from app.documents.types import AnalizSonucu, AyristirilmisBelge, Gosterge, Grafik, Tablo
from app.orchestration.models import AgentState

# Turkce'nin PDF/font tarafinda en cok sorun cikaran harfleri.
ZOR_HARFLER = "ÇĞİIıÖŞÜçğıöşü"


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------


def _excel_bayt() -> bytes:
    kitap = Workbook()
    sayfa = kitap.active
    sayfa.title = "Bilanço"
    sayfa.append(["Gösterge", "2025", "2026"])
    sayfa.append(["Net Kâr (mn TL)", 1200, 1416])
    sayfa.append(["Özkaynak", 8400, 9100])
    tampon = io.BytesIO()
    kitap.save(tampon)
    return tampon.getvalue()


def _state(dosya_adi: str, icerik: bytes, soru: str = "Özetle") -> AgentState:
    return AgentState(
        user_query=soru,
        user_id=1,
        thread_id=1,
        belge={"dosya_adi": dosya_adi, "icerik": icerik},
    )


def _pdf_metni(pdf: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as belge:
        return "\n".join(sayfa.extract_text() or "" for sayfa in belge.pages)


# ---------------------------------------------------------------------------
# Ayristirma
# ---------------------------------------------------------------------------


def test_excel_turkce_karakterleri_koruyarak_ayristirilir():
    belge = parser.ayristir(_excel_bayt(), "bilanço.xlsx")

    assert belge.tur == "excel"
    assert belge.tablolar
    assert "Gösterge" in belge.tablolar[0].basliklar
    assert belge.tablolar[0].satirlar[0][0] == "Net Kâr (mn TL)"


@pytest.mark.parametrize("dosya_adi", ["belge.docx", "veri.csv", "notlar.txt", "adsiz"])
def test_desteklenmeyen_uzantilar_reddedilir(dosya_adi):
    with pytest.raises(parser.BelgeAyristirmaHatasi):
        parser.belge_turu(dosya_adi)


def test_bozuk_pdf_anlasilir_hata_verir():
    with pytest.raises(parser.BelgeAyristirmaHatasi):
        parser.ayristir(b"bu bir PDF degil", "sahte.pdf")


def test_ozet_girdi_butceyi_asmaz():
    """Kirpma notu butceye DAHIL olmali - aksi halde baglam penceresi tasar."""
    belge = AyristirilmisBelge(tur="pdf", dosya_adi="x.pdf", metin="a" * 5000)

    assert len(belge.ozet_girdi(200)) <= 200
    assert "kırpıldı" in belge.ozet_girdi(200) or "kirpildi" in belge.ozet_girdi(200)


# ---------------------------------------------------------------------------
# Grafik
# ---------------------------------------------------------------------------


def test_bozuk_grafik_verisi_cizilmez_ve_cokmez(tmp_path):
    """Etiket/deger sayisi tutmuyorsa grafik URETILMEZ, istisna da FIRLAMAZ."""
    bozuk = Grafik(tur="bar", etiketler=["a", "b", "c"], degerler=[1.0, 2.0])

    assert bozuk.gecerli_mi() is False
    assert charts.grafik_ciz(bozuk, str(tmp_path)) is None


def test_gecerli_grafik_png_uretir(tmp_path):
    grafik = Grafik(
        tur="bar",
        baslik="Yıllara Göre Net Kâr",
        etiketler=["2024", "2025", "2026"],
        degerler=[980, 1200, 1416],
        eksen_adi="Değişim",
    )
    yol = charts.grafik_ciz(grafik, str(tmp_path))

    assert yol is not None
    assert yol.endswith(".png")


def test_negatif_seri_pasta_yerine_cubuga_duser(tmp_path):
    """Negatif deger pasta grafikte anlamsizdir; sessizce bozuk dilim CIZILMEZ."""
    grafik = Grafik(tur="pie", etiketler=["a", "b"], degerler=[-5.0, 10.0])

    assert charts.grafik_ciz(grafik, str(tmp_path)) is not None


# ---------------------------------------------------------------------------
# PDF raporu
# ---------------------------------------------------------------------------


def test_pdf_turkce_karakterleri_bozmadan_uretir():
    sonuc = AnalizSonucu(
        baslik="Şirket Bilanço Özeti",
        sade_aciklama=f"Zor harfler: {ZOR_HARFLER}",
        ozet="Net kâr %18 arttı, özkaynak güçlendi.",
        gostergeler=[Gosterge(ad="Net Kâr", deger="1,42 milyar TL", sayisal=1416)],
    )
    belge = AyristirilmisBelge(tur="excel", dosya_adi="bilanço.xlsx", sayfa_sayisi=1)

    metin = _pdf_metni(report.rapor_uret(sonuc, belge))

    assert "Şirket Bilanço Özeti" in metin
    for harf in ZOR_HARFLER:
        assert harf in metin, f"'{harf}' harfi PDF'te kayboldu"


def test_pdf_isaretleme_karakterlerini_kacirir():
    """`<`, `>`, `&` ReportLab paragraf ayristiricisini BOZAR - kacirilmali.

    Kacirilmasaydi belgeden gelen "Kâr > Zarar" gibi masum bir metin PDF
    uretimini komple dusururdu.
    """
    sonuc = AnalizSonucu(
        baslik="Test",
        bulgular=["Kâr > Zarar & <riskli> durum"],
    )
    belge = AyristirilmisBelge(tur="pdf", dosya_adi="a.pdf")

    metin = _pdf_metni(report.rapor_uret(sonuc, belge))

    assert "<riskli>" in metin
    assert "Kâr > Zarar &" in metin


def test_bolum_basligi_icerikten_ayri_sayfada_kalmaz(tmp_path):
    """REGRESYON KORUMASI: oksuz baslik.

    Canli testte gorulen hata: sayfayi dolduran uzun bir ozetin ardindan
    "Grafik" basligi 1. sayfanin DIBINDE kaldi, grafik 2. sayfaya dustu.
    `KeepTogether` bunu engeller - baslik ve icerik ayni sayfada olmali.
    """
    import pypdfium2 as pdfium

    grafik = Grafik(tur="bar", baslik="Test", etiketler=["2025", "2026"], degerler=[1200, 1416])
    grafik_yolu = charts.grafik_ciz(grafik, str(tmp_path))

    # Sayfayi neredeyse dolduran icerik: basligin sayfa dibine denk gelmesi
    # icin gereken kosul budur.
    sonuc = AnalizSonucu(
        baslik="Uzun Rapor",
        ozet="Bu cümle sayfayı doldurmak için tekrarlanıyor. " * 40,
        grafik=grafik,
    )
    pdf = report.rapor_uret(sonuc, AyristirilmisBelge(tur="pdf", dosya_adi="a.pdf"), grafik_yolu)

    belge = pdfium.PdfDocument(io.BytesIO(pdf))
    try:
        sayfa_metinleri = [belge[i].get_textpage().get_text_range() for i in range(len(belge))]
    finally:
        belge.close()

    grafik_sayfasi = [i for i, m in enumerate(sayfa_metinleri) if "Grafik" in m]
    assert grafik_sayfasi, "'Grafik' basligi hicbir sayfada bulunamadi"
    # Baslik son sayfada TEK BASINA kalmamali: grafigin oldugu sayfada olmali.
    # Gorsel PDF metnine yansimaz, bu yuzden baslik sayfasinin SON sayfa
    # olmadigini ya da altinda icerik bulundugunu dogruluyoruz.
    baslik_sayfasi = grafik_sayfasi[0]
    kalan = sayfa_metinleri[baslik_sayfasi].split("Grafik", 1)[1]
    assert kalan.strip() or baslik_sayfasi == len(sayfa_metinleri) - 1


def test_ayristirma_uyarilari_rapor_dipnotunda_gorunur():
    """Kullanici raporun neden eksik olabilecegini GORMELI."""
    belge = AyristirilmisBelge(
        tur="pdf",
        dosya_adi="rapor.pdf",
        uyarilar=["12 sayfanın 3 tanesi taranmış görüntü olduğu için okunamadı."],
    )

    metin = _pdf_metni(report.rapor_uret(AnalizSonucu(ozet="x"), belge))

    assert "taranmış görüntü" in metin


# ---------------------------------------------------------------------------
# Ajan - uctan uca
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ajan_llmsiz_calisir_ve_pdf_uretir():
    """LLM bagli degilse deterministik ozet uretilir - rapor YINE cikar."""
    ajan = DocumentAnalysisAgent(mcp_client=None, llm=None, timeout_seconds=60)

    sonuc = await ajan.run(_state("bilanço.xlsx", _excel_bayt()))

    assert sonuc["document_report"]["pdf_bytes"][:4] == b"%PDF"
    assert sonuc["document_data"]["summary_text"]


@pytest.mark.asyncio
async def test_pdf_baytlari_metin_alanina_sizmaz():
    """REGRESYON KORUMASI.

    `document_data` sozlugu `_ajan_metni()` tarafindan metne cevrilir ve
    `summary_text` yoksa `str(sozluk)` yapilir. PDF baytlari ayni sozlukte
    olsaydi ikili icerik kullaniciya gonderilen METNE ve LLM prompt'una ham
    repr olarak dokulurdu.
    """
    from app.engine.orchestrator import _ajan_metni

    ajan = DocumentAnalysisAgent(mcp_client=None, llm=None, timeout_seconds=60)
    sonuc = await ajan.run(_state("bilanço.xlsx", _excel_bayt()))

    assert "pdf_bytes" not in sonuc["document_data"]
    metin = _ajan_metni(sonuc["document_data"])
    assert "%PDF" not in metin
    assert len(metin) < 1000


@pytest.mark.asyncio
async def test_belge_yokken_ajan_sessizce_atlar():
    """Dosya eklenmemis bir turda ajan hicbir sey URETMEMELI."""
    ajan = DocumentAnalysisAgent(mcp_client=None, llm=None, timeout_seconds=60)

    sonuc = await ajan.run(AgentState(user_query="merhaba", user_id=1, thread_id=1))

    assert sonuc == {}


@pytest.mark.asyncio
async def test_gorsel_modeli_yoksa_anlasilir_hata_doner():
    """Vision modeli tanimli degilse 400 beklenmez, ACIK mesaj verilir."""
    ajan = DocumentAnalysisAgent(mcp_client=None, llm=None, timeout_seconds=60)

    sonuc = await ajan.run(_state("ekran.png", b"\x89PNG\r\n"))

    assert sonuc["agent_errors"][0].error_type == "tool_error"
    assert "DOCUMENT_VISION_MODEL" in sonuc["agent_errors"][0].message


@pytest.mark.asyncio
async def test_desteklenmeyen_dosya_ajan_seviyesinde_hataya_cevrilir():
    ajan = DocumentAnalysisAgent(mcp_client=None, llm=None, timeout_seconds=60)

    sonuc = await ajan.run(_state("belge.docx", b"icerik"))

    assert "document_report" not in sonuc
    assert sonuc["agent_errors"][0].error_type == "tool_error"


# ---------------------------------------------------------------------------
# Model JSON ayristirma
# ---------------------------------------------------------------------------


def test_json_cozucu_markdown_cercevesini_soyar():
    """Modeller JSON'u ```json cercevesine alir - ham `json.loads` patlardi."""
    ham = '```json\n{"baslik": "Test", "ozet": "özet"}\n```'

    sonuc = DocumentAnalysisAgent._json_coz(ham)

    assert sonuc is not None
    assert sonuc.baslik == "Test"


def test_json_cozucu_cevresindeki_aciklamayi_atar():
    ham = 'İşte analiz:\n{"baslik": "X", "ozet": "y"}\nUmarım yardımcı olur.'

    sonuc = DocumentAnalysisAgent._json_coz(ham)

    assert sonuc is not None
    assert sonuc.baslik == "X"


def test_json_cozucu_bozuk_girdide_none_doner():
    assert DocumentAnalysisAgent._json_coz("bu JSON degil") is None
    assert DocumentAnalysisAgent._json_coz("") is None


def test_gosterge_cozucu_bozuk_kayitlari_atlar():
    """Bir gostergenin bozuk olmasi digerlerini KAYBETTIRMEMELI."""
    ham = [
        {"ad": "Net Kâr", "deger": "1,4 mlr", "sayisal": 1400},
        {"ad": "", "deger": "bos ad - atlanmali"},
        "sozluk degil - atlanmali",
        {"ad": "Özkaynak", "deger": "9 mlr", "sayisal": "sayi degil"},
    ]

    gostergeler = DocumentAnalysisAgent._gostergeleri_coz(ham)

    assert [g.ad for g in gostergeler] == ["Net Kâr", "Özkaynak"]
    # Sayisal cevrilemedi ama METIN deger korundu: tablo dogru gorunur.
    assert gostergeler[1].sayisal is None
    assert gostergeler[1].deger == "9 mlr"


def test_rapor_dosya_adi_tehlikeli_karakterleri_temizler():
    """Ad `Content-Disposition` basligina girebilir - yol ayraci kalmamali."""
    ad = DocumentAnalysisAgent._rapor_dosya_adi("../../etc/passwd.xlsx")

    assert "/" not in ad
    assert ".." not in ad
    assert ad.endswith("_analiz_raporu.pdf")


# ---------------------------------------------------------------------------
# Orchestrator yonlendirmesi
# ---------------------------------------------------------------------------


async def test_belge_ekliyken_router_belge_ajanini_secer():
    """Finans sinyali OLMAYAN bir cumlede bile ekli dosya belirleyicidir."""
    from app.engine.factory import build_orchestrator
    from app.engine.orchestrator import AGENT_DOCUMENT_ANALYSIS

    orch = build_orchestrator()
    karar = await orch.route_node(
        AgentState(
            user_query="buna bir bakar mısın?",
            user_id=1,
            thread_id=1,
            belge={"dosya_adi": "x.pdf", "icerik": b"x"},
        )
    )

    assert karar["requested_agents"] == [AGENT_DOCUMENT_ANALYSIS]
    # Kapsam kontrolu ATLANMALI: aksi halde sorgu `small_talk`'a duser ve
    # yuklenen belge sessizce yok sayilirdi.
    assert karar["scope"] == "finans"


async def test_belge_yokken_belge_ajani_calismaz():
    from app.engine.factory import build_orchestrator
    from app.engine.orchestrator import AGENT_DOCUMENT_ANALYSIS

    orch = build_orchestrator()

    piyasa = await orch.route_node(
        AgentState(user_query="THYAO hissesi ne durumda?", user_id=1, thread_id=1)
    )
    assert AGENT_DOCUMENT_ANALYSIS not in piyasa["requested_agents"]

    # Devam turu yedegi ("hepsini calistir") de belge ajanini KAPSAMAMALI.
    devam = orch.route_intent(
        AgentState(
            user_query="peki ya şimdi?",
            user_id=1,
            thread_id=1,
            messages=[
                {"role": "user", "content": "önceki"},
                {"role": "user", "content": "peki ya şimdi?"},
            ],
        )
    )
    assert AGENT_DOCUMENT_ANALYSIS not in devam


def test_tablo_ilk_satiri_seyrekse_baslik_sayilmaz():
    """Yanlis baslik varsaymak kullaniciya YANLIS sutun adi gosterirdi."""
    tablo = parser._tablo_olustur([["", "", "x"], ["a", "b", "c"], ["d", "e", "f"]], "test")

    assert isinstance(tablo, Tablo)
    assert tablo.basliklar == []
    assert len(tablo.satirlar) == 3
