"""Piyasa ve risk uclarinin testleri."""

from datetime import date

import pytest

from app.services.risk import risk_profili_hesapla

# ---------------------------------------------------------------------------
# Piyasa
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_asset_list_returned(client, auth):
    govde = client.get("/api/market/assets", headers=auth).json()

    semboller = {v["symbol"] for v in govde["items"]}
    assert {"THYAO", "BTC", "USD/TRY"} <= semboller


@pytest.mark.db
def test_asset_list_filtered_by_category(client, auth):
    govde = client.get("/api/market/assets?category=CRYPTO", headers=auth).json()

    assert govde["items"]
    assert all(v["asset_class"] == "CRYPTO" for v in govde["items"])


@pytest.mark.db
def test_price_history_returns_requested_number_of_days(client, auth):
    govde = client.get("/api/market/history?symbol=THYAO&days=10", headers=auth).json()

    assert govde["symbol"] == "THYAO"
    assert govde["points"]
    assert all(nokta["price"] > 0 for nokta in govde["points"])
    # Nokta SAYISI seed'in cozunurluguna bagli; sinanan sey istenen ARALIK.
    ilk = date.fromisoformat(govde["points"][0]["ts"][:10])
    son = date.fromisoformat(govde["points"][-1]["ts"][:10])
    assert (son - ilk).days <= 10


@pytest.mark.db
def test_price_history_in_chronological_order(client, auth):
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
    assert {"time", "open", "high", "low", "close", "volume"} == set(govde["candles"][0])


@pytest.mark.db
def test_teknik_analiz_ucu_sinif_ve_gosterge_doner(client, auth):
    yanit = client.get("/api/market/technical?symbol=THYAO", headers=auth)

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["symbol"] == "THYAO"
    assert govde["interval"] == "1d"
    assert govde["sufficient"] is True
    assert govde["summary"]["label"] in {"GUCLU_AL", "AL", "NOTR", "SAT", "GUCLU_SAT"}
    assert govde["last_candle_ts"]
    assert {"key", "label", "value", "signal"} == set(govde["indicators"][0])
    assert {200} <= {ma["period"] for ma in govde["moving_averages"]}


@pytest.mark.db
def test_teknik_analiz_veri_yoksa_404_yerine_yetersiz_doner(client, auth):
    """Bos sonuc bir HATA DEGIL: frontend "veri yetersiz" gosterir."""
    yanit = client.get("/api/market/technical?symbol=YOKBOYLE", headers=auth)

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["sufficient"] is False
    assert govde["summary"] is None
    assert govde["reason"]


@pytest.mark.db
def test_unknown_symbol_returns_404(client, auth):
    yanit = client.get("/api/market/history?symbol=YOKBOYLE", headers=auth)

    assert yanit.status_code == 404
    assert yanit.json()["error"]["code"] == "not_found"


@pytest.mark.db
def test_search_finds_relevant_document(client, auth):
    yanit = client.post(
        "/api/market/search", headers=auth, json={"query": "THYAO net kar yolcu doluluk"}
    )

    assert yanit.status_code == 200
    sonuclar = yanit.json()["items"]
    assert sonuclar
    # `sirket` unvani tasir ("Turk Hava Yollari"), `symbol` kodu ("THYAO").
    assert any(s["symbol"] == "THYAO" for s in sonuclar)


@pytest.mark.db
def test_search_respects_company_filter(client, auth):
    """Filtre SEMBOL ile de calismali: ajan sorgudan sembol cikarir, dokumanda
    unvan yazilidir. Yalnizca unvana bakilsaydi filtreli arama bos donerdi."""
    sonuclar = client.post(
        "/api/market/search", headers=auth, json={"query": "maliyet", "sirket": "SASA"}
    ).json()["items"]

    assert sonuclar
    assert all(s["symbol"] == "SASA" for s in sonuclar)


@pytest.mark.db
def test_search_rejects_too_short_query(client, auth):
    yanit = client.post("/api/market/search", headers=auth, json={"query": "a"})

    assert yanit.status_code == 422


