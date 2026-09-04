"""`app.forecast.engine` - ham model ciktisini URUNE ceviren katman.

⚠️ TimesFM BURADA CALISTIRILMAZ. `torch` + `timesfm` ~1-2 GB bellek ve
~200 MB indirme demektir; suite'in ona bagli olmasi kabul edilemez. Modul
zaten bu yalitim icin ayrilmis (`app/forecast/model.py`), testler de o
sinirdan sahte cikti enjekte eder.

Boylece test edilen sey URUN KARARLARIDIR: shrinkage agirligi, TL drift'i,
band kaydirma ve hafta sonu atlama - hepsi olculerek secilmis sayilar.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from app.forecast import engine
from app.forecast import model as tahmin_modeli
from app.forecast.engine import ASGARI_GECMIS, UYARI_METNI, portfoy_tahmini_birlestir, tahmin_uret
from app.forecast.types import Tahmin, TahminNoktasi

SON_TARIH = date(2026, 9, 2)  # Carsamba


@pytest.fixture
def model_acik(monkeypatch, ayar):
    """Modeli "yuklu" gosterir ve HAM ciktisini test kontrol eder.

    Donen fabrika `(medyan, q10, q90)` uretir; boylece her test kendi
    senaryosunu kurar.
    """
    ayar(forecast_horizon_days=5, forecast_model_weight=0.30, forecast_model="sahte-model")
    monkeypatch.setattr(tahmin_modeli, "yuklu_mu", lambda: True)

    def _kur(medyan, q10=None, q90=None):
        m = np.asarray(medyan, dtype=float)
        a = np.asarray(q10 if q10 is not None else m * 0.9, dtype=float)
        u = np.asarray(q90 if q90 is not None else m * 1.1, dtype=float)
        monkeypatch.setattr(tahmin_modeli, "ham_tahmin", lambda seri, ufuk: (m, a, u))

    return _kur


def duz_seri(deger: float = 100.0, gun: int = ASGARI_GECMIS + 10) -> list[float]:
    return [deger] * gun


# --- Kapali / yetersiz veri ----------------------------------------------


def test_model_yuklu_degilse_tahmin_uretilmez(monkeypatch):
    """Ozellik SESSIZCE kapanir - bu bir HATA DEGILDIR."""
    monkeypatch.setattr(tahmin_modeli, "yuklu_mu", lambda: False)
    assert tahmin_uret("THYAO", duz_seri(), SON_TARIH) is None


def test_asgari_gecmisin_altinda_tahmin_uretilmez(model_acik):
    model_acik([100] * 5)
    assert tahmin_uret("THYAO", [100.0] * (ASGARI_GECMIS - 1), SON_TARIH) is None


def test_gecersiz_fiyatlar_serinin_disinda_birakilir(model_acik):
    """Sifir/negatif/None kapanislar elenir; kalan sayi asgarinin altina
    duserse tahmin uretilmez."""
    model_acik([100] * 5)
    kirli = [0, None, -5] + [100.0] * (ASGARI_GECMIS - 1)
    assert tahmin_uret("THYAO", kirli, SON_TARIH) is None


def test_model_hatasi_grafigi_dusurmez(model_acik, monkeypatch):
    """Tahmin hatasi TUM grafigi degil yalnizca tahmin katmanini kapatmali."""
    model_acik([100] * 5)
    monkeypatch.setattr(
        tahmin_modeli, "ham_tahmin", lambda *a: (_ for _ in ()).throw(RuntimeError("model coktu"))
    )
    assert tahmin_uret("THYAO", duz_seri(), SON_TARIH) is None


# --- Shrinkage ------------------------------------------------------------


def test_shrinkage_modeli_referansa_ceker(model_acik, ayar):
    """Agirlik 0.30: modele TAM guvenmek hatayi BUYUTUYOR (olculdu). Nokta
    tahmini = 0.30*model + 0.70*son_fiyat."""
    model_acik([200.0] * 5)
    t = tahmin_uret("THYAO", duz_seri(100.0), SON_TARIH)
    assert t.noktalar[0].deger == pytest.approx(0.30 * 200 + 0.70 * 100)


def test_agirlik_bir_olunca_ham_model_kullanilir(model_acik, ayar):
    model_acik([200.0] * 5)
    ayar(forecast_model_weight=1.0)
    t = tahmin_uret("THYAO", duz_seri(100.0), SON_TARIH)
    assert t.noktalar[0].deger == pytest.approx(200.0)


def test_agirlik_sifir_olunca_naive_referans_kalir(model_acik, ayar):
    model_acik([200.0] * 5)
    ayar(forecast_model_weight=0.0)
    t = tahmin_uret("THYAO", duz_seri(100.0), SON_TARIH)
    assert all(n.deger == pytest.approx(100.0) for n in t.noktalar)


# --- TL drift -------------------------------------------------------------


def test_drift_kategorisinde_referans_trendi_surdurur(model_acik, ayar):
    """TL'nin kalici deger kaybi GERCEK bir trend: dovizde referansi son
    fiyattan drift'e cevirmek hatayi %1,54'ten %0,79'a indirdi."""
    ayar(forecast_drift_categories="Döviz (Fiat)", forecast_model_weight=0.0)
    model_acik([100.0] * 5)
    artan = [100.0 * (1.001**i) for i in range(ASGARI_GECMIS + 10)]

    t = tahmin_uret("USD/TRY", artan, SON_TARIH, kategori="Döviz (Fiat)")
    degerler = [n.deger for n in t.noktalar]
    assert degerler == sorted(degerler)  # trend surduruluyor
    assert degerler[0] > artan[-1]


