"""Hesaplama mantigi testleri - AG ve VERITABANI GEREKTIRMEZ.

Yahoo cagrisi ve DB yazimi burada test EDILMEZ; testler saf fonksiyonlari
sabitler. Boylece internet olmadan da mantigin dogrulugu dogrulanabilir.

Kritik davranislar:
  * Haftalik/yillik degisim TAKVIM gunune gore hesaplanir (borsa hafta sonu
    kapali oldugu icin "7 satir geriye git" yanlis sonuc verir).
  * Seri yeterince geriye gitmiyorsa `None` doner - deger UYDURULMAZ.
  * Gram altin turetmesinde kur bosluklari bir onceki gecerli kurla doldurulur.
"""

import pandas as pd
import pytest

from symbols import (
    TROY_ONS_GRAM,
    VARSAYILAN_KATEGORILER,
    VarlikEslesme,
    eslesmeleri_getir,
    ons_usd_to_gram_try,
)
from yahoo import gram_try_serisi, metrikleri_hesapla


def _seri(fiyatlar: list[float], baslangic: str = "2026-01-01", gun_araligi: int = 1) -> pd.Series:
    """Gunluk UTC indeksli kapanis serisi uretir."""
    indeks = pd.date_range(baslangic, periods=len(fiyatlar), freq=f"{gun_araligi}D", tz="UTC")
    return pd.Series(fiyatlar, index=indeks)


_ESLESME = VarlikEslesme("TEST", "STOCK", "TEST.IS")


# ---------------------------------------------------------------------------
# Ons -> gram cevrimi
# ---------------------------------------------------------------------------


def test_ons_usd_gram_try_cevrimi_dogru_hesaplanir():
    # 4458.10 USD/ons, 47.8960 USD/TRY -> (4458.10/31.1034768)*47.8960
    sonuc = ons_usd_to_gram_try(4458.10, 47.8960)

    beklenen = (4458.10 / TROY_ONS_GRAM) * 47.8960
    assert sonuc == pytest.approx(beklenen)
    assert sonuc == pytest.approx(6864.4, abs=1.0)  # ~6864 TL/gram


def test_ons_cevrimi_gecersiz_girdide_hata_verir():
    with pytest.raises(ValueError):
        ons_usd_to_gram_try(0, 47.0)
    with pytest.raises(ValueError):
        ons_usd_to_gram_try(4000.0, -1)


# ---------------------------------------------------------------------------
# Metrikler
# ---------------------------------------------------------------------------


def test_gunluk_degisim_son_iki_kapanistan_hesaplanir():
    veri = metrikleri_hesapla(_ESLESME, _seri([100.0, 110.0]))

    assert veri.current_price == 110.0
    assert veri.prev_close == 100.0
    assert veri.daily_change_pct == 10.0


def test_prev_close_ile_gunluk_degisim_sema_bagini_korur():
    """Sema: prev_close = current_price / (1 + daily_change_pct/100)."""
    veri = metrikleri_hesapla(_ESLESME, _seri([80.0, 92.0]))

    yeniden = veri.current_price / (1 + veri.daily_change_pct / 100)
    assert yeniden == pytest.approx(veri.prev_close, rel=1e-4)


def test_haftalik_degisim_takvim_gunune_gore_hesaplanir():
    """8 gunluk seride 7 takvim gunu oncesi ILK elemandir."""
    veri = metrikleri_hesapla(_ESLESME, _seri([100.0, 101, 102, 103, 104, 105, 106, 200.0]))

    # son = 200, 7 gun oncesi = 100 -> %100 artis
    assert veri.weekly_change_pct == 100.0


def test_hafta_sonu_bosluklari_yanlis_referans_secmez():
    """Islem gunleri seyrek olsa bile referans TAKVIM tarihinden secilir.

    3 gunde bir islem goren bir seride "7 satir geriye" gitmek 21 gun
    oncesine giderdi; dogru davranis 7 gun veya oncesindeki EN YAKIN
    kapanisi almaktir.
    """
    seri = _seri([10.0, 20.0, 30.0, 40.0], gun_araligi=3)  # 1, 4, 7, 10 Ocak

    veri = metrikleri_hesapla(_ESLESME, seri)

    # Son tarih 10 Ocak; 7 gun oncesi 3 Ocak -> o tarihte veya oncesinde
    # en yakin kapanis 1 Ocak'taki 10.0
    assert veri.weekly_change_pct == pytest.approx(300.0)


def test_seri_yeterince_geriye_gitmiyorsa_none_doner():
    """Bir yillik veri yoksa yillik degisim UYDURULMAZ."""
    veri = metrikleri_hesapla(_ESLESME, _seri([100.0, 105.0, 110.0]))

    assert veri.yearly_change_pct is None


