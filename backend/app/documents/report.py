"""`AnalizSonucu` -> okunabilir Turkce PDF (ReportLab).

NEDEN ReportLab (WeasyPrint DEGIL)
----------------------------------
Ilk tercih WeasyPrint'ti (HTML/CSS -> PDF). Gelistirme makinesinde denendi ve
IMPORT BILE EDILEMEDI: `libgobject-2.0-0` bulunamadi - WeasyPrint GTK/Pango/
Cairo sistem kutuphanelerine baglidir ve bunlar Windows'ta ayrica kurulur.
Ayni bagimlilik CI ve production imajina da yansirdi.

ReportLab saf Python'dur, sistem kutuphanesi istemez ve FinRobot'un da
kullandigi kutuphanedir. Turkce karakterler `fonts.py` icinde kaydedilen
DejaVu ile garanti altina alinir (ReportLab'in gomulu Helvetica'si Latin-1
oldugu icin `g`, `s`, `I`, `i` harflerini TASIMAZ).

RAPOR DILI
----------
Urun karari: rapor FINANS TERIMI BILMEYEN bir kullaniciya yazilir. Bu dosya
duzeni saglar; sadelestirme LLM prompt'unda zorlanir (bkz.
`agents/document_analysis.py`). Duzen tarafinda buna hizmet eden secimler:
  * Tek kolon (FinRobot'un iki kolonlu duzeni yatirim raporu icindir, sade
    ozet icin okumayi zorlastirir).
  * Once "Kisaca ne anlama geliyor" bolumu, teknik doküm sonra.
  * Her bolum baslikli ve kisa - duvar metin yok.
"""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO

from app.documents.fonts import KALIN, NORMAL, turkce_fontlari_kur
from app.documents.types import AnalizSonucu, AyristirilmisBelge

logger = logging.getLogger(__name__)

#: PDF'te gosterilecek azami gosterge/madde sayisi. Sinir yoksa model uzun
#: bir liste dondurdugunde rapor "sade ozet" olmaktan cikar.
AZAMI_GOSTERGE = 12
AZAMI_MADDE = 8


def _stiller():
    """Rapor stilleri. Tum metin stilleri DejaVu tabanlidir."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    return {
        "baslik": ParagraphStyle(
            "baslik",
            fontName=KALIN,
            fontSize=18,
            leading=23,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=2,
        ),
        "altbaslik": ParagraphStyle(
            "altbaslik",
            fontName=NORMAL,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=14,
        ),
        "bolum": ParagraphStyle(
            "bolum",
            fontName=KALIN,
            fontSize=12.5,
            leading=16,
            textColor=colors.HexColor("#1e3a8a"),
            spaceBefore=14,
            spaceAfter=6,
        ),
        "govde": ParagraphStyle(
            "govde",
            fontName=NORMAL,
            fontSize=10.5,
            leading=15.5,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=5,
        ),
        "madde": ParagraphStyle(
            "madde",
            fontName=NORMAL,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#1f2937"),
            leftIndent=12,
            bulletIndent=2,
            spaceAfter=3,
        ),
        "dipnot": ParagraphStyle(
            "dipnot",
            fontName=NORMAL,
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#64748b"),
            spaceBefore=4,
        ),
    }


def _kacisli(metin: str) -> str:
    """Metni ReportLab paragraf isaretlemesine karsi guvenli hale getirir.

    ⚠️ ZORUNLU: `Paragraph` icerigi mini-HTML olarak AYRISTIRIR. Belgeden
    gelen "Kar > Zarar" ya da "<Sirket A.S.>" gibi bir metin ayristiriciyi
    bozar ve PDF uretimi komple coker. Kullanici verisi asla ham gecmez.
    """
    return str(metin).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _gosterge_tablosu(sonuc: AnalizSonucu, genislik: float):
    """Sayisal gostergeleri iki sutunlu ozet tablosuna cevirir."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    veri = [["Gösterge", "Değer"]]
    for gosterge in sonuc.gostergeler[:AZAMI_GOSTERGE]:
        veri.append([_kacisli(gosterge.ad), _kacisli(gosterge.deger)])

    tablo = Table(veri, colWidths=[genislik * 0.55, genislik * 0.45], hAlign="LEFT")
    tablo.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), NORMAL),
                ("FONTNAME", (0, 0), (-1, 0), KALIN),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e7ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                # Satir bazli zebra: uzun tabloda goz kaymasini onler.
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    return tablo


def _madde_listesi(basliklar: list[str], stil) -> list:
    """Madde imli paragraflar uretir."""
    from reportlab.platypus import Paragraph

    return [
        Paragraph(_kacisli(metin), stil, bulletText="•")
        for metin in basliklar[:AZAMI_MADDE]
        if str(metin).strip()
    ]


