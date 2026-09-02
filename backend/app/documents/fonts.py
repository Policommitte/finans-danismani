"""Turkce karakter garantisi: ReportLab ve matplotlib icin ORTAK font kaynagi.

NEDEN AYRI BIR MODUL
--------------------
Rapor iki ayri motordan gecer - metin/tablo ReportLab'de, grafik
matplotlib'de cizilir - ve IKISI DE kendi font cozumlemesini yapar. Ayri
birakilsalardi tek bir tarafin fontu eksik kalir ve kullanici PDF'i actiginda
"Sirket Buyume Orani" basligini duzgun gorurken grafik ekseninde "Deiim"
gibi glifi olmayan bir metin gorurdu (tofu kutulari).

NEDEN DejaVu
------------
matplotlib DejaVu ailesini KENDI ICINDE tasir. Yani:
  * Repoya ayrica font dosyasi koymaya gerek yok.
  * Isletim sistemine bagimlilik yok - Windows'ta "Arial var mi", Linux
    konteynerinde "hicbir font yok" sorusu ortadan kalkar.
  * DejaVu tam Latin-Extended-A kapsar; Turkce'nin zor harfleri (i, I, g,
    s, ç, ö, ü ve buyuk karsiliklari) eksiksiz.

ReportLab'in gomulu Helvetica'si KULLANILMAZ: WinAnsi/Latin-1 kodlamasi
`g`, `s`, `I`, `i` harflerini TASIMAZ; bu harfler sessizce kaybolur ya da
yanlis glife duser.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

#: ReportLab'e kaydedilen mantiksal font adlari. Rapor kodu bu sabitleri
#: kullanir; dosya adlarini bilmek zorunda kalmaz.
NORMAL = "PolifinSans"
KALIN = "PolifinSans-Bold"

#: matplotlib'in `font.family` degeri icin DejaVu'nun AILE adi (dosya adi
#: degil - matplotlib aileyle calisir).
MPL_AILE = "DejaVu Sans"


def _font_dizini() -> str:
    """matplotlib'in birlikte geldigi TTF dizini."""
    import matplotlib

    return os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")


@lru_cache(maxsize=1)
def turkce_fontlari_kur() -> bool:
    """DejaVu'yu hem ReportLab'e hem matplotlib'e tanitir.

    `lru_cache` ile SURECTE BIR KEZ calisir: ReportLab ayni font adini ikinci
    kez kaydetmeye calisirsa gereksiz is yapilir, matplotlib'in font cache'i
    de her cagride yeniden taranmamalidir.

    Returns:
        Kurulum basarili mi. `False` donerse cagiran taraf PDF uretmeyi
        SURDURUR ama Turkce glifler bozulabilir - bu yuzden `False` durumu
        loglanir. Rapor uretimini komple dusurmek daha kotu olurdu: kullanici
        hicbir sey alamamaktansa fontu bozuk bir rapor almalidir.
    """
    try:
        from matplotlib import font_manager
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        dizin = _font_dizini()
        duz = os.path.join(dizin, "DejaVuSans.ttf")
        kalin = os.path.join(dizin, "DejaVuSans-Bold.ttf")

        for yol in (duz, kalin):
            if not os.path.exists(yol):
                logger.warning("Turkce font dosyasi bulunamadi", extra={"yol": yol})
                return False

        pdfmetrics.registerFont(TTFont(NORMAL, duz))
        pdfmetrics.registerFont(TTFont(KALIN, kalin))

        # Kalin/normal esleme: ReportLab `<b>` etiketini ancak bu kayitla
        # dogru dosyaya yonlendirir. Yapilmazsa kalin metin sentetik olarak
        # kalinlastirilir ve bazi Turkce glifler deforme olur.
        pdfmetrics.registerFontFamily(
            NORMAL, normal=NORMAL, bold=KALIN, italic=NORMAL, boldItalic=KALIN
        )

        font_manager.fontManager.addfont(duz)
        font_manager.fontManager.addfont(kalin)
        return True
    except Exception:  # noqa: BLE001 - font kurulumu rapor uretimini DUSURMEMELI
        logger.exception("Turkce font kurulumu basarisiz; PDF glifleri bozulabilir")
        return False


def matplotlib_turkce_ayarla() -> None:
    """Grafik eksenlerinde/basliklarinda Turkce icin matplotlib'i hazirlar.

    `Agg` arka ucu SECILIR: sunucuda ekran yoktur, varsayilan interaktif arka
    uc secilirse `plt.subplots()` cagrisi bas eder ya da uyari kusar.
    """
    import matplotlib

    matplotlib.use("Agg", force=True)
    turkce_fontlari_kur()

    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = MPL_AILE
    # Eksi isareti: matplotlib varsayilan olarak U+2212 (MINUS SIGN) kullanir,
    # DejaVu'da vardir ama bazi PDF okuyucularda kopyalanamaz cikar. ASCII
    # tire negatif getirileri (-%12,4) sorunsuz gosterir.
    plt.rcParams["axes.unicode_minus"] = False
