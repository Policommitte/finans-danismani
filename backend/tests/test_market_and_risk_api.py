"""Piyasa ve risk uclarinin testleri."""

from datetime import date

import pytest

from app.services.risk import risk_profili_hesapla

# ---------------------------------------------------------------------------
# Piyasa
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_varlik_listesi_doner(client, auth):
    govde = client.get("/api/market/assets", headers=auth).json()

    semboller = {v["symbol"] for v in govde["items"]}
    assert {"THYAO", "BTC", "USD/TRY"} <= semboller


@pytest.mark.db
def test_varlik_listesi_kategoriye_gore_filtrelenir(client, auth):
    govde = client.get("/api/market/assets?category=CRYPTO", headers=auth).json()

    assert govde["items"]
    assert all(v["asset_class"] == "CRYPTO" for v in govde["items"])


@pytest.mark.db
def test_fiyat_gecmisi_istenen_gun_sayisinca_nokta_doner(client, auth):
    govde = client.get("/api/market/history?symbol=THYAO&days=10", headers=auth).json()

    assert govde["symbol"] == "THYAO"
    assert govde["points"]
    assert all(nokta["price"] > 0 for nokta in govde["points"])
    # Nokta SAYISI seed'in cozunurluguna bagli; sinanan sey istenen ARALIK.
    ilk = date.fromisoformat(govde["points"][0]["ts"][:10])
    son = date.fromisoformat(govde["points"][-1]["ts"][:10])
    assert (son - ilk).days <= 10


@pytest.mark.db
def test_fiyat_gecmisi_kronolojik_sirali(client, auth):
    """PriceChart soldan saga cizer; seri eskiden yeniye gelmeli."""
    noktalar = client.get("/api/market/history?symbol=THYAO&days=5", headers=auth).json()["points"]

    zamanlar = [nokta["ts"] for nokta in noktalar]
    assert zamanlar == sorted(zamanlar)


@pytest.mark.db
def test_mum_endpointi_ohlc_serisi_doner(client, auth):
    yanit = client.get(
        "/api/market/candles?symbol=THYAO&interval=1d&range=1m",
        headers=auth,
    )

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["symbol"] == "THYAO"
    assert govde["interval"] == "1d"
    assert govde["range"] == "1m"
    assert govde["candles"]
    assert {"time", "open", "high", "low", "close", "volume"} == set(
        govde["candles"][0]
    )


@pytest.mark.db
def test_bilinmeyen_sembol_404_doner(client, auth):
    yanit = client.get("/api/market/history?symbol=YOKBOYLE", headers=auth)

    assert yanit.status_code == 404
    assert yanit.json()["error"]["code"] == "not_found"


@pytest.mark.db
def test_arama_ilgili_dokumani_bulur(client, auth):
    yanit = client.post(
        "/api/market/search", headers=auth, json={"query": "THYAO net kar yolcu doluluk"}
    )

    assert yanit.status_code == 200
    sonuclar = yanit.json()["items"]
    assert sonuclar
    # `sirket` unvani tasir ("Turk Hava Yollari"), `symbol` kodu ("THYAO").
    assert any(s["symbol"] == "THYAO" for s in sonuclar)


@pytest.mark.db
def test_arama_sirket_filtresine_uyar(client, auth):
    """Filtre SEMBOL ile de calismali: ajan sorgudan sembol cikarir, dokumanda
    unvan yazilidir. Yalnizca unvana bakilsaydi filtreli arama bos donerdi."""
    sonuclar = client.post(
        "/api/market/search", headers=auth, json={"query": "maliyet", "sirket": "SASA"}
    ).json()["items"]

    assert sonuclar
    assert all(s["symbol"] == "SASA" for s in sonuclar)


@pytest.mark.db
def test_arama_cok_kisa_sorguyu_reddeder(client, auth):
    yanit = client.post("/api/market/search", headers=auth, json={"query": "a"})

    assert yanit.status_code == 422


# ---------------------------------------------------------------------------
# Risk - skor DETERMINISTIK ve tek kaynakli
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_risk_profili_bilesenleriyle_doner(client, auth):
    govde = client.get("/api/risk/profile", headers=auth).json()

    assert 0 < govde["risk_score"] <= 100
    assert govde["risk_level"] in {"dusuk", "orta", "yuksek", "cok yuksek"}
    assert govde["risk_tolerance"] == "HIGH"
    assert set(govde["components"]) == {
        "concentration",
        "asset_type",
        "volatility",
        "single_position",
    }
    assert govde["reasons"]


