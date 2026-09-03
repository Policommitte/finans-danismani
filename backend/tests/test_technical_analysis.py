"""Teknik analiz motoru testleri - gostergeler, sinyaller ve veri kaynagi sirasi.

Aga ve veritabanina CIKMAZ: mum kaynaklari monkeypatch ile degistirilir.
"""

import math

import pytest

from app.services import technical_analysis as service
from app.services.technical_analysis import (
    MIN_CANDLES,
    _label,
    _summarize,
    summary_text,
    technical_analysis,
)


def _candles(closes: list[float], *, with_range: bool = True) -> list[dict]:
    """Kapanis listesinden gunluk mum serisi uretir."""
    return [
        (
            {
                "ts": f"2026-01-{(index % 28) + 1:02d} 00:00:00+00:00",
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
            }
            if with_range
            else {"ts": f"2026-01-{(index % 28) + 1:02d} 00:00:00+00:00", "close": close}
        )
        for index, close in enumerate(closes)
    ]


class SahteDepo:
    """`get_candles` / `get_history` doner; hangisinin cagrildigi kaydedilir."""

    def __init__(self, candles=None, history=None):
        self._candles = candles or []
        self._history = history or []
        self.candle_calls: list[dict] = []

    async def get_candles(self, symbol: str, interval: str = "5m", days: int = 5) -> list[dict]:
        self.candle_calls.append({"symbol": symbol, "interval": interval, "days": days})
        return self._candles

    async def get_history(self, symbol: str, days: int = 30) -> list[dict]:
        return self._history


@pytest.fixture
def sahte_depo(monkeypatch):
    def _kur(depo: SahteDepo, yahoo=None):
        monkeypatch.setattr(service, "get_market_repository", lambda: depo)

        async def _gunluk_ohlc(sembol: str, gun: int):
            return yahoo

        monkeypatch.setattr(service, "gunluk_ohlc", _gunluk_ohlc)
        return depo

    return _kur


# ---------------------------------------------------------------------------
# Sinyal ve ozet siniflandirmasi
# ---------------------------------------------------------------------------


def test_ozet_esikleri():
    assert _label(1.0) == "GUCLU_AL"
    assert _label(0.5) == "GUCLU_AL"
    assert _label(0.2) == "AL"
    assert _label(0.0) == "NOTR"
    assert _label(-0.2) == "SAT"
    assert _label(-0.6) == "GUCLU_SAT"


def test_veri_yok_sinyali_skora_girmez():
    ozet = _summarize(["AL", "AL", "VERI_YOK", "VERI_YOK"])
    assert ozet is not None
    assert ozet.buy == 2
    assert ozet.score == 1.0  # iki sinyalin ortalamasi, dorde bolunmez


def test_hepsi_veri_yoksa_ozet_uretilmez():
    assert _summarize(["VERI_YOK", "VERI_YOK"]) is None


# ---------------------------------------------------------------------------
# Yetersiz veri
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_yetersiz_veride_sinif_uretilmez(sahte_depo):
    sahte_depo(SahteDepo(candles=_candles([100.0 + i for i in range(MIN_CANDLES - 1)])))

    sonuc = await technical_analysis("THYAO")

    assert sonuc.sufficient is False
    assert sonuc.summary is None
    assert sonuc.indicators == []
    assert str(MIN_CANDLES) in sonuc.reason


@pytest.mark.asyncio
async def test_hic_veri_yoksa_hata_firlatilmaz(sahte_depo):
    sahte_depo(SahteDepo(), yahoo=None)

    sonuc = await technical_analysis("BILINMEYEN")

    assert sonuc.sufficient is False
    assert sonuc.source == "yok"
    assert sonuc.candle_count == 0


# ---------------------------------------------------------------------------
# Veri kaynagi sirasi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_once_kayitli_gunluk_mumlar_kullanilir(sahte_depo):
    depo = sahte_depo(SahteDepo(candles=_candles([100.0 + i for i in range(60)])))

    sonuc = await technical_analysis("THYAO", days=200)

    assert sonuc.source == "market_candles"
    assert depo.candle_calls[0]["interval"] == "1d"
    assert depo.candle_calls[0]["days"] == 200


