"""Yahoo canli fiyat istemcisinin saf mantigi (`app/market/yahoo.py`).

BU TESTLER AGA CIKMAZ: sembol eslemesi, ticker listesi uretimi, gram/TRY
turetmesi ve `yf.download` ciktisinin cozulmesi sinanir. Gercek indirme
`_indir` icinde izole edilmistir; DataFrame'ler elde kurulur.

Kritik davranislar:
  * Turetilmis varlik istendiginde USD/TRY kuru OTOMATIK istege eklenir;
    eklenmezse gram altin fiyati hesaplanamaz.
  * Kur veya ons fiyati eksikse turetilmis varlik sonuca EKLENMEZ - yanlis
    fiyat yazmaktansa eski fiyat korunur.
  * `_son_fiyatlar` yfinance'in IKI farkli kolon bicimini de cozer; bozulursa
    sessizce bos sonuc doner ve sistem farkinda olmadan simulatore duser.
"""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

from app.market import yahoo

# ---------------------------------------------------------------------------
# Sembol eslemesi
# ---------------------------------------------------------------------------


def test_bist_hisseleri_is_ekiyle_eslenir():
    for sembol in ("THYAO", "GARAN", "TCELL", "SASA", "ASELS", "EREGL"):
        assert yahoo.YAHOO_TICKERS[sembol].endswith(".IS")


def test_desteklenen_semboller_turetilmisleri_de_icerir():
    desteklenen = yahoo.desteklenen_semboller()

    assert "THYAO" in desteklenen
    assert "GRAM_ALTIN" in desteklenen  # turetilmis
    assert "GUMUS" in desteklenen
    assert "TR10Y" not in desteklenen  # Yahoo'da guvenilir karsiligi yok


def test_altin_ve_gumus_dogrudan_eslenmez():
    """Yahoo'da TRY/gram sembolu yoktur; bunlar turetilir."""
    assert "GRAM_ALTIN" not in yahoo.YAHOO_TICKERS
    assert "GUMUS" not in yahoo.YAHOO_TICKERS
    assert yahoo.TURETILMIS_GRAM_TRY["GRAM_ALTIN"] == "GC=F"


# ---------------------------------------------------------------------------
# Ticker listesi
# ---------------------------------------------------------------------------


def test_dogrudan_semboller_icin_ticker_uretilir():
    assert yahoo.gerekli_tickerlar(["THYAO", "AAPL"]) == ["AAPL", "THYAO.IS"]


def test_turetilmis_sembol_kur_tickerini_de_ekler():
    """KRITIK: USD/TRY olmadan gram fiyati hesaplanamaz."""
    tickerlar = yahoo.gerekli_tickerlar(["GRAM_ALTIN"])

    assert "GC=F" in tickerlar
    assert yahoo.USDTRY_TICKER in tickerlar


def test_turetme_yoksa_kur_gereksiz_yere_eklenmez():
    tickerlar = yahoo.gerekli_tickerlar(["THYAO"])

    assert yahoo.USDTRY_TICKER not in tickerlar


def test_bilinmeyen_sembol_sessizce_atlanir():
    assert yahoo.gerekli_tickerlar(["YOKBOYLE", "THYAO"]) == ["THYAO.IS"]


def test_ayni_ticker_tekrar_edilmez():
    """USD/TRY hem varlik hem turetme girdisi olabilir; liste benzersizdir."""
    tickerlar = yahoo.gerekli_tickerlar(["USD/TRY", "GRAM_ALTIN"])

    assert tickerlar.count(yahoo.USDTRY_TICKER) == 1


# ---------------------------------------------------------------------------
# Fiyat turetme
# ---------------------------------------------------------------------------


def test_dogrudan_fiyat_oldugu_gibi_aktarilir():
    sonuc = yahoo.fiyatlari_turet({"THYAO.IS": 301.2534567}, ["THYAO"])

    assert sonuc == {"THYAO": 301.2535}  # 4 basamaga yuvarlanir


def test_gram_altin_ons_ve_kurdan_hesaplanir():
    # 3110.34768 / 31.1034768 = tam 100 USD/gram; 100 * 40 = 4000 TRY/gram
    ham = {"GC=F": 3110.34768, yahoo.USDTRY_TICKER: 40.0}

    sonuc = yahoo.fiyatlari_turet(ham, ["GRAM_ALTIN"])

    assert sonuc["GRAM_ALTIN"] == pytest.approx(4000.0)


def test_gercekci_degerlerle_gram_altin_makul_cikar():
    ham = {"GC=F": 4451.60, yahoo.USDTRY_TICKER: 47.9163}

    sonuc = yahoo.fiyatlari_turet(ham, ["GRAM_ALTIN"])

    assert 6000 < sonuc["GRAM_ALTIN"] < 8000


