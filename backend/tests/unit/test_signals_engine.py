"""`app.signals.engine` - tarama bazli sinyal uretimi (UC-07).

Motor SAF ve DETERMINISTIKTIR: LLM yok, I/O yok. Bu sart, "neden bana
geldi?" (FR-AUT-012) ucunun gercek bir cevap verebilmesinin temeli - metin
bir modelin o anki ciktisi degil, kural tablosunun sonucu.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.signals.engine import ISLEM_DISI_SINIFLAR, KURAL_ADLARI, kural_adi, sinyal_uret
from tests.helpers import asset

SIMDI = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


def uret(varliklar, *, threshold=0.0, ttl=240, bayatlik=30):
    return sinyal_uret(
        varliklar,
        now=SIMDI,
        threshold=threshold,
        ttl_minutes=ttl,
        max_staleness_minutes=bayatlik,
    )


def taze(**alanlar):
    """Bayatlik kontrolunden gecen bir varlik satiri."""
    return asset(price_updated_at=SIMDI, **alanlar)


# --- Kural tablosu --------------------------------------------------------


def test_sert_dusus_satis_sinyali_uretir():
    (s,) = uret([taze(daily_change_pct=-6.0)])
    assert s["rule_code"] == "SHARP_DROP"
    assert s["direction"] == "SELL"


def test_asiri_isinma_kar_realizasyonu_onerir():
    (s,) = uret([taze(weekly_change_pct=14.0, daily_change_pct=0.5)])
    assert (s["rule_code"], s["direction"]) == ("OVEREXTENDED", "SELL")


def test_yukselis_trendinde_geri_cekilme_alim_sinyali_uretir():
    (s,) = uret([taze(yearly_change_pct=20.0, weekly_change_pct=-5.0)])
    assert (s["rule_code"], s["direction"]) == ("PULLBACK_IN_UPTREND", "BUY")


def test_istikrarli_yukselis_dusuk_guvenli_alim_uretir():
    (s,) = uret([taze(yearly_change_pct=18.0, weekly_change_pct=2.0)])
    assert (s["rule_code"], s["direction"]) == ("STEADY_UPTREND", "BUY")
    assert s["confidence"] < 0.55  # temkinli


def test_kurallar_birbirini_disliyor_ve_ilk_eslesen_kazaniyor():
    """FR-AUT-001: her oneri tek enstruman ve TEK yon icerir. Sert dusus
    ayni anda asiri isinma kosulunu da saglayan bir satirda kazanmali -
    risk azaltan kural once gelir."""
    sinyaller = uret([taze(daily_change_pct=-8.0, weekly_change_pct=15.0)])
    assert len(sinyaller) == 1
    assert sinyaller[0]["rule_code"] == "SHARP_DROP"


def test_hicbir_kurala_uymayan_varlik_sinyal_uretmez():
    assert uret([taze(daily_change_pct=0.2, weekly_change_pct=1.0, yearly_change_pct=3.0)]) == []


# --- Eleme kurallari ------------------------------------------------------


@pytest.mark.parametrize("sinif", sorted(ISLEM_DISI_SINIFLAR))
def test_islem_disi_siniflar_elenir(sinif):
    """Endeks ve tahvil-getiri gostergesi dogrudan alinip satilamaz."""
    assert uret([taze(asset_class=sinif, daily_change_pct=-9.0)]) == []


@pytest.mark.parametrize("fiyat", [0, None, -1])
def test_fiyati_olmayan_varlik_elenir(fiyat):
    assert uret([taze(current_price=fiyat, daily_change_pct=-9.0)]) == []


def test_bayat_fiyatli_varlik_elenir():
    """KRITIK: bayat fiyatla uretilen oneri onaylanirsa emir, fiyat gelene
    kadar PENDING asili kalir - kullaniciya asla gerceklesmeyecek bir emir
    onerilmis olur."""
    bayat = asset(daily_change_pct=-9.0, price_updated_at=SIMDI.replace(hour=11, minute=0))
    assert uret([bayat], bayatlik=30) == []
    assert len(uret([bayat], bayatlik=120)) == 1


def test_zaman_damgasi_olmayan_varlik_bayat_sayilir():
    """Fail-closed: bilinmiyorsa oneri URETME."""
    assert uret([asset(daily_change_pct=-9.0, price_updated_at=None)]) == []


@pytest.mark.parametrize("ham", ["bozuk-tarih", "2026-13-45"])
def test_cozulemeyen_zaman_damgasi_bayat_sayilir(ham):
    assert uret([asset(daily_change_pct=-9.0, price_updated_at=ham)]) == []


def test_zaman_dilimsiz_damga_utc_kabul_edilir():
    naif = SIMDI.replace(tzinfo=None)
    assert len(uret([asset(daily_change_pct=-9.0, price_updated_at=naif)])) == 1


def test_iso_metin_damgasi_ayristirilir():
    ham = SIMDI.isoformat()
    assert len(uret([asset(daily_change_pct=-9.0, price_updated_at=ham)])) == 1


# --- Guven, esik ve zarf --------------------------------------------------


def test_guven_sifir_bir_araligina_sikistirilir():
    """Ham skor formulu teorik olarak 1'i asabilir; kirpma sozlesmeyi
    korur."""
    for s in uret([taze(daily_change_pct=-50.0), taze(symbol="X", yearly_change_pct=200.0)]):
        assert 0.0 <= s["confidence"] <= 1.0


def test_dusus_siddetlendikce_guven_artar():
    (hafif,) = uret([taze(daily_change_pct=-5.5)])
    (agir,) = uret([taze(daily_change_pct=-12.0)])
    assert agir["confidence"] > hafif["confidence"]


def test_esik_alti_sinyal_de_donulur_ama_yayinlanmaz():
    """D-02: esigin altinda kalan sinyal ic kayda alinir - motorun neyi
    neden eledigi izlenebilir kalir."""
    (s,) = uret([taze(daily_change_pct=-5.1)], threshold=0.99)
    assert s["published"] is False
    assert "esik" in s["suppressed_reason"]


def test_esik_ustu_sinyalde_bastirma_nedeni_bos_kalir():
    (s,) = uret([taze(daily_change_pct=-9.0)], threshold=0.1)
    assert s["published"] is True
    assert s["suppressed_reason"] is None


def test_gerekce_en_fazla_bes_madde_tasir():
    """FR-AUT-003."""
    for s in uret([taze(daily_change_pct=-9.0), taze(symbol="X", yearly_change_pct=25.0)]):
        assert 0 < len(s["rationale"]) <= 5


def test_kanit_alani_karari_veren_girdileri_tasir():
    """Aciklanabilirlik ucu (UC-18) bu alandan beslenir."""
    (s,) = uret([taze(daily_change_pct=-7.5, weekly_change_pct=3.0, yearly_change_pct=12.0)])
    assert s["evidence"]["daily_change_pct"] == -7.5
    assert s["evidence"]["weekly_change_pct"] == 3.0
    assert s["evidence"]["price_as_of"]


def test_son_gecerlilik_ttl_kadar_ileridedir():
    (s,) = uret([taze(daily_change_pct=-9.0)], ttl=90)
    assert (s["expires_at"] - SIMDI).total_seconds() == 90 * 60


def test_referans_fiyat_varligin_o_anki_fiyatidir():
    (s,) = uret([taze(current_price=412.5, daily_change_pct=-9.0)])
    assert s["reference_price"] == 412.5


def test_ayni_girdi_ayni_ciktiyi_uretir():
    """Deterministiklik sozlesmesi - aciklanabilirligin temeli."""
    girdi = [taze(daily_change_pct=-7.0), taze(symbol="X", yearly_change_pct=30.0)]
    assert uret(girdi) == uret(girdi)


def test_metinsel_yuzdeler_de_okunur():
    """Repo satirlari Decimal/str donebiliyor."""
    (s,) = uret([taze(daily_change_pct="-6.5")])
    assert s["rule_code"] == "SHARP_DROP"


def test_bozuk_yuzde_degeri_sifir_sayilir():
    """Cozulemeyen deger kurali tetiklememeli, cokme de uretmemeli."""
    assert uret([taze(daily_change_pct="yok", weekly_change_pct=None)]) == []


# --- Kural adlari ---------------------------------------------------------


@pytest.mark.parametrize("kod", sorted(KURAL_ADLARI))
def test_her_kural_kodunun_turkce_adi_vardir(kod):
    """Kod arayuzde HAM gosterilmez: "PULLBACK_IN_UPTREND" kullaniciya
    hicbir sey anlatmaz."""
    assert kural_adi(kod) != kod


def test_bilinmeyen_kod_kendisiyle_doner():
    assert kural_adi("YENI_KURAL") == "YENI_KURAL"


def test_uretilen_her_kural_kodunun_adi_tanimlidir():
    """Motor bir kod uretip `KURAL_ADLARI`'na eklemeyi unutursa arayuz ham
    kod gosterir - bu test o bosluğu yakalar."""
    girdiler = [
        taze(daily_change_pct=-9.0),
        taze(symbol="B", weekly_change_pct=15.0),
        taze(symbol="C", yearly_change_pct=20.0, weekly_change_pct=-5.0),
        taze(symbol="D", yearly_change_pct=18.0, weekly_change_pct=2.0),
    ]
    kodlar = {s["rule_code"] for s in uret(girdiler)}
    assert kodlar == set(KURAL_ADLARI)