@pytest.mark.asyncio
async def test_depo_bossa_yahoo_yoluna_dusulur(sahte_depo):
    sahte_depo(SahteDepo(), yahoo=_candles([100.0 + i for i in range(60)]))

    sonuc = await technical_analysis("THYAO")

    assert sonuc.source == "yahoo"
    assert sonuc.sufficient is True


@pytest.mark.asyncio
async def test_son_care_kapanis_serisidir(sahte_depo):
    history = [{"ts": f"2026-01-{(i % 28) + 1:02d}", "price": 100.0 + i} for i in range(60)]
    sahte_depo(SahteDepo(history=history), yahoo=None)

    sonuc = await technical_analysis("GRAM_ALTIN")

    assert sonuc.source == "price_history"
    assert sonuc.sufficient is True


@pytest.mark.asyncio
async def test_kapanis_serisinde_aralik_gostergeleri_hesaplanmaz(sahte_depo):
    history = [{"ts": f"2026-01-{(i % 28) + 1:02d}", "price": 100.0 + i} for i in range(60)]
    sahte_depo(SahteDepo(history=history), yahoo=None)

    sonuc = await technical_analysis("GRAM_ALTIN")

    aralik_gerektirenler = {"stoch_k_9_6", "adx_14", "cci_20", "willr_14"}
    for indicator in sonuc.indicators:
        if indicator.key in aralik_gerektirenler:
            assert indicator.signal == "VERI_YOK"
            assert indicator.value is None
        else:
            assert indicator.value is not None


# ---------------------------------------------------------------------------
# Gosterge degerleri ve yon
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kesintisiz_yukselis_al_uretir(sahte_depo):
    sahte_depo(SahteDepo(candles=_candles([100.0 + i for i in range(120)])))

    sonuc = await technical_analysis("THYAO")

    assert sonuc.summary.label in ("AL", "GUCLU_AL")
    # Fiyat her ortalamanin ustunde: hicbir MA "SAT" veremez.
    assert all(ma.sma_signal in ("AL", "VERI_YOK") for ma in sonuc.moving_averages)


@pytest.mark.asyncio
async def test_kesintisiz_dusus_sat_uretir(sahte_depo):
    sahte_depo(SahteDepo(candles=_candles([300.0 - i for i in range(120)])))

    sonuc = await technical_analysis("THYAO")

    assert sonuc.summary.label in ("SAT", "GUCLU_SAT")
    assert all(ma.sma_signal in ("SAT", "VERI_YOK") for ma in sonuc.moving_averages)


@pytest.mark.asyncio
async def test_rsi_degeri_wilder_konvansiyonuyla_hesaplanir(sahte_depo):
    """Kesintisiz yukseliste RSI 100'e yaklasir - kutuphane konvansiyonu teyidi."""
    sahte_depo(SahteDepo(candles=_candles([100.0 + i for i in range(60)])))

    sonuc = await technical_analysis("THYAO")

    rsi = next(i for i in sonuc.indicators if i.key == "rsi_14")
    assert math.isclose(rsi.value, 100.0, abs_tol=0.01)
    assert rsi.signal == "SAT"  # 70 uzeri asiri alim


@pytest.mark.asyncio
async def test_uzun_ortalamalar_mum_yetmezse_veri_yok(sahte_depo):
    sahte_depo(SahteDepo(candles=_candles([100.0 + i for i in range(60)])))

    sonuc = await technical_analysis("THYAO")

    uzun = next(ma for ma in sonuc.moving_averages if ma.period == 200)
    assert uzun.sma is None
    assert uzun.sma_signal == "VERI_YOK"
    kisa = next(ma for ma in sonuc.moving_averages if ma.period == 20)
    assert kisa.sma is not None


# ---------------------------------------------------------------------------
# Ajana giden ozet metni
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ozet_metni_aralik_ve_zaman_bilgisi_tasir(sahte_depo):
    sahte_depo(SahteDepo(candles=_candles([100.0 + i for i in range(120)])))

    metin = summary_text(await technical_analysis("THYAO"))

    assert "gunluk mumlar" in metin
    assert "120 mum" in metin
    assert "RSI(14)" in metin


@pytest.mark.asyncio
async def test_yetersiz_veride_ozet_metni_sayi_icermez(sahte_depo):
    sahte_depo(SahteDepo(candles=_candles([100.0, 101.0, 102.0])))

    metin = summary_text(await technical_analysis("THYAO"))

    assert "teknik analiz yapilamadi" in metin
    assert "RSI" not in metin