def test_kur_yoksa_turetilmis_varlik_atlanir():
    """Yanlis fiyat yazmaktansa eski fiyat korunur."""
    sonuc = yahoo.fiyatlari_turet({"GC=F": 4451.60}, ["GRAM_ALTIN"])

    assert "GRAM_ALTIN" not in sonuc


def test_ons_fiyati_yoksa_turetilmis_varlik_atlanir():
    sonuc = yahoo.fiyatlari_turet({yahoo.USDTRY_TICKER: 47.9}, ["GRAM_ALTIN"])

    assert "GRAM_ALTIN" not in sonuc


def test_eksik_fiyat_digerlerini_engellemez():
    """Bir sembol gelmezse digerleri yine de dondurulur (kismi basari)."""
    ham = {"THYAO.IS": 301.25}

    sonuc = yahoo.fiyatlari_turet(ham, ["THYAO", "AAPL", "GRAM_ALTIN"])

    assert sonuc == {"THYAO": 301.25}


def test_sifir_fiyat_gecerli_sayilmaz():
    sonuc = yahoo.fiyatlari_turet({"THYAO.IS": 0}, ["THYAO"])

    assert sonuc == {}


# ---------------------------------------------------------------------------
# Bos girdi
# ---------------------------------------------------------------------------


async def test_bos_sembol_listesi_ag_cagrisi_yapmaz():
    """Istenecek sembol yoksa Yahoo'ya HIC gidilmemeli."""
    assert await yahoo.canli_fiyatlar([]) == {}


async def test_yalnizca_desteklenmeyen_sembollerde_cagri_yapilmaz():
    assert await yahoo.canli_fiyatlar(["TR10Y", "YOKBOYLE"]) == {}


# ---------------------------------------------------------------------------
# `yf.download` ciktisinin cozulmesi (`_son_fiyatlar`)
#
# BU MODULDEKI EN KIRILGAN YER: yfinance surum degisikliklerinde kolon yapisi
# degisir. Bozuldugunda istisna FIRLATMAZ, sessizce bos sozluk doner - yani
# saglayici "Yahoo bos dondu" deyip simulatore duser ve kimse fark etmez.
# ---------------------------------------------------------------------------

NAN = float("nan")


def _coklu_ticker_df(kapanislar: dict[str, list[float]]) -> pd.DataFrame:
    """`yf.download`'un COKLU ticker ciktisi.

    Kolonlar (Price, Ticker) MultiIndex'idir; `group_by="column"` varsayilani
    ile ust seviye 'Close', 'Open' gibi alan adlaridir.
    """
    uzunluk = len(next(iter(kapanislar.values())))
    indeks = pd.date_range("2026-08-19 10:00", periods=uzunluk, freq="min")

    veri: dict[tuple[str, str], list[float]] = {}
    for ticker, seri in kapanislar.items():
        veri[("Close", ticker)] = seri
        # Gercek ciktida baska alanlar da vardir; kod yalnizca Close okumali.
        veri[("Open", ticker)] = [0.0] * uzunluk

    df = pd.DataFrame(veri, index=indeks)
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["Price", "Ticker"])
    return df


def _tek_ticker_duz_df(kapanis: list[float]) -> pd.DataFrame:
    """`multi_level_index=False` (veya eski yfinance) ciktisi: DUZ kolonlar.

    Bu bicimde `df["Close"]` bir Series'tir, DataFrame degil.
    """
    indeks = pd.date_range("2026-08-19 10:00", periods=len(kapanis), freq="min")
    return pd.DataFrame({"Close": kapanis, "Open": [0.0] * len(kapanis)}, index=indeks)


def test_coklu_ticker_son_kapanislari_cozulur():
    df = _coklu_ticker_df({"THYAO.IS": [300.0, 301.5], "AAPL": [215.0, 216.25]})

    sonuc = yahoo._son_fiyatlar(df, ["AAPL", "THYAO.IS"])

    assert sonuc == {"THYAO.IS": 301.5, "AAPL": 216.25}


def test_onceki_islem_gununun_kapanisi_ayri_doner():
    indeks = pd.to_datetime(["2026-08-18 17:59", "2026-08-19 10:00", "2026-08-19 10:01"])
    df = pd.DataFrame({"Close": [298.0, 300.0, 301.5]}, index=indeks)

    sonuc = yahoo._son_kotasyonlar(df, ["THYAO.IS"])

    assert sonuc == {"THYAO.IS": {"price": 301.5, "previous_close": 298.0}}