def test_drift_disi_kategoride_referans_duz_kalir(model_acik, ayar):
    """Hisse/kriptoda boyle bir trend YOK - drift kullanmak hatayi
    buyuturdu."""
    ayar(forecast_drift_categories="Döviz (Fiat)", forecast_model_weight=0.0)
    model_acik([100.0] * 5)
    artan = [100.0 * (1.001**i) for i in range(ASGARI_GECMIS + 10)]

    t = tahmin_uret("THYAO", artan, SON_TARIH, kategori="BIST Hisse Senedi")
    assert {n.deger for n in t.noktalar} == {round(artan[-1], 6)}


def test_drift_kategorileri_ayardan_okunur(ayar):
    ayar(forecast_drift_categories="A, B ,, C ")
    assert engine.drift_kategorileri() == {"A", "B", "C"}


def test_bos_drift_ayari_bos_kume_verir(ayar):
    ayar(forecast_drift_categories="")
    assert engine.drift_kategorileri() == set()


# --- Band kaydirma --------------------------------------------------------


def test_band_kaydirilir_genisligi_korunur(model_acik):
    """Kalibre edilmis olan GENISLIKTIR, merkez degil. Nokta referansa
    cekilince band ayni miktarda kaydirilir - kullanici "cizgi bandin
    ortasinda degil" diye gormesin."""
    model_acik(medyan=[200.0] * 5, q10=[180.0] * 5, q90=[220.0] * 5)
    t = tahmin_uret("THYAO", duz_seri(100.0), SON_TARIH)

    n = t.noktalar[0]
    assert n.ust - n.alt == pytest.approx(40.0)  # ham genislik korundu
    assert (n.alt + n.ust) / 2 == pytest.approx(n.deger)  # nokta ortada


def test_alt_sinir_negatife_dusmez(model_acik):
    """Cok oynak varliklarda (kripto) alt sinir teorik olarak 0'in altina
    inebilir; fiyat negatif olamaz."""
    model_acik(medyan=[10.0] * 5, q10=[-500.0] * 5, q90=[50.0] * 5)
    t = tahmin_uret("BTC", duz_seri(10.0), SON_TARIH)
    assert all(n.alt >= 0.0 for n in t.noktalar)


# --- Takvim ---------------------------------------------------------------


def test_hafta_sonlari_atlanir(model_acik, ayar):
    """Carsamba (2 Eylul) + 5 is gunu -> Per, Cum, Pzt, Sal, Car."""
    ayar(forecast_horizon_days=5)
    model_acik([100.0] * 5)
    t = tahmin_uret("THYAO", duz_seri(), SON_TARIH)
    assert [n.tarih for n in t.noktalar] == [
        "2026-09-03",
        "2026-09-04",
        "2026-09-07",
        "2026-09-08",
        "2026-09-09",
    ]


def test_tahmin_son_tarihin_ERTESINDEN_baslar(model_acik):
    model_acik([100.0] * 5)
    t = tahmin_uret("THYAO", duz_seri(), SON_TARIH)
    assert t.son_tarih == SON_TARIH.isoformat()
    assert t.noktalar[0].tarih > t.son_tarih


def test_nokta_sayisi_ufka_esittir(model_acik, ayar):
    ayar(forecast_horizon_days=3)
    model_acik([100.0] * 3)
    assert len(tahmin_uret("THYAO", duz_seri(), SON_TARIH).noktalar) == 3


# --- Zarf -----------------------------------------------------------------


def test_uyari_metni_her_tahminde_tasinir(model_acik):
    """URUN KARARI: olculen dogruluk naive'e cok yakin, kullaniciya yanlis
    guven verilmemeli."""
    model_acik([100.0] * 5)
    assert tahmin_uret("THYAO", duz_seri(), SON_TARIH).uyari == UYARI_METNI


def test_model_etiketi_agirligi_tasir(model_acik, ayar):
    """Izlenebilirlik: hangi yapilandirmayla uretildigi kayitli kalir."""
    ayar(forecast_model="timesfm-x", forecast_model_weight=0.30)
    model_acik([100.0] * 5)
    assert tahmin_uret("THYAO", duz_seri(), SON_TARIH).model == "timesfm-x+shrink0.30"


