"""`app.services.risk` - deterministik risk skoru.

SAYININ TEK KAYNAGI. Hem `RiskStrategyAgent` (sohbet) hem
`GET /api/risk/profile` (dashboard) bu fonksiyonu cagirir. Iki yerde
hesaplansaydi kullanici ekranda 70, sohbette 77 gorurdu - 27 Agustos
2026'da tam olarak bu yasandi.
"""

from __future__ import annotations

import pytest

from app.services.risk import (
    ASSET_CLASS_LABELS_TR,
    ASSET_CLASS_RISK,
    TOLERANCE_LIMITS,
    oynaklik_yuzdesi,
    risk_profili_hesapla,
)
from tests.helpers import allocation, holding

# --- Oynaklik -------------------------------------------------------------


def test_sabit_fiyat_serisinde_oynaklik_sifirdir():
    assert oynaklik_yuzdesi([100.0] * 10) == 0.0


def test_bos_seri_sifir_doner():
    assert oynaklik_yuzdesi([]) == 0.0


def test_ortalamasi_sifir_olan_seri_cokmez():
    """Sifira bolme korumasi."""
    assert oynaklik_yuzdesi([0.0, 0.0]) == 0.0


def test_dalgali_seri_daha_yuksek_oynaklik_verir():
    sakin = oynaklik_yuzdesi([100, 101, 99, 100, 101])
    dalgali = oynaklik_yuzdesi([100, 140, 60, 130, 70])
    assert dalgali > sakin > 0


def test_oynaklik_olcekten_bagimsizdir():
    """Ortalamaya gore normalize edildigi icin 1 TL'lik ve 1000 TL'lik iki
    varlik ayni goreli dalgayla ayni oynakligi verir."""
    a = oynaklik_yuzdesi([100, 110, 90])
    b = oynaklik_yuzdesi([1000, 1100, 900])
    assert a == pytest.approx(b)


# --- Bos / bozuk portfoy --------------------------------------------------


@pytest.mark.parametrize(
    "holdings",
    [[], [holding(market_value_try=0)], [holding(market_value_try=None)]],
)
def test_deger_tasimayan_portfoy_hesaplanamadi_doner(holdings):
    """ "Veri yok" ile "risksiz" KARISMASIN diye seviye `hesaplanamadi`,
    `holding_count` de 0 doner."""
    sonuc = risk_profili_hesapla(holdings, [])
    assert sonuc["risk_score"] == 0
    assert sonuc["risk_level"] == "hesaplanamadi"
    assert sonuc["holding_count"] == 0
    assert sonuc["components"] == {}


# --- Bilesenler -----------------------------------------------------------


def test_tek_sinifta_yogunlasma_tavan_puani_alir():
    sonuc = risk_profili_hesapla(
        [holding("BTC", asset_class="CRYPTO")],
        [allocation("CRYPTO", 100.0)],
    )
    assert sonuc["components"]["concentration"] == 40.0


def test_dengeli_dagilim_yogunlasma_cezasi_almaz():
    """%25 ve alti dengeli kabul edilir."""
    dort_sinif = [allocation(s, 25.0) for s in ("STOCK", "BOND", "GOLD", "FOREX")]
    holdings = [holding(s, asset_class=s, market_value_try=25_000) for s in ("A", "B", "C", "D")]
    sonuc = risk_profili_hesapla(holdings, dort_sinif)
    assert sonuc["components"]["concentration"] == 0.0


def test_kripto_tahvilden_daha_riskli_puanlanir():
    """Sinif katsayilari `ASSET_CLASS_RISK` tablosundan gelir."""
    kripto = risk_profili_hesapla(
        [holding("BTC", asset_class="CRYPTO")], [allocation("CRYPTO", 100.0)]
    )
    tahvil = risk_profili_hesapla(
        [holding("TAHVIL", asset_class="BOND")], [allocation("BOND", 100.0)]
    )
    assert kripto["components"]["asset_type"] > tahvil["components"]["asset_type"]
    assert kripto["risk_score"] > tahvil["risk_score"]