@pytest.mark.db
def test_risk_skoru_ayni_girdide_ayni_sonucu_verir(client, auth):
    """Deterministik: iki cagri arasinda LLM ya da rastgelelik yok."""
    birinci = client.get("/api/risk/profile", headers=auth).json()
    ikinci = client.get("/api/risk/profile", headers=auth).json()

    assert birinci == ikinci


def test_bos_portfoyde_skor_hesaplanamadi_doner():
    sonuc = risk_profili_hesapla(holdings=[], allocation=[])

    assert sonuc["risk_score"] == 0
    assert sonuc["risk_level"] == "hesaplanamadi"
    assert sonuc["holding_count"] == 0


def test_tek_kripto_varlik_dengeli_portfoyden_riskli():
    kripto = risk_profili_hesapla(
        holdings=[{"symbol": "BTC", "asset_class": "CRYPTO", "market_value_try": 100_000}],
        allocation=[{"asset_class": "CRYPTO", "class_pct": 100}],
    )
    dengeli = risk_profili_hesapla(
        holdings=[
            {"symbol": "TR10Y", "asset_class": "BOND", "market_value_try": 25_000},
            {"symbol": "GRAM_ALTIN", "asset_class": "GOLD", "market_value_try": 25_000},
            {"symbol": "THYAO", "asset_class": "STOCK", "market_value_try": 25_000},
            {"symbol": "USD/TRY", "asset_class": "FOREX", "market_value_try": 25_000},
        ],
        allocation=[
            {"asset_class": "BOND", "class_pct": 25},
            {"asset_class": "GOLD", "class_pct": 25},
            {"asset_class": "STOCK", "class_pct": 25},
            {"asset_class": "FOREX", "class_pct": 25},
        ],
    )

    assert kripto["risk_score"] > dengeli["risk_score"]
    assert kripto["components"]["concentration"] > dengeli["components"]["concentration"]


def test_oynaklik_skoru_yukseltir():
    varliklar = [{"symbol": "BTC", "asset_class": "CRYPTO", "market_value_try": 100_000}]
    dagilim = [{"asset_class": "CRYPTO", "class_pct": 100}]

    olculmemis = risk_profili_hesapla(varliklar, dagilim)
    oynak = risk_profili_hesapla(varliklar, dagilim, volatility_by_symbol={"BTC": 9.0})

    assert oynak["risk_score"] > olculmemis["risk_score"]
    assert oynak["avg_volatility_pct"] == 9.0


@pytest.mark.parametrize("tolerans", ["LOW", "MEDIUM", "HIGH"])
def test_tamamen_kripto_portfoy_her_toleransin_ustunde(tolerans):
    """%100 kripto skoru 80'in uzerine cikar; en yuksek tolerans bile asilir."""
    sonuc = risk_profili_hesapla(
        holdings=[{"symbol": "BTC", "asset_class": "CRYPTO", "market_value_try": 100_000}],
        allocation=[{"asset_class": "CRYPTO", "class_pct": 100}],
        risk_tolerance=tolerans,
    )

    assert sonuc["tolerance_alignment"] == "tolerans ustu"
    assert sonuc["suggestions"]


def test_dengeli_portfoy_dusuk_toleransla_uyumlu():
    sonuc = risk_profili_hesapla(
        holdings=[
            {"symbol": "TR10Y", "asset_class": "BOND", "market_value_try": 40_000},
            {"symbol": "GRAM_ALTIN", "asset_class": "GOLD", "market_value_try": 30_000},
            {"symbol": "USD/TRY", "asset_class": "FOREX", "market_value_try": 30_000},
        ],
        allocation=[
            {"asset_class": "BOND", "class_pct": 40},
            {"asset_class": "GOLD", "class_pct": 30},
            {"asset_class": "FOREX", "class_pct": 30},
        ],
        risk_tolerance="LOW",
    )

    assert sonuc["risk_level"] == "dusuk"
    assert sonuc["tolerance_alignment"] in {"uyumlu", "tolerans alti"}


def test_tolerans_bilinmiyorsa_karsilastirma_yapilmaz():
    sonuc = risk_profili_hesapla(
        holdings=[{"symbol": "THYAO", "asset_class": "STOCK", "market_value_try": 10_000}],
        allocation=[{"asset_class": "STOCK", "class_pct": 100}],
    )

    assert sonuc["tolerance_alignment"] == "bilinmiyor"