def test_bos_mu_nokta_yoksa_dogru_doner():
    assert Tahmin(sembol="X", son_fiyat=1, son_tarih="2026-01-01").bos_mu() is True


# --- Portfoy birlestirme --------------------------------------------------


def nokta(deger: float, yari_bant: float, tarih: str = "2026-09-03") -> TahminNoktasi:
    return TahminNoktasi(tarih=tarih, deger=deger, alt=deger - yari_bant, ust=deger + yari_bant)


def tahmin(sembol: str, son: float, noktalar: list[TahminNoktasi]) -> Tahmin:
    return Tahmin(sembol=sembol, son_fiyat=son, son_tarih="2026-09-02", noktalar=noktalar)


def test_bos_liste_portfoy_tahmini_uretmez():
    assert portfoy_tahmini_birlestir([], nakit=0, son_tarih=SON_TARIH) is None


def test_noktasiz_tahmin_portfoy_tahminini_iptal_eder():
    assert portfoy_tahmini_birlestir([(tahmin("A", 10, []), 1.0)], 0, SON_TARIH) is None


def test_nokta_tahminleri_adetle_carpilip_toplanir():
    """Beklenen deger DOGRUSALDIR: toplamin beklentisi = beklentilerin
    toplami."""
    a = tahmin("A", 100, [nokta(110, 10)])
    b = tahmin("B", 50, [nokta(60, 5)])
    p = portfoy_tahmini_birlestir([(a, 2.0), (b, 3.0)], nakit=1_000, son_tarih=SON_TARIH)
    assert p.noktalar[0].deger == pytest.approx(110 * 2 + 60 * 3 + 1_000)


def test_nakit_tahmin_edilmez_sabit_eklenir():
    """TL'nin kendisi referans birimdir."""
    a = tahmin("A", 100, [nokta(100, 0)])
    p = portfoy_tahmini_birlestir([(a, 1.0)], nakit=500, son_tarih=SON_TARIH)
    assert p.son_fiyat == pytest.approx(600)
    assert p.noktalar[0].deger == pytest.approx(600)


def test_bantlar_TOPLANMAZ_kareler_toplaminin_karekoku_alinir():
    """⚠️ KORELASYON. Alt sinirlari toplayip ust sinirlari toplamak "TUM
    varliklar AYNI ANDA en kotu senaryoyu yasar" demektir - riski CIDDI
    SEKILDE abartir. Kovaryans matrisi kurulana kadar bagimsizlik
    varsayimiyla sqrt(Σσ²) kullaniliyor."""
    a = tahmin("A", 100, [nokta(100, 30)])
    b = tahmin("B", 100, [nokta(100, 40)])
    p = portfoy_tahmini_birlestir([(a, 1.0), (b, 1.0)], nakit=0, son_tarih=SON_TARIH)

    yari = (p.noktalar[0].ust - p.noktalar[0].alt) / 2
    assert yari == pytest.approx(50.0)  # sqrt(30²+40²), 70 DEGIL
    assert yari < 30 + 40


def test_yari_bantlar_adetle_olceklenir():
    a = tahmin("A", 100, [nokta(100, 10)])
    p = portfoy_tahmini_birlestir([(a, 3.0)], nakit=0, son_tarih=SON_TARIH)
    assert (p.noktalar[0].ust - p.noktalar[0].alt) / 2 == pytest.approx(30.0)


def test_portfoy_alt_siniri_negatife_dusmez():
    a = tahmin("A", 1, [nokta(1, 500)])
    p = portfoy_tahmini_birlestir([(a, 1.0)], nakit=0, son_tarih=SON_TARIH)
    assert p.noktalar[0].alt == 0.0


def test_ufuk_en_kisa_tahmine_gore_kirpilir():
    """Bir varligin tahmini kisaysa portfoy tahmini onun boyunda kalir -
    eksik varlikla toplamak portfoyu KUCUK gosterirdi."""
    uzun = tahmin("A", 100, [nokta(100, 5, "2026-09-03"), nokta(101, 5, "2026-09-04")])
    kisa = tahmin("B", 100, [nokta(100, 5, "2026-09-03")])
    p = portfoy_tahmini_birlestir([(uzun, 1.0), (kisa, 1.0)], 0, SON_TARIH)
    assert len(p.noktalar) == 1


def test_portfoy_tahmini_sembolu_ve_uyarisi_sabittir():
    a = tahmin("A", 100, [nokta(100, 5)])
    p = portfoy_tahmini_birlestir([(a, 1.0)], 0, SON_TARIH)
    assert p.sembol == "PORTFOY"
    assert p.uyari == UYARI_METNI
