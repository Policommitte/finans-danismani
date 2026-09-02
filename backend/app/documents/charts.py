"""Analiz sonucundaki sayisal seriyi PNG grafige cevirir (matplotlib).

TASARIM KARARI - GRAFIK ASLA ISI DUSURMEZ
------------------------------------------
Grafik raporun SUSUDUR, ozu degil. Bozuk bir seri ("degerler" listesi
etiketlerden kisa, tur "pasta" gibi taninmayan bir deger, hepsi sifir) cizim
sirasinda istisna firlatabilir. Bunun kullanicinin raporu HIC alamamasina yol
acmasi kabul edilemez - bu yuzden her cizim savunmali sarilir ve basarisizlik
`None` doner; rapor grafiksiz derlenir.

Kullanicinin sartlarindan biri "grafik hatalari olmasin" idi; bu modulde bu
sart iki sekilde karsilaniyor:
  1. Cizim oncesi `Grafik.gecerli_mi()` ile veri dogrulanir.
  2. Turkce etiketler icin font `fonts.matplotlib_turkce_ayarla()` ile
     garantiye alinir - aksi halde eksen yazilari tofu kutusu cikardi.
"""

from __future__ import annotations

import logging
import os

from app.documents.fonts import matplotlib_turkce_ayarla
from app.documents.types import Grafik

logger = logging.getLogger(__name__)

#: Rapor genisligine oturan sabit figur boyutu (inc). PDF'te 150 mm
#: genisliginde gosterilir; 6.4x3.2 oran bozulmadan sigar.
FIGUR_BOYUTU = (6.4, 3.2)
FIGUR_DPI = 150

#: Marka rengi - frontend'deki `--color-primary` ile uyumlu ton.
ANA_RENK = "#2563eb"
PASTA_RENKLERI = ["#2563eb", "#0ea5e9", "#14b8a6", "#f59e0b", "#ef4444", "#8b5cf6"]

#: Pasta grafikte azami dilim. Daha fazlasi okunamaz hale gelir.
AZAMI_PASTA_DILIMI = 6


def _etiketi_kisalt(etiket: str, azami: int = 18) -> str:
    """Uzun etiketleri eksende ust uste binmeyecek sekilde kirpar."""
    etiket = " ".join(str(etiket).split())
    return etiket if len(etiket) <= azami else etiket[: azami - 1] + "…"


def grafik_ciz(grafik: Grafik, hedef_dizin: str, dosya_adi: str = "grafik.png") -> str | None:
    """Grafigi PNG olarak yazar ve dosya yolunu doner; cizilemezse `None`.

    Args:
        grafik: Modelin onerdigi seri.
        hedef_dizin: PNG'nin yazilacagi (var olan) dizin.
        dosya_adi: Cikti dosyasinin adi.
    """
    if not grafik or not grafik.gecerli_mi():
        logger.info("grafik verisi gecersiz, grafiksiz devam ediliyor")
        return None

    matplotlib_turkce_ayarla()
    import matplotlib.pyplot as plt

    yol = os.path.join(hedef_dizin, dosya_adi)
    fig = None
    try:
        etiketler = [_etiketi_kisalt(e) for e in grafik.etiketler]
        degerler = [float(d) for d in grafik.degerler]

        fig, ax = plt.subplots(figsize=FIGUR_BOYUTU)

        if grafik.tur == "pie":
            # Negatif deger pasta grafikte ANLAMSIZDIR (matplotlib sessizce
            # bozuk dilim cizer). Boyle bir seri geldiginde cubuga dusulur -
            # veri korunur, gorsel yaniltici olmaz.
            if any(d < 0 for d in degerler) or sum(degerler) <= 0:
                logger.info("pasta grafik icin uygun olmayan seri, cubuga dusuluyor")
                ax.bar(etiketler, degerler, color=ANA_RENK)
            else:
                ax.pie(
                    degerler[:AZAMI_PASTA_DILIMI],
                    labels=etiketler[:AZAMI_PASTA_DILIMI],
                    autopct="%1.1f%%",
                    colors=PASTA_RENKLERI,
                    startangle=90,
                )
                ax.axis("equal")
        elif grafik.tur == "line":
            ax.plot(etiketler, degerler, marker="o", color=ANA_RENK, linewidth=2)
            ax.grid(True, alpha=0.3)
        else:  # "bar"
            ax.bar(etiketler, degerler, color=ANA_RENK)
            ax.grid(True, axis="y", alpha=0.3)

        if grafik.tur != "pie":
            if grafik.eksen_adi:
                ax.set_ylabel(grafik.eksen_adi)
            # Uzun etiketler yatayda sigmazsa egilir; ust uste binme
            # "grafik hatasi" olarak gorunurdu.
            if max((len(e) for e in etiketler), default=0) > 8:
                plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
            for kenar in ("top", "right"):
                ax.spines[kenar].set_visible(False)

        if grafik.baslik:
            ax.set_title(grafik.baslik, fontsize=12)

        fig.tight_layout()
        fig.savefig(yol, dpi=FIGUR_DPI, bbox_inches="tight")
        return yol
    except Exception:  # noqa: BLE001 - grafik hatasi RAPORU DUSURMEZ
        logger.exception("grafik cizilemedi, rapor grafiksiz uretilecek")
        return None
    finally:
        if fig is not None:
            # Kapatilmazsa figurler surecte birikir: uzun calisan bir sunucuda
            # bellek sizintisi ve "More than 20 figures" uyarilari uretir.
            plt.close(fig)
