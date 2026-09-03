"""Belge/gorsel analizi ve PDF rapor uretimi.

Moduller:
    fonts    Turkce karakter garantisi (ReportLab + matplotlib ORTAK kaynak)
    types    Boru hattinin ortak sozlesmesi (ayristirma -> analiz -> rapor)
    parser   PDF (pdfplumber) ve Excel (openpyxl) ayristirma
    vision   Gorseli metne cevirme (AYRI gorme modeli ile)
    charts   Sayisal seriyi PNG grafige cevirme (matplotlib)
    report   Analiz sonucunu Turkce PDF'e derleme (ReportLab)

Boru hattini birlestiren ajan: `app.agents.document_analysis`.
"""