@pytest.mark.parametrize("sinif", sorted(ASSET_CLASS_RISK))
def test_bilinen_her_sinif_puanlanabilir(sinif):
    sonuc = risk_profili_hesapla([holding("X", asset_class=sinif)], [allocation(sinif, 100.0)])
    assert 0 <= sonuc["risk_score"] <= 100


def test_bilinmeyen_sinif_orta_katsayiya_duser():
    """Yeni bir sinif tabloya eklenmeden gelirse skor patlamamali."""
    sonuc = risk_profili_hesapla([holding("X", asset_class="NFT")], [allocation("NFT", 100.0)])
    assert 0 < sonuc["risk_score"] <= 100


def test_oynaklik_olculemezse_bilesen_sifir_kalir():
    sonuc = risk_profili_hesapla([holding()], [allocation()], volatility_by_symbol=None)
    assert sonuc["components"]["volatility"] == 0.0
    assert sonuc["avg_volatility_pct"] is None


def test_yuksek_oynaklik_tavan_puani_alir():
    """%8 ve ustu tam puan (15)."""
    sonuc = risk_profili_hesapla(
        [holding("BTC")], [allocation()], volatility_by_symbol={"BTC": 12.0}
    )
    assert sonuc["components"]["volatility"] == 15.0
    assert sonuc["avg_volatility_pct"] == 12.0


def test_tek_pozisyon_yogunlugu_ayri_cezalandirilir():
    """Sinif dagilimi dengeli olsa bile TEK varlik agirsa risk artar."""
    dev = holding("THYAO", asset_class="STOCK", market_value_try=900_000)
    kucuk = holding("GARAN", asset_class="BOND", market_value_try=100_000)
    sonuc = risk_profili_hesapla([dev, kucuk], [allocation("STOCK", 50), allocation("BOND", 50)])
    assert sonuc["components"]["single_position"] > 0


def test_dagilim_verilmezse_varliklardan_uretilir():
    """MCP tool ciktisi dagilim tasimayabilir; skor yine hesaplanabilmeli."""
    holdings = [
        holding("BTC", asset_class="CRYPTO", market_value_try=750_000),
        holding("TAH", asset_class="BOND", market_value_try=250_000),
    ]
    uretilen = risk_profili_hesapla(holdings, [])
    verilen = risk_profili_hesapla(holdings, [allocation("CRYPTO", 75.0), allocation("BOND", 25.0)])
    assert uretilen["risk_score"] == verilen["risk_score"]


# --- Skor ve seviye -------------------------------------------------------


def test_skor_bilesenlerin_toplamina_esittir():
    sonuc = risk_profili_hesapla(
        [holding("BTC", asset_class="CRYPTO")],
        [allocation("CRYPTO", 100.0)],
        volatility_by_symbol={"BTC": 6.0},
    )
    assert sonuc["risk_score"] == round(sum(sonuc["components"].values()))


def test_cesitlendirilmis_dusuk_riskli_portfoy_dusuk_seviye_alir():
    siniflar = ("BOND", "GOLD", "FOREX", "STOCK")
    sonuc = risk_profili_hesapla(
        [holding(s, asset_class=s, market_value_try=25_000) for s in siniflar],
        [allocation(s, 25.0) for s in siniflar],
    )
    assert sonuc["risk_score"] < 35
    assert sonuc["risk_level"] == "dusuk"


def test_tek_varlikli_kripto_portfoyu_cok_yuksek_seviye_alir():
    sonuc = risk_profili_hesapla(
        [holding("BTC", asset_class="CRYPTO")],
        [allocation("CRYPTO", 100.0)],
        volatility_by_symbol={"BTC": 20.0},
    )
    assert sonuc["risk_level"] == "cok yuksek"