def test_tam_bir_yillik_seri_yillik_degisim_URETEMEZ():
    """`--period 1y` tuzagi: seri tam 365 gun once BASLIYORSA referans yoktur.

    365 gun oncesi serinin ilk gununden ONCEsine dusuyorsa 'onceki veya
    esit' kayit bulunamaz. Bu yuzden varsayilan period 2y'dir.
    """
    seri = _seri([100.0 + i for i in range(365)])  # 1 Ocak'tan itibaren 365 gun

    veri = metrikleri_hesapla(_ESLESME, seri)

    assert veri.yearly_change_pct is None


def test_bir_yildan_uzun_seride_yillik_degisim_hesaplanir():
    seri = _seri([100.0] * 400)
    seri.iloc[-1] = 150.0  # son gun 150

    veri = metrikleri_hesapla(_ESLESME, seri)

    assert veri.yearly_change_pct == pytest.approx(50.0)


def test_gecmis_listesi_price_history_icin_hazir_doner():
    veri = metrikleri_hesapla(_ESLESME, _seri([100.0, 101.0, 102.0]))

    assert len(veri.gecmis) == 3
    ts, fiyat = veri.gecmis[-1]
    assert fiyat == 102.0
    assert ts.tzinfo is not None  # TIMESTAMPTZ icin zaman dilimi zorunlu


def test_volatilite_gunluk_getiri_sapmasi_olarak_hesaplanir():
    seri = _seri([100, 102, 101, 103, 105, 104, 106, 108])

    veri = metrikleri_hesapla(_ESLESME, seri)

    assert veri.volatilite is not None
    assert 0 < veri.volatilite < 0.1  # gunluk oynaklik makul aralikta


def test_cok_kisa_seride_volatilite_none_doner():
    veri = metrikleri_hesapla(_ESLESME, _seri([100.0, 101.0]))

    assert veri.volatilite is None


# ---------------------------------------------------------------------------
# Gram altin turetmesi
# ---------------------------------------------------------------------------


def test_gram_serisi_kur_ile_carpilir():
    altin = _seri([3110.34768, 3110.34768])  # /31.1034768 = tam 100 USD/gram
    kur = _seri([40.0, 50.0])

    gram = gram_try_serisi(altin, kur)

    assert gram.iloc[0] == pytest.approx(4000.0)
    assert gram.iloc[1] == pytest.approx(5000.0)


def test_kur_eksik_gunde_onceki_kur_kullanilir():
    """Altin islem gorup kur serisinde o gun veri yoksa son bilinen kur alinir."""
    altin = _seri([3110.34768, 3110.34768, 3110.34768])  # 1,2,3 Ocak
    kur = _seri([40.0])  # yalnizca 1 Ocak

    gram = gram_try_serisi(altin, kur)

    assert len(gram) == 3
    assert gram.iloc[2] == pytest.approx(4000.0)  # 1 Ocak kuru tasindi


def test_kur_serisi_altin_baslangicindan_sonra_basliyorsa_bos_gunler_dusurulur():
    altin = _seri([3110.34768, 3110.34768], baslangic="2026-01-01")
    kur = _seri([40.0], baslangic="2026-01-02")

    gram = gram_try_serisi(altin, kur)

    # 1 Ocak icin kur yok -> o gun dusurulur, 2 Ocak kalir
    assert len(gram) == 1


# ---------------------------------------------------------------------------
# Sembol eslemesi
# ---------------------------------------------------------------------------


def test_varsayilan_kategoriler_kriptoyu_icermez():
    semboller = {e.db_symbol for e in eslesmeleri_getir()}

    assert "THYAO" in semboller
    assert "GRAM_ALTIN" in semboller
    assert "USD/TRY" in semboller
    assert "BTC" not in semboller  # gorev kapsami disinda
    assert "CRYPTO" not in VARSAYILAN_KATEGORILER


def test_kategori_filtresi_calisir():
    semboller = {e.db_symbol for e in eslesmeleri_getir(["GOLD"])}

    assert semboller == {"GRAM_ALTIN", "GUMUS"}


def test_altin_eslesmeleri_turetilmis_isaretlidir():
    altin = next(e for e in eslesmeleri_getir(["GOLD"]) if e.db_symbol == "GRAM_ALTIN")

    assert altin.turetilmis is True
    assert altin.yahoo_ticker == "GC=F"


def test_bist_hisseleri_is_ekiyle_eslenir():
    hisseler = eslesmeleri_getir(["STOCK"])

    assert all(e.yahoo_ticker.endswith(".IS") for e in hisseler)
    assert all(not e.turetilmis for e in hisseler)
