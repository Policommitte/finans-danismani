# -*- coding: utf-8 -*-
"""Tahmin katmani testleri.

⚠️ MODEL CAGRISI YAPILMAZ. `torch`+`timesfm` agir/opsiyonel bagimliliklardir
ve CI'da kurulu OLMAYABILIR; testler `model.ham_tahmin`'i fake bir cikti ile
degistirir. Boylece IS MANTIGI (shrinkage, TL drift, band kaydirma, portfoy
toplama) modelden BAGIMSIZ dogrulanir - zaten kirilgan olan kisim odur,
modelin kendisi degil.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from app.config import settings
from app.forecast import engine
from app.forecast.types import Tahmin, TahminNoktasi


@pytest.fixture
def sahte_model(monkeypatch):
    """`ham_tahmin`'i sabit bir cikti ile degistirir: medyan = son*1.10.

    Yani model "1 ay sonra %10 artis" diyor. Shrinkage'in bu iddiayi ne
    kadar kirptigi boylece TAM OLARAK olculebilir.
    """

    def fake(kapanislar, ufuk):
        son = float(kapanislar[-1])
        medyan = np.linspace(son * 1.005, son * 1.10, ufuk)
        return medyan, medyan * 0.90, medyan * 1.10

    monkeypatch.setattr(engine.tahmin_modeli, "ham_tahmin", fake)
    monkeypatch.setattr(engine.tahmin_modeli, "yuklu_mu", lambda: True)


@pytest.fixture
def duz_seri() -> list[float]:
    """Trendsiz seri - drift teriminin sifira yakin olmasi beklenir."""
    return [100.0] * 200


def _tahmin(seri, kategori="", sembol="TEST") -> Tahmin:
    return engine.tahmin_uret(sembol, seri, date(2026, 9, 1), kategori)


# ---------------------------------------------------------------------------
# Shrinkage
# ---------------------------------------------------------------------------


def test_shrinkage_model_iddiasini_kirpar(sahte_model, duz_seri, monkeypatch):
    """Model %10 artis diyor; agirlik 0.30 ise sonuc ~%3 olmali.

    OLCUME DAYALI KARAR: ham modele tam guvenmek (agirlik 1.0) backtest'te
    hatayi %7,06'dan %7,49'a CIKARIYORDU. Bu test o kararin kodda gercekten
    uygulandigini garanti eder.
    """
    monkeypatch.setattr(settings, "forecast_model_weight", 0.30)

    t = _tahmin(duz_seri)
    son_nokta = t.noktalar[-1].deger

    # 0.30*110 + 0.70*100 = 103
    assert son_nokta == pytest.approx(103.0, rel=0.01)


def test_agirlik_sifir_naive_uretir(sahte_model, duz_seri, monkeypatch):
    """Agirlik 0 -> tahmin duz cizgi (naive). Ozelligi 'kapatmadan' etkisizlestirir."""
    monkeypatch.setattr(settings, "forecast_model_weight", 0.0)

    t = _tahmin(duz_seri)

    assert all(n.deger == pytest.approx(100.0) for n in t.noktalar)


# ---------------------------------------------------------------------------
# TL drift
# ---------------------------------------------------------------------------


def test_tl_bazli_kategoride_drift_uygulanir(sahte_model, monkeypatch):
    """TL bazli varlikta referans son fiyat DEGIL, drift olmali.

    Olculdu: dovizde drift naive'in hatasini %1,54'ten %0,79'a indirdi.
    """
    monkeypatch.setattr(settings, "forecast_model_weight", 0.0)  # sadece referansi gor
    monkeypatch.setattr(settings, "forecast_drift_categories", "Döviz (Fiat)")

    # Gunde ~%0,1 artan seri
    artan = [100.0 * (1.001**i) for i in range(200)]

    driftli = _tahmin(artan, kategori="Döviz (Fiat)")
    driftsiz = _tahmin(artan, kategori="USA Hisse")

    # Drift'li olan YUKARI gitmeli, driftsiz DUZ kalmali
    assert driftli.noktalar[-1].deger > driftli.son_fiyat * 1.01
    assert driftsiz.noktalar[-1].deger == pytest.approx(driftsiz.son_fiyat)


def test_drift_kategorileri_ayardan_okunur(monkeypatch):
    monkeypatch.setattr(settings, "forecast_drift_categories", "A, B ,C")
    assert engine.drift_kategorileri() == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Band kaydirma
# ---------------------------------------------------------------------------


def test_nokta_her_zaman_bandin_icinde(sahte_model, duz_seri, monkeypatch):
    """REGRESYON KORUMASI.

    Nokta tahmini shrinkage ile referansa cekilir ama band modelin HAM
    kuantillerinden gelir. Band kaydirilmazsa cizgi bandin ORTASINDA
    KALMAZ - kullanici bunu gorsel bir hata olarak algilar.
    """
    monkeypatch.setattr(settings, "forecast_model_weight", 0.30)

    t = _tahmin(duz_seri)

    for n in t.noktalar:
        assert n.alt <= n.deger <= n.ust, f"{n.tarih}: nokta bandin disinda"


def test_band_genisligi_shrinkage_ile_degismez(sahte_model, duz_seri, monkeypatch):
    """Kaydirma bandi TASIR, DARALTMAZ - kalibre edilmis olan genisliktir.

    Olculdu: kaydirma kapsami bozmadi (%77,2 -> %77,0).
    """
    monkeypatch.setattr(settings, "forecast_model_weight", 1.0)
    genis_ham = [n.ust - n.alt for n in _tahmin(duz_seri).noktalar]

    monkeypatch.setattr(settings, "forecast_model_weight", 0.30)
    genis_shrunk = [n.ust - n.alt for n in _tahmin(duz_seri).noktalar]

    assert genis_ham == pytest.approx(genis_shrunk, rel=1e-9)


def test_alt_sinir_negatife_dusmez(sahte_model, monkeypatch):
    """Fiyat negatif olamaz; cok oynak seride alt sinir 0'in altina inebilirdi."""
    monkeypatch.setattr(settings, "forecast_model_weight", 0.30)

    def cok_genis(kapanislar, ufuk):
        son = float(kapanislar[-1])
        medyan = np.full(ufuk, son)
        return medyan, medyan * -5.0, medyan * 5.0  # absurt genis band

    monkeypatch.setattr(engine.tahmin_modeli, "ham_tahmin", cok_genis)

    t = _tahmin([50.0] * 200)

    assert all(n.alt >= 0.0 for n in t.noktalar)