def test_tek_varlikli_tahvil_portfoyu_bile_orta_seviyeye_cikar():
    """⚠️ SEZGIYE AYKIRI AMA DOGRU: en guvenli sinif bile TEK basina
    tutuldugunda yogunlasma (40) + tek pozisyon (10) cezasini alir.
    Model "hangi varlik" kadar "ne kadar dagitilmis" sorusunu da olcer."""
    sonuc = risk_profili_hesapla([holding("TAH", asset_class="BOND")], [allocation("BOND", 100.0)])
    assert sonuc["components"]["asset_type"] < 5  # sinif riski cok dusuk
    assert sonuc["risk_level"] == "orta"  # ama cesitlendirme yok


def test_skor_yuz_uzerine_cikmaz():
    """Tum bilesenler tavana vursa bile toplam 100'u asmamali."""
    sonuc = risk_profili_hesapla(
        [holding("BTC", asset_class="CRYPTO", market_value_try=1_000_000)],
        [allocation("CRYPTO", 100.0)],
        volatility_by_symbol={"BTC": 99.0},
    )
    assert sonuc["risk_score"] <= 100


# --- Tolerans uyumu -------------------------------------------------------


@pytest.mark.parametrize("tolerans", sorted(TOLERANCE_LIMITS))
def test_yuksek_skor_dusuk_toleransta_uyari_uretir(tolerans):
    sonuc = risk_profili_hesapla(
        [holding("BTC", asset_class="CRYPTO")],
        [allocation("CRYPTO", 100.0)],
        risk_tolerance=tolerans,
        volatility_by_symbol={"BTC": 20.0},
    )
    if sonuc["risk_score"] > TOLERANCE_LIMITS[tolerans]:
        assert sonuc["tolerance_alignment"] == "tolerans ustu"
        assert any("tolerans" in o for o in sonuc["suggestions"])


def test_tolerans_beyani_yoksa_uyum_bilinmiyor():
    sonuc = risk_profili_hesapla([holding()], [allocation()], risk_tolerance=None)
    assert sonuc["tolerance_alignment"] == "bilinmiyor"


def test_taninmayan_tolerans_degeri_cokme_uretmez():
    sonuc = risk_profili_hesapla([holding()], [allocation()], risk_tolerance="ASIRI")
    assert sonuc["tolerance_alignment"] == "bilinmiyor"


def test_cok_dusuk_risk_yuksek_toleransta_tolerans_alti_sayilir():
    sonuc = risk_profili_hesapla(
        [holding("TAH", asset_class="BOND")],
        [allocation("BOND", 100.0)],
        risk_tolerance="HIGH",
    )
    assert sonuc["tolerance_alignment"] == "tolerans alti"


# --- Gerekceler -----------------------------------------------------------


def test_gerekceler_turkce_sinif_etiketi_kullanir():
    """Kullanici "CRYPTO" degil "Kripto" gormeli."""
    sonuc = risk_profili_hesapla(
        [holding("BTC", asset_class="CRYPTO")], [allocation("CRYPTO", 100.0)]
    )
    assert any(ASSET_CLASS_LABELS_TR["CRYPTO"] in g for g in sonuc["reasons"])


def test_az_varlikli_portfoy_icin_gerekce_eklenir():
    sonuc = risk_profili_hesapla([holding()], [allocation()])
    assert any("yalnızca 1 varlık" in g for g in sonuc["reasons"])


def test_agir_tek_pozisyon_gerekcede_adiyla_gecer():
    dev = holding("THYAO", market_value_try=900_000)
    kucuk = holding("GARAN", market_value_try=100_000)
    sonuc = risk_profili_hesapla([dev, kucuk], [allocation("STOCK", 100.0)])
    assert any("THYAO" in g for g in sonuc["reasons"])


def test_ayni_girdi_ayni_skoru_verir():
    """Deterministiklik: dashboard ile sohbet ayni sayiyi gostermeli."""
    girdi = ([holding("BTC", asset_class="CRYPTO")], [allocation("CRYPTO", 100.0)])
    assert risk_profili_hesapla(*girdi) == risk_profili_hesapla(*girdi)
