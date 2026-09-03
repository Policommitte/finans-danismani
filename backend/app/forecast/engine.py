"""Ham model ciktisini URUNE cevirir: shrinkage + TL drift + band kaydirma.

BU DOSYADAKI HER SAYI OLCULEREK SECILDI
---------------------------------------
42 varlik / 2 yillik gercek veri, 378 kesitlik sizintisiz walk-forward
(21 is gunu ileri). Karsilastirma tablosu:

    yapilandirma              MAPE    yon    %80 kapsam
    naive (taban)             7,07      -         77,2
    TimesFM ham               7,49   54,8         77,2   (+%6,0 kotu)
    shrink 0.30               7,06   54,8         77,2   (-%0,1)
    shrink + TL drift         6,93   59,5         79,1   (-%1,9) ← URETIM

Uc olcu de AYNI ANDA iyilesti: hata dustu, yon isabeti 59,5'e cikti
(yazi-turadan belirgin yukarida), band kapsami hedefe (%80) yaklasti.

NEDEN SHRINKAGE
---------------
Modele TAM guvenmek (agirlik 1.0) hatayi BUYUTUYOR: dusuk sinyalli
finansal seride modelin urettigi sapmanin cogu gurultudur. Agirligi 0.30'a
cekmek, modelin sinyalini korurken gurultusunu bastirir - klasik
"shrinkage toward the mean" fikri.

NEDEN TL BAZLI VARLIKLARDA DRIFT
--------------------------------
TL'nin kalici deger kaybi GERCEK bir trend. Olculdu: dovizde referansi
son fiyattan drift'e cevirmek hatayi %1,54'ten %0,79'a indirdi (neredeyse
yariya). Hisse/kriptoda boyle bir trend YOK - oralarda drift kullanmak
hatayi buyuturdu, bu yuzden kategori bazli ayrim var.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np

from app.config import settings
from app.forecast import model as tahmin_modeli
from app.forecast.types import Tahmin, TahminNoktasi

logger = logging.getLogger(__name__)

#: Modelin anlamli calismasi icin gereken asgari gecmis. Daha kisa seride
#: hem TimesFM baglami zayif kalir hem drift tahmini guvenilmez olur.
ASGARI_GECMIS = 60

UYARI_METNI = (
    "Bu tahmin geçmiş fiyat hareketinden üretilmiştir ve yatırım tavsiyesi "
    "değildir. Fiyatın yönü güvenilir şekilde tahmin edilemez; asıl anlamlı "
    "bilgi, gölgeli alanla gösterilen olası aralıktır."
)


def drift_kategorileri() -> set[str]:
    """Referansi drift olacak kategoriler (ayardan, virgulle ayrilmis)."""
    ham = settings.forecast_drift_categories or ""
    return {parca.strip() for parca in ham.split(",") if parca.strip()}


def _is_gunleri(baslangic: date, adet: int) -> list[date]:
    """Hafta sonlarini ATLAYARAK `adet` kadar ileri gun uretir.

    Resmi tatiller DAHIL EDILMEZ: borsa takvimi varliga gore degisir
    (BIST, NYSE, kripto 7/24) ve yanlis takvim, dogru tahmini yanlis gune
    yazmaktan daha kotu bir hata degildir - grafikte bir-iki gunluk kayma
    kullanicinin okumasini bozmaz. Kripto icin bile hafta sonu atlanir:
    gunluk mum verisi zaten is gunu bazli toplaniyor.
    """
    gunler: list[date] = []
    imlec = baslangic
    while len(gunler) < adet:
        imlec += timedelta(days=1)
        if imlec.weekday() < 5:  # 5=Cumartesi, 6=Pazar
            gunler.append(imlec)
    return gunler


def tahmin_uret(
    sembol: str,
    kapanislar: list[float],
    son_tarih: date,
    kategori: str = "",
) -> Tahmin | None:
    """Bir varlik icin uretim tahmini. Uretilemezse `None`.

    Args:
        kapanislar: Gunluk kapanis fiyatlari, ESKIDEN YENIYE sirali.
        son_tarih: Son kapanisin tarihi - tahmin bunun ERTESINDEN baslar.
        kategori: Varlik kategorisi (TL drift karari icin).
    """
    if not tahmin_modeli.yuklu_mu():
        return None

    seri = np.asarray([float(k) for k in kapanislar if k and k > 0], dtype=np.float64)
    if len(seri) < ASGARI_GECMIS:
        logger.info("tahmin icin yetersiz gecmis", extra={"sembol": sembol, "gun": len(seri)})
        return None

    ufuk = settings.forecast_horizon_days
    try:
        medyan, q10, q90 = tahmin_modeli.ham_tahmin(seri, ufuk)
    except Exception:  # noqa: BLE001 - tahmin hatasi grafigi DUSURMEMELI
        logger.exception("model tahmini basarisiz", extra={"sembol": sembol})
        return None

    son = float(seri[-1])
    agirlik = float(settings.forecast_model_weight)

    # --- Referans seri: TL bazli varliklarda drift, digerlerinde duz cizgi ---
    if kategori in drift_kategorileri():
        gunluk_log = float(np.mean(np.diff(np.log(seri))))
        referans = np.array([son * np.exp(gunluk_log * (i + 1)) for i in range(ufuk)])
    else:
        referans = np.full(ufuk, son)

    nokta = agirlik * medyan + (1.0 - agirlik) * referans

    # --- BAND KAYDIRMA ---
    # Nokta tahmini referansa cekildigi icin modelin HAM bandinin ortasinda
    # kalmaz; kullanici "cizgi bandin ortasinda degil" diye gorurdu.
    # Bandi ayni miktarda kaydirip GENISLIGINI koruyoruz: kalibre edilmis
    # olan genisliktir, merkez degil. Olculdu - kapsam bozulmadi
    # (%77,2 -> %77,0), uretim yapilandirmasinda %79,1'e CIKTI.
    kayma = nokta - medyan
    alt = q10 + kayma
    ust = q90 + kayma

    gunler = _is_gunleri(son_tarih, ufuk)
    noktalar = [
        TahminNoktasi(
            tarih=gun.isoformat(),
            deger=round(float(nokta[i]), 6),
            # Bant siniri negatife dusemez: fiyat negatif olamaz ve cok
            # oynak varliklarda (kripto) alt sinir teorik olarak 0'in
            # altina inebilir.
            alt=round(max(float(alt[i]), 0.0), 6),
            ust=round(float(ust[i]), 6),
        )
        for i, gun in enumerate(gunler)
    ]

    return Tahmin(
        sembol=sembol,
        son_fiyat=round(son, 6),
        son_tarih=son_tarih.isoformat(),
        noktalar=noktalar,
        model=f"{settings.forecast_model}+shrink{agirlik:.2f}",
        uyari=UYARI_METNI,
    )


def portfoy_tahmini_birlestir(
    tahminler: list[tuple[Tahmin, float]],
    nakit: float,
    son_tarih: date,
) -> Tahmin | None:
    """Varlik tahminlerini TEK portfoy tahminine toplar.

    Args:
        tahminler: (tahmin, adet) ciftleri - adet varligin portfoydeki miktari.
        nakit: Likit bakiye; tahmin edilmez, sabit eklenir.

    ⚠️ KORELASYON UYARISI - BANT NEDEN BOYLE HESAPLANIYOR
    ------------------------------------------------------
    NOKTA tahminleri toplanabilir (beklenen deger DOGRUSALDIR: toplamin
    beklentisi, beklentilerin toplamidir).

    BANTLAR TOPLANAMAZ. Alt sinirlari toplayip ust sinirlari toplamak,
    "TUM varliklar AYNI ANDA en kotu senaryoyu yasar" demektir - varliklar
    mukemmel korelasyonlu olsaydi dogru olurdu, degiller. Bu, riski CIDDI
    SEKILDE ABARTIR.

    Dogru cozum kovaryans matrisidir. Onu kurana kadar, varliklarin
    BAGIMSIZ oldugu varsayimiyla karelerin toplaminin karekokunu
    kullaniyoruz (sqrt(Σσ²)). Bu da tam dogru degil - gercek korelasyon
    sifir degil, pozitif - yani bu bant GERCEGINDEN BIRAZ DAR olabilir.
    Iki ucun ortasinda, savunulabilir bir yaklasim; kovaryans matrisi
    eklenene kadar bilincli bir ara cozumdur.
    """
    if not tahminler:
        return None

    ufuk = min(len(t.noktalar) for t, _ in tahminler)
    if ufuk == 0:
        return None

    toplam_son = sum(t.son_fiyat * adet for t, adet in tahminler) + nakit
    noktalar: list[TahminNoktasi] = []

    for i in range(ufuk):
        deger = sum(t.noktalar[i].deger * adet for t, adet in tahminler) + nakit

        # Her varligin yari-bant genisligi, adetle olceklenmis
        yari_bantlar = [
            (t.noktalar[i].ust - t.noktalar[i].alt) / 2.0 * adet for t, adet in tahminler
        ]
        birlesik_yari = float(np.sqrt(np.sum(np.square(yari_bantlar))))

        noktalar.append(
            TahminNoktasi(
                tarih=tahminler[0][0].noktalar[i].tarih,
                deger=round(deger, 2),
                alt=round(max(deger - birlesik_yari, 0.0), 2),
                ust=round(deger + birlesik_yari, 2),
            )
        )

    return Tahmin(
        sembol="PORTFOY",
        son_fiyat=round(toplam_son, 2),
        son_tarih=son_tarih.isoformat(),
        noktalar=noktalar,
        model=tahminler[0][0].model,
        uyari=UYARI_METNI,
    )