# ---------------------------------------------------------------------------
# Takvim
# ---------------------------------------------------------------------------


def test_hafta_sonlari_atlanir(sahte_model, duz_seri):
    t = _tahmin(duz_seri)

    for n in t.noktalar:
        assert date.fromisoformat(n.tarih).weekday() < 5, f"{n.tarih} hafta sonu"


def test_tahmin_son_gozlemin_ERTESINDEN_baslar(sahte_model, duz_seri):
    """Grafikte kesikli cizgi son gercek noktadan devam etmeli."""
    t = _tahmin(duz_seri)

    assert date.fromisoformat(t.noktalar[0].tarih) > date(2026, 9, 1)
    assert len(t.noktalar) == settings.forecast_horizon_days


# ---------------------------------------------------------------------------
# Guvenli kapanma
# ---------------------------------------------------------------------------


def test_model_yoksa_none_doner(monkeypatch, duz_seri):
    """Ozellik kapaliysa SESSIZCE None - uygulama calismaya devam eder."""
    monkeypatch.setattr(engine.tahmin_modeli, "yuklu_mu", lambda: False)

    assert _tahmin(duz_seri) is None


def test_yetersiz_gecmiste_none_doner(sahte_model):
    assert _tahmin([100.0] * 10) is None


def test_model_cokerse_none_doner(sahte_model, duz_seri, monkeypatch):
    """Model istisnasi grafigi DUSURMEMELI."""

    def patla(kapanislar, ufuk):
        raise RuntimeError("model coktu")

    monkeypatch.setattr(engine.tahmin_modeli, "ham_tahmin", patla)

    assert _tahmin(duz_seri) is None


