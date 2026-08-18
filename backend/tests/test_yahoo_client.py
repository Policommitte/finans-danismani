"""Yahoo canli fiyat istemcisinin saf mantigi (`app/market/yahoo.py`).

BU TESTLER AGA CIKMAZ: yalnizca sembol eslemesi, ticker listesi uretimi ve
gram/TRY turetmesi sinanir. Gercek indirme `_indir` icinde izole edilmistir.

Kritik davranislar:
  * Turetilmis varlik istendiginde USD/TRY kuru OTOMATIK istege eklenir;
    eklenmezse gram altin fiyati hesaplanamaz.
  * Kur veya ons fiyati eksikse turetilmis varlik sonuca EKLENMEZ - yanlis
    fiyat yazmaktansa eski fiyat korunur.
"""

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
