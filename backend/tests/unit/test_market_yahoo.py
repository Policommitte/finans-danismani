"""`app.market.yahoo` - ticker esleme ve fiyat turetme (aga cikmayan kisim).

Bu dosya HICBIR ag cagrisi yapmaz: yalnizca sembol tablosu, turetme
matematigi ve upsert daraltma kurallari sinanir. Indirme yolunun kendisi
`tests/services/test_market_scheduler.py` icinde sahte saglayiciyla
calisir.
"""

from __future__ import annotations

import pytest

from app.market.yahoo import (
    TROY_ONS_GRAM,
    TURETILMIS_GRAM_TRY,
    USDTRY_TICKER,
    YAHOO_TICKERS,
    desteklenen_semboller,
    fiyatlari_turet,
    gerekli_tickerlar,
    ilk_mum_paketini_daralt,
    kotasyonlari_turet,
    son_mumlari_daralt,
    tamamlanmis_saatlik_mumlar,
)

from datetime import datetime, timedelta, timezone


# --- Sembol tablosu -------------------------------------------------------


def test_desteklenen_semboller_iki_tabloyu_birlestirir():
    assert desteklenen_semboller() == set(YAHOO_TICKERS) | set(TURETILMIS_GRAM_TRY)


def test_turetilmis_semboller_dogrudan_tabloda_YER_ALMAZ():
    """Ayni sembol iki tabloda olsaydi `gerekli_tickerlar` kur eklemeyi
    atlar ve gram fiyati hic hesaplanamazdi."""
    assert not set(TURETILMIS_GRAM_TRY) & set(YAHOO_TICKERS)


def test_bist_hisseleri_is_ekiyle_yazilir():
    assert YAHOO_TICKERS["THYAO"] == "THYAO.IS"
    assert all(t.endswith(".IS") for s, t in YAHOO_TICKERS.items() if s in {"GARAN", "ASELS"})


def _borsa_verisi_modulu():
    """`borsa-verisi/symbols.py`'i backend'i kirletmeden yukler.

    `sys.modules`'e KAYDEDILMESI sart: modul `@dataclass` kullanir ve
    dataclasses, ClassVar cozumlemesi icin `sys.modules[cls.__module__]`'e
    bakar - kayitsiz yuklemede orasi `None` doner ve import patlar.
    """
    import importlib.util
    import sys
    from pathlib import Path

    betik = Path(__file__).resolve().parents[3] / "borsa-verisi" / "symbols.py"
    if not betik.exists():
        pytest.skip("borsa-verisi/symbols.py bu kurulumda yok")

    ad = "_test_borsa_symbols"
    spec = importlib.util.spec_from_file_location(ad, betik)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[ad] = modul
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.modules.pop(ad, None)
    return modul


def test_sembol_tablosu_borsa_verisi_betigi_ile_AYNI():
    """⚠️ IKI YERDE DURAN ESLEME. `borsa-verisi/symbols.py` bagimsiz bir
    betiktir, backend'i import ETMEZ ve tabloyu kendi bicimiyle
    (`ESLESMELER`) tutar. Elle senkron tutulurlar - ayrisirlarsa fiyat
    gorevi ve gecmis dolduran betik FARKLI varlik kumeleri cekmeye baslar
    ve kimse fark etmez. Bu test o sessiz ayrismayi yakalar."""
    modul = _borsa_verisi_modulu()

    dogrudan = {e.db_symbol: e.yahoo_ticker for e in modul.ESLESMELER if not e.turetilmis}
    turetilmis = {e.db_symbol: e.yahoo_ticker for e in modul.ESLESMELER if e.turetilmis}

    assert dogrudan == YAHOO_TICKERS
    assert turetilmis == TURETILMIS_GRAM_TRY


def test_troy_ons_sabiti_iki_yerde_AYNI():
    """Sabit ayrisirsa gram altin fiyati backend ile arsiv betiginde
    farkli hesaplanir - grafik ile canli fiyat tutmaz."""
    assert _borsa_verisi_modulu().TROY_ONS_GRAM == TROY_ONS_GRAM


# --- gerekli_tickerlar ----------------------------------------------------


def test_bilinen_semboller_ticker_a_cevrilir():
    assert gerekli_tickerlar(["THYAO", "AAPL"]) == sorted(["THYAO.IS", "AAPL"])


def test_bilinmeyen_sembol_sessizce_atlanir():
    assert gerekli_tickerlar(["YOK_BOYLE_BIR_SEY"]) == []


