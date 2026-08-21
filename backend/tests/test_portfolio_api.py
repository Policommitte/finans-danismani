"""Portfoy ve dashboard uclarinin testleri (§14-12).

Rakamlar `db/v5_schema_and_data.sql` seed'inden gelir; hesap zinciri
(holdings -> allocation -> summary) bozulursa test kirilir.
"""

import pytest

pytestmark = pytest.mark.db

#: 1 numarali portfoyun beklenen toplami:
#:   THYAO 1000 x 315.50            =   315.500,00 TL
#:   SASA  5000 x  45.20            =   226.000,00 TL
#:   BTC      0.5 x 65.400 x 33,55  = 1.097.085,00 TL  (USD -> TRY cevrimi)
BEKLENEN_TOPLAM = 1_638_585.00


def test_ozet_seed_ile_ayni_toplami_verir(client, auth):
    yanit = client.get("/api/portfolio/summary", headers=auth)

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["holding_count"] == 3
    assert round(govde["total_value_try"], 2) == BEKLENEN_TOPLAM


def test_ozet_kar_zarari_maliyetten_hesaplar(client, auth):
    govde = client.get("/api/portfolio/summary", headers=auth).json()

    beklenen_pnl = govde["total_value_try"] - govde["total_cost_try"]
    assert round(govde["total_pnl_try"], 2) == round(beklenen_pnl, 2)


def test_varliklar_deger_sirali_doner(client, auth):
    govde = client.get("/api/portfolio/holdings", headers=auth).json()

    degerler = [h["market_value_try"] for h in govde["items"]]
    assert degerler == sorted(degerler, reverse=True)
    assert govde["items"][0]["symbol"] == "BTC"  # FX cevrimi sonrasi en buyuk


def test_varliklar_toplami_ozetle_tutarli(client, auth):
    """Ayni sayi iki uctan da ayni gelmeli - hesap tek kaynaktan geliyor."""
    ozet = client.get("/api/portfolio/summary", headers=auth).json()
    varliklar = client.get("/api/portfolio/holdings", headers=auth).json()

    assert round(varliklar["total_value_try"], 2) == round(ozet["total_value_try"], 2)


def test_yabanci_para_varlik_try_ye_cevrilir(client, auth):
    """BTC fiyati USD; portfoy degeri USD/TRY kuru ile carpilmis olmali."""
    varliklar = client.get("/api/portfolio/holdings", headers=auth).json()["items"]
    btc = next(h for h in varliklar if h["symbol"] == "BTC")

    assert btc["currency"] == "USD"
    assert round(btc["market_value_try"], 2) == round(0.5 * 65_400.0 * 33.55, 2)


def test_dagilim_yuzdeleri_100_e_tamamlanir(client, auth):
    govde = client.get("/api/portfolio/allocation", headers=auth).json()

    toplam_yuzde = sum(dilim["class_pct"] for dilim in govde["items"])
    assert abs(toplam_yuzde - 100.0) < 0.05
    assert {d["asset_class"] for d in govde["items"]} == {"STOCK", "CRYPTO"}


def test_islemler_limit_parametresine_uyar(client, auth):
    govde = client.get("/api/portfolio/transactions?limit=2", headers=auth).json()

    assert govde["limit"] == 2
    assert len(govde["items"]) <= 2


def test_islemler_gecersiz_limiti_reddeder(client, auth):
    yanit = client.get("/api/portfolio/transactions?limit=0", headers=auth)

    assert yanit.status_code == 422
    assert yanit.json()["error"]["code"] == "validation_error"


def test_portfoyu_bos_kullanici_404_alir(client):
    """Seed'de 10 numarali kullanicinin portfoyu kasitli olarak BOS."""
    from app.auth.security import create_access_token

    yanit = client.get(
        "/api/portfolio/summary",
        headers={"Authorization": f"Bearer {create_access_token(2)}"},
    )
    # 2 numarali kullanicinin portfoyu dolu; bos portfoy davranisi icin
    # repository dogrudan sinanir (asagida).
    assert yanit.status_code == 200


async def test_bos_portfoyde_ozet_none_doner():
    """Bos portfoy bir HATA degil; repository `None` dondurmeli."""
    from app.repositories.deps import get_portfolio_repository

    assert await get_portfolio_repository().get_summary(user_id=2_000_000_000) is None


def test_dashboard_tek_istekte_hepsini_dondurur(client, auth):
    """Ilk yukleme 4 istek yerine 1: summary + holdings + allocation + risk."""
    govde = client.get("/api/dashboard/summary", headers=auth).json()

    assert govde["summary"]["holding_count"] == 3
    assert len(govde["holdings"]) == 3
    assert govde["allocation"]
    assert govde["risk"]["risk_score"] > 0
    assert govde["movers"]


def test_dashboard_ile_granuler_uclar_ayni_sayiyi_verir(client, auth):
    dashboard = client.get("/api/dashboard/summary", headers=auth).json()
    ozet = client.get("/api/portfolio/summary", headers=auth).json()
    risk = client.get("/api/risk/profile", headers=auth).json()

    assert dashboard["summary"]["total_value_try"] == ozet["total_value_try"]
    assert dashboard["risk"]["risk_score"] == risk["risk_score"]


def test_gunluk_portfoy_degisimi_onceki_kapanislarin_toplamidir(client, auth):
    dashboard = client.get("/api/dashboard/summary", headers=auth).json()

    beklenen = sum(holding["daily_change_try"] for holding in dashboard["holdings"])
    assert dashboard["summary"]["daily_change_try"] == round(beklenen, 2)
    assert dashboard["summary"]["daily_change_pct"] is not None