def test_turetilmis_kotasyon_onceki_metal_ve_kuru_birlikte_kullanir():
    ham = {
        "GC=F": {"price": 3110.34768, "previous_close": 2799.312912},
        yahoo.USDTRY_TICKER: {"price": 40.0, "previous_close": 39.0},
    }

    sonuc = yahoo.kotasyonlari_turet(ham, ["GRAM_ALTIN"])

    assert sonuc["GRAM_ALTIN"]["price"] == pytest.approx(4000.0)
    assert sonuc["GRAM_ALTIN"]["previous_close"] == pytest.approx(3510.0)


def test_son_satir_bossa_bir_onceki_gecerli_kapanis_alinir():
    """Intraday veride son mumlar cogu zaman NaN gelir - atlanmalidir."""
    df = _coklu_ticker_df({"THYAO.IS": [300.0, 301.5, NAN, NAN]})

    sonuc = yahoo._son_fiyatlar(df, ["THYAO.IS"])

    assert sonuc == {"THYAO.IS": 301.5}


def test_tamamen_bos_ticker_sonuca_girmez():
    """Bir sembol gelmezse digerleri yine de donmeli (kismi basari)."""
    df = _coklu_ticker_df({"THYAO.IS": [300.0, 301.5], "SOL-USD": [NAN, NAN]})

    sonuc = yahoo._son_fiyatlar(df, ["SOL-USD", "THYAO.IS"])

    assert sonuc == {"THYAO.IS": 301.5}


def test_sifir_kapanis_gecerli_sayilmaz():
    """0 fiyat gercek bir kotasyon degildir; yazilirsa dashboard bozulur."""
    df = _coklu_ticker_df({"THYAO.IS": [300.0, 0.0]})

    assert yahoo._son_fiyatlar(df, ["THYAO.IS"]) == {}


def test_tek_ticker_duz_bicim_de_cozulur():
    """`Close` Series geldiginde ticker adi listeden alinir."""
    df = _tek_ticker_duz_df([300.0, 301.5])

    sonuc = yahoo._son_fiyatlar(df, ["THYAO.IS"])

    assert sonuc == {"THYAO.IS": 301.5}


def test_bos_dataframe_bos_sozluk_dondurur():
    assert yahoo._son_fiyatlar(pd.DataFrame(), ["THYAO.IS"]) == {}


def test_none_bos_sozluk_dondurur():
    """yfinance hata durumunda `None` donebilir; istisna firlatilmamali."""
    assert yahoo._son_fiyatlar(None, ["THYAO.IS"]) == {}


# ---------------------------------------------------------------------------
# Sembol tablosu senkronu
# ---------------------------------------------------------------------------


def _borsa_verisi_symbols():
    """`borsa-verisi/symbols.py`'yi dosya yolundan yukler.

    `borsa-verisi/` bir paket DEGILDIR ve backend onu import etmez; bu yuzden
    normal `import` calismaz. Klasor yoksa (backend tek basina kullanildiginda)
    test atlanir.
    """
    yol = Path(__file__).resolve().parents[2] / "borsa-verisi" / "symbols.py"
    if not yol.exists():
        pytest.skip("borsa-verisi/ bu kopyada yok")

    spec = importlib.util.spec_from_file_location("borsa_verisi_symbols", yol)
    modul = importlib.util.module_from_spec(spec)
    # `sys.modules`'a ONCE yazilmali: `symbols.py` `from __future__ import
    # annotations` kullaniyor ve @dataclass alan tiplerini cozerken modulu
    # `sys.modules` uzerinden ariyor - kayitli degilse AttributeError verir.
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


def test_sembol_tablosu_borsa_verisi_ile_ayni():
    """AYNI ESLEME IKI YERDE DURUYOR - ayrisirlarsa burasi kirmizi yanar.

    `app/market/yahoo.py` canli fiyati, `borsa-verisi/symbols.py` gecmis
    veriyi ceker. Biri duzeltilip digeri unutulursa grafikteki gecmis seri ile
    canli fiyat FARKLI enstrumanlardan gelir ve bu sessizce olur.
    """
    symbols = _borsa_verisi_symbols()

    dogrudan = {e.db_symbol: e.yahoo_ticker for e in symbols.ESLESMELER if not e.turetilmis}
    turetilmis = {e.db_symbol: e.yahoo_ticker for e in symbols.ESLESMELER if e.turetilmis}

    assert yahoo.YAHOO_TICKERS == dogrudan
    assert yahoo.TURETILMIS_GRAM_TRY == turetilmis


def test_troy_ons_sabiti_iki_yerde_ayni():
    """Sabit ayrisirsa gram altin fiyati iki kaynakta farkli cikar."""
    symbols = _borsa_verisi_symbols()

    assert yahoo.TROY_ONS_GRAM == symbols.TROY_ONS_GRAM
    assert yahoo.USDTRY_TICKER == symbols.USDTRY_TICKER