@pytest.mark.db
async def test_arama_dense_ayagi_gercekten_calisir(client, auth, monkeypatch):
    """`search_assets` artik `.search()` yerine `.hybrid_search()` cagirir (bkz.
    `app/services/market.py`) - bu test dense (embedding) ayagin bu REST
    yolunda da GERCEKTEN devrede oldugunu kanitlar, sadece "hata firlatmadi"
    degil. Ayni DOC-005 deseni:
    `test_hybrid_search.py::test_dense_ayak_gercekten_calisir`.

    Sorgu metninde ("zzqx wobble flurb nonsense") DOC-005 icerigiyle hicbir
    ORTAK kelime yoktur - BM25 boyle bir sorguda kesinlikle bos doner. DOC-005'in
    GERCEK embedding'i sahte sorgu vektoru olarak enjekte edilerek yine de
    bulunmasi, `get_rag_repository().hybrid_search(...)` cagrisinin gercekten
    calistigini kanitlar.
    """
    from sqlalchemy import text

    from app.repositories import deps
    from app.repositories.sql import SqlRagRepository
    from app.services import market

    async with deps._session_factory()() as session:
        satir = (
            await session.execute(
                text(
                    """
                    SELECT c.embedding FROM rag.chunks c
                    JOIN rag.documents d ON d.id = c.document_id
                    WHERE d.external_id = :external_id LIMIT 1
                    """
                ),
                {"external_id": "DOC-005"},
            )
        ).first()
    vektor = [float(x) for x in satir[0].strip("[]").split(",")]

    class _SahteEmbedder:
        async def embed_query(self, text: str) -> list[float]:
            return vektor

        async def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [vektor for _ in texts]

    fake_repo = SqlRagRepository(deps._session_factory(), embedder=_SahteEmbedder())
    monkeypatch.setattr(market, "get_rag_repository", lambda: fake_repo)

    yanit = client.post(
        "/api/market/search", headers=auth, json={"query": "zzqx wobble flurb nonsense"}
    )

    assert yanit.status_code == 200
    sonuclar = yanit.json()["items"]
    assert sonuclar, "dense ayak calismiyorsa sonuc bos doner"
    assert sonuclar[0]["doc_id"] == "DOC-005"


# ---------------------------------------------------------------------------
# Risk - skor DETERMINISTIK ve tek kaynakli
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_risk_profile_returned_with_components(client, auth):
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
def test_risk_score_is_deterministic(client, auth):
    """Deterministik: iki cagri arasinda LLM ya da rastgelelik yok."""
    birinci = client.get("/api/risk/profile", headers=auth).json()
    ikinci = client.get("/api/risk/profile", headers=auth).json()

    assert birinci == ikinci


def test_empty_portfolio_returns_score_unavailable():
    sonuc = risk_profili_hesapla(holdings=[], allocation=[])

    assert sonuc["risk_score"] == 0
    assert sonuc["risk_level"] == "hesaplanamadi"
    assert sonuc["holding_count"] == 0


def test_single_crypto_asset_riskier_than_balanced_portfolio():
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


def test_volatility_raises_score():
    varliklar = [{"symbol": "BTC", "asset_class": "CRYPTO", "market_value_try": 100_000}]
    dagilim = [{"asset_class": "CRYPTO", "class_pct": 100}]

    olculmemis = risk_profili_hesapla(varliklar, dagilim)
    oynak = risk_profili_hesapla(varliklar, dagilim, volatility_by_symbol={"BTC": 9.0})

    assert oynak["risk_score"] > olculmemis["risk_score"]
    assert oynak["avg_volatility_pct"] == 9.0


@pytest.mark.parametrize("tolerans", ["LOW", "MEDIUM", "HIGH"])
def test_all_crypto_portfolio_exceeds_every_tolerance(tolerans):
    """%100 kripto skoru 80'in uzerine cikar; en yuksek tolerans bile asilir."""
    sonuc = risk_profili_hesapla(
        holdings=[{"symbol": "BTC", "asset_class": "CRYPTO", "market_value_try": 100_000}],
        allocation=[{"asset_class": "CRYPTO", "class_pct": 100}],
        risk_tolerance=tolerans,
    )

    assert sonuc["tolerance_alignment"] == "tolerans ustu"
    assert sonuc["suggestions"]


def test_balanced_portfolio_matches_low_tolerance():
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


def test_no_comparison_when_tolerance_unknown():
    sonuc = risk_profili_hesapla(
        holdings=[{"symbol": "THYAO", "asset_class": "STOCK", "market_value_try": 10_000}],
        allocation=[{"asset_class": "STOCK", "class_pct": 100}],
    )

    assert sonuc["tolerance_alignment"] == "bilinmiyor"