def rapor_uret(
    sonuc: AnalizSonucu,
    belge: AyristirilmisBelge,
    grafik_yolu: str | None = None,
) -> bytes:
    """Analiz sonucunu PDF baytlarina cevirir.

    Args:
        sonuc: LLM'in urettigi yapilandirilmis analiz.
        belge: Kaynak belge - dipnotta adi ve uyarilari gosterilir.
        grafik_yolu: `charts.grafik_ciz` ciktisi; `None` ise grafik bolumu
            hic cizilmez.

    Returns:
        PDF icerigi. Dosyaya YAZILMAZ - cagiran taraf nereye koyacagina
        kendi karar verir (HTTP yaniti, depolama, e-posta eki).
    """
    turkce_fontlari_kur()

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Image,
        KeepTogether,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    def bolum(baslik_metni: str, *icerikler):
        """Baslik + icerigi AYRILMAZ bir blok olarak ekler.

        `KeepTogether` olmadan ReportLab bolum basligini bir sayfanin
        dibinde birakip icerigi sonrakine atabiliyor. Canli testte birebir
        yasandi: "Grafik" basligi 1. sayfanin sonunda oksuz kaldi, grafik
        2. sayfaya dustu - kullanicinin "grafik hatasi olmasin" sartini
        ihlal eden bir gorunum.
        """
        akis.append(KeepTogether([Paragraph(baslik_metni, stiller["bolum"]), *icerikler]))

    stiller = _stiller()
    tampon = BytesIO()
    kenar = 18 * mm
    doc = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=kenar,
        rightMargin=kenar,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=sonuc.baslik or "Belge Analiz Raporu",
        author="Polifin Yatırım Asistanı",
    )
    icerik_genisligi = A4[0] - 2 * kenar

    akis: list = []

    # --- Baslik ---
    akis.append(Paragraph(_kacisli(sonuc.baslik or "Belge Analiz Raporu"), stiller["baslik"]))
    akis.append(
        Paragraph(
            f"{_kacisli(belge.dosya_adi)} · {datetime.now():%d.%m.%Y %H:%M}",
            stiller["altbaslik"],
        )
    )
    akis.append(HRFlowable(width="100%", thickness=0.7, color="#cbd5e1", spaceAfter=4))

    # Hicbir icerik uretilemediyse bos bir PDF gondermek yerine durumu ACIKCA
    # yaz - kullanici "bos dosya" ile karsilasmasin. Bolumlerden ONCE eklenir;
    # eskiden sabit indekse (`insert(3, ...)`) yaziliyordu ve bolumler
    # `KeepTogether` bloklarina alininca o indeks anlamini yitirdi.
    if sonuc.bos_mu():
        akis.append(
            Paragraph(
                "Belge okundu ancak özetlenebilecek finansal içerik bulunamadı.",
                stiller["govde"],
            )
        )

    # --- Once SADE ACIKLAMA: kullanici raporu actiginda ilk bunu gormeli ---
    if sonuc.sade_aciklama:
        bolum(
            "Kısaca ne anlama geliyor?",
            Paragraph(_kacisli(sonuc.sade_aciklama), stiller["govde"]),
        )

    if sonuc.ozet:
        bolum("Özet", Paragraph(_kacisli(sonuc.ozet), stiller["govde"]))

    if sonuc.bulgular:
        bolum("Öne Çıkan Bulgular", *_madde_listesi(sonuc.bulgular, stiller["madde"]))

    if sonuc.gostergeler:
        bolum(
            "Sayısal Göstergeler",
            Spacer(1, 3),
            _gosterge_tablosu(sonuc, icerik_genisligi),
        )

    if grafik_yolu:
        # Oran KORUNUR: `charts.FIGUR_BOYUTU` 6.4x3.2 (2:1). Sabit yukseklik
        # vermek grafigi ezip etiketleri okunmaz yapardi.
        genislik = icerik_genisligi
        bolum("Grafik", Image(grafik_yolu, width=genislik, height=genislik / 2))

    if sonuc.riskler:
        bolum(
            "Dikkat Edilmesi Gerekenler",
            *_madde_listesi(sonuc.riskler, stiller["madde"]),
        )

    # --- Dipnot: kaynak + uyarilar + yasal not ---
    akis.append(Spacer(1, 10))
    akis.append(HRFlowable(width="100%", thickness=0.5, color="#e2e8f0", spaceAfter=4))

    dipnotlar = [f"Kaynak belge: {_kacisli(belge.dosya_adi)}"]
    if belge.sayfa_sayisi:
        birim = "sayfa" if belge.tur == "pdf" else "tablo"
        dipnotlar.append(f"İşlenen {birim} sayısı: {belge.sayfa_sayisi}")
    # Ayristirma uyarilari SAKLANMAZ: kullanici raporun neden eksik
    # olabilecegini bilmelidir.
    dipnotlar.extend(_kacisli(u) for u in belge.uyarilar)
    dipnotlar.append(
        "Bu rapor yüklediğiniz belgeden otomatik olarak üretilmiştir ve "
        "yatırım tavsiyesi değildir."
    )
    for satir in dipnotlar:
        akis.append(Paragraph(satir, stiller["dipnot"]))

    try:
        doc.build(akis)
    except Exception:
        logger.exception("PDF derlenemedi")
        raise

    return tampon.getvalue()