def test_turetilmis_varlik_kuru_da_ister():
    """Gram altin ons/USD fiyatindan uretilir; kur olmadan hesaplanamaz."""
    tickerlar = gerekli_tickerlar(["GRAM_ALTIN"])
    assert TURETILMIS_GRAM_TRY["GRAM_ALTIN"] in tickerlar
    assert USDTRY_TICKER in tickerlar


def test_turetme_yoksa_kur_bosuna_eklenmez():
    assert USDTRY_TICKER not in gerekli_tickerlar(["AAPL"])


def test_kur_zaten_isteniyorsa_mukerrer_eklenmez():
    tickerlar = gerekli_tickerlar(["USD/TRY", "GRAM_ALTIN"])
    assert tickerlar.count(USDTRY_TICKER) == 1


# --- fiyat turetme --------------------------------------------------------


def test_dogrudan_fiyatlar_dort_basamaga_yuvarlanir():
    assert fiyatlari_turet({"THYAO.IS": 312.123456}, ["THYAO"]) == {"THYAO": 312.1235}


def test_gram_altin_ons_ve_kurdan_hesaplanir():
    ons_usd, kur = 2_500.0, 34.0
    (sonuc,) = fiyatlari_turet(
        {TURETILMIS_GRAM_TRY["GRAM_ALTIN"]: ons_usd, USDTRY_TICKER: kur}, ["GRAM_ALTIN"]
    ).values()
    assert sonuc == pytest.approx(ons_usd / TROY_ONS_GRAM * kur, abs=1e-4)


def test_kur_yoksa_turetilmis_varlik_SONUCA_EKLENMEZ():
    """Yanlis fiyat yazmaktansa eski fiyat korunur."""
    ham = {TURETILMIS_GRAM_TRY["GRAM_ALTIN"]: 2_500.0}
    assert fiyatlari_turet(ham, ["GRAM_ALTIN"]) == {}


def test_sifir_fiyat_sonuca_yazilmaz():
    assert fiyatlari_turet({"THYAO.IS": 0}, ["THYAO"]) == {}


def test_troy_ons_sabiti_kiymetli_maden_standardidir():
    assert TROY_ONS_GRAM == pytest.approx(31.1034768)


# --- kotasyon turetme -----------------------------------------------------


def test_kotasyon_fiyat_ve_onceki_kapanisi_tasir():
    ham = {"THYAO.IS": {"price": 310.0, "previous_close": 300.0}}
    assert kotasyonlari_turet(ham, ["THYAO"]) == {
        "THYAO": {"price": 310.0, "previous_close": 300.0}
    }


def test_onceki_kapanis_yoksa_none_kalir():
    """Gunluk degisim hesaplanamaz ama fiyat yine de yazilabilir."""
    ham = {"THYAO.IS": {"price": 310.0, "previous_close": None}}
    assert kotasyonlari_turet(ham, ["THYAO"])["THYAO"]["previous_close"] is None


def test_fiyati_olmayan_kotasyon_atlanir():
    assert kotasyonlari_turet({"THYAO.IS": {"price": None}}, ["THYAO"]) == {}


def test_turetilmis_kotasyonun_onceki_kapanisi_da_cevrilir():
    """Gram altinin dunku kapanisi, dunku ons VE dunku kur ile hesaplanir -
    bugunku kurla degil."""
    ham = {
        TURETILMIS_GRAM_TRY["GRAM_ALTIN"]: {"price": 2_500.0, "previous_close": 2_400.0},
        USDTRY_TICKER: {"price": 34.0, "previous_close": 33.0},
    }
    sonuc = kotasyonlari_turet(ham, ["GRAM_ALTIN"])["GRAM_ALTIN"]
    assert sonuc["previous_close"] == pytest.approx(2_400.0 / TROY_ONS_GRAM * 33.0, abs=1e-4)


def test_turetilmis_kotasyonda_kur_gecmisi_yoksa_onceki_kapanis_none():
    ham = {
        TURETILMIS_GRAM_TRY["GRAM_ALTIN"]: {"price": 2_500.0, "previous_close": 2_400.0},
        USDTRY_TICKER: {"price": 34.0, "previous_close": None},
    }
    assert kotasyonlari_turet(ham, ["GRAM_ALTIN"])["GRAM_ALTIN"]["previous_close"] is None


# --- Upsert daraltma ------------------------------------------------------


def mum(sembol: str, aralik: str, ts: str) -> dict:
    return {"symbol": sembol, "interval": aralik, "ts": ts}