# ---------------------------------------------------------------------------
# Portfoy toplama - KORELASYON
# ---------------------------------------------------------------------------


def _basit_tahmin(son: float, alt_pay: float, ust_pay: float) -> Tahmin:
    return Tahmin(
        sembol="X",
        son_fiyat=son,
        son_tarih="2026-09-01",
        noktalar=[
            TahminNoktasi(tarih="2026-09-02", deger=son, alt=son - alt_pay, ust=son + ust_pay)
        ],
    )


def test_portfoy_nokta_tahminleri_TOPLANIR():
    """Beklenen deger DOGRUSALDIR: toplamin beklentisi = beklentilerin toplami."""
    a = _basit_tahmin(100.0, 10.0, 10.0)
    b = _basit_tahmin(50.0, 5.0, 5.0)

    p = engine.portfoy_tahmini_birlestir(
        [(a, 2.0), (b, 4.0)], nakit=1000.0, son_tarih=date(2026, 9, 1)
    )

    # 100*2 + 50*4 + 1000 = 1400
    assert p.noktalar[0].deger == pytest.approx(1400.0)
    assert p.son_fiyat == pytest.approx(1400.0)


def test_portfoy_bandi_TOPLANMAZ_riski_abartmaz():
    """⚠️ EN KRITIK PORTFOY TESTI.

    Bantlari duz toplamak "TUM varliklar AYNI ANDA en kotu senaryoyu yasar"
    demektir - varliklar mukemmel korelasyonlu olsaydi dogru olurdu, degiller.
    Riski CIDDI SEKILDE abartirdi. Karelerin toplaminin karekoku kullanilir.
    """
    a = _basit_tahmin(100.0, 10.0, 10.0)  # yari bant 10
    b = _basit_tahmin(100.0, 10.0, 10.0)  # yari bant 10

    p = engine.portfoy_tahmini_birlestir(
        [(a, 1.0), (b, 1.0)], nakit=0.0, son_tarih=date(2026, 9, 1)
    )

    yari = (p.noktalar[0].ust - p.noktalar[0].alt) / 2
    # Duz toplam 20 OLURDU; bagimsizlik varsayimiyla sqrt(10²+10²)=14,142...
    # Tolerans 0.01: portfoy degerleri kurusa (2 ondalik) yuvarlanir.
    assert yari == pytest.approx(np.sqrt(200.0), abs=0.01)
    assert yari < 20.0, "bant duz toplanmis - risk abartiliyor"


def test_portfoy_bos_listede_none_doner():
    assert engine.portfoy_tahmini_birlestir([], nakit=0.0, son_tarih=date(2026, 9, 1)) is None


# ---------------------------------------------------------------------------
# Rota: sembol sorgu parametresi (yol parcasi degil)
#
# `/forecast/{symbol}` iken `USD/TRY` 404 aliyordu: frontend `USD%2FTRY`
# gonderse de sunucu yolu yonlendirmeden once cozuyor. Kardes uclar
# (`/candles?symbol=`) zaten sorgu parametresi kullaniyor.
# ---------------------------------------------------------------------------


def test_forecast_route_accepts_symbol_with_slash(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.routes import market as market_routes
    from app.auth.deps import get_current_user
    from app.main import app

    gorulen: list[str] = []

    async def fake_forecast(symbol: str):
        gorulen.append(symbol)
        return None

    monkeypatch.setattr(market_routes.forecast_service, "varlik_tahmini", fake_forecast)
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "role": "customer"}
    try:
        client = TestClient(app)
        yanit = client.get("/api/market/forecast", params={"symbol": "USD/TRY"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert yanit.status_code == 200, yanit.text
    assert gorulen == ["USD/TRY"]