def test_son_mumlari_daralt_aralik_basina_sinir_uygular():
    """Her tick'te on binlerce satiri tekrar upsert etmek yerine yalnizca
    DEGISEBILECEK son satirlar yollanir."""
    mumlar = [mum("THYAO", "5m", f"2026-09-02T10:{i:02d}:00") for i in range(10)]
    daraltilmis = son_mumlari_daralt(mumlar)
    assert len(daraltilmis) == 3  # 5m siniri
    assert [m["ts"] for m in daraltilmis] == [m["ts"] for m in mumlar[-3:]]


def test_daraltma_sembol_ve_aralik_basina_ayri_calisir():
    mumlar = [
        *[mum("THYAO", "1h", f"2026-09-02T{i:02d}:00:00") for i in range(5)],
        *[mum("GARAN", "1h", f"2026-09-02T{i:02d}:00:00") for i in range(5)],
    ]
    daraltilmis = son_mumlari_daralt(mumlar)
    assert len(daraltilmis) == 4  # her sembol icin 2
    assert {m["symbol"] for m in daraltilmis} == {"THYAO", "GARAN"}


def test_bilinmeyen_aralikta_yalnizca_son_satir_kalir():
    mumlar = [mum("X", "2h", f"2026-09-02T{i:02d}:00:00") for i in range(4)]
    assert len(son_mumlari_daralt(mumlar)) == 1


def test_ilk_paket_arsivlik_serileri_KORUR_yalnizca_saatligi_daraltir():
    """Ilk canli paket eski saatlik arsivin ustune yazmamali; 1d/5m
    serileri ise tam yazilir (bosluk kapatma)."""
    saatlik = [mum("THYAO", "1h", f"2026-09-02T{i:02d}:00:00") for i in range(6)]
    gunluk = [mum("THYAO", "1d", f"2026-09-0{i}T00:00:00") for i in range(1, 6)]
    sonuc = ilk_mum_paketini_daralt(saatlik + gunluk)

    assert len([m for m in sonuc if m["interval"] == "1d"]) == 5  # tam korundu
    assert len([m for m in sonuc if m["interval"] == "1h"]) == 2  # daraltildi


# --- Devam eden saat ------------------------------------------------------


def test_devam_eden_saatlik_mum_uzlastirmaya_YAZILMAZ():
    """Yahoo son 1h satirini piyasa acikken guncelleyebilir. Uzlastirma
    yalniz KAPANMIS saatleri yazarsa, canli 1dk cevabindan uretilen mevcut
    mum geriye dogru degismez."""
    simdi = datetime(2026, 9, 2, 13, 30, tzinfo=timezone.utc)
    mumlar = [
        {"ts": "2026-09-02T11:00:00+00:00"},  # kapandi
        {"ts": "2026-09-02T12:00:00+00:00"},  # kapandi (13:00'da)
        {"ts": "2026-09-02T13:00:00+00:00"},  # DEVAM EDIYOR
    ]
    kalanlar = tamamlanmis_saatlik_mumlar(mumlar, now=simdi)
    assert [m["ts"] for m in kalanlar] == [mumlar[0]["ts"], mumlar[1]["ts"]]


def test_tam_saat_sinirindaki_mum_kapanmis_sayilir():
    simdi = datetime(2026, 9, 2, 13, 0, tzinfo=timezone.utc)
    mumlar = [{"ts": "2026-09-02T12:00:00+00:00"}]
    assert tamamlanmis_saatlik_mumlar(mumlar, now=simdi) == mumlar


def test_zaman_dilimsiz_referans_utc_kabul_edilir():
    naif = datetime(2026, 9, 2, 13, 30)
    mumlar = [{"ts": "2026-09-02T11:00:00+00:00"}]
    assert tamamlanmis_saatlik_mumlar(mumlar, now=naif) == mumlar


def test_z_sonekli_zaman_damgasi_ayristirilir():
    simdi = datetime(2026, 9, 2, 13, 30, tzinfo=timezone.utc)
    assert tamamlanmis_saatlik_mumlar([{"ts": "2026-09-02T11:00:00Z"}], now=simdi)


def test_gelecek_tarihli_mum_yazilmaz():
    simdi = datetime(2026, 9, 2, 13, 30, tzinfo=timezone.utc)
    gelecek = (simdi + timedelta(hours=5)).isoformat()
    assert tamamlanmis_saatlik_mumlar([{"ts": gelecek}], now=simdi) == []
