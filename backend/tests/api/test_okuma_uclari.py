"""Salt okunan REST uclarinin sozlesmesi.

Bu dosya "veri ne diyor" degil "ARAYUZ ne bekliyor" sorusunu sinar:
zorunlu alanlar var mi, tip dogru mu, kimlik dogrulama zorunlu mu, kapali
bir ozellik hata mi yoksa `null` mi donuyor.

Testler BELLEK ICI depoya konusur (bkz. conftest); iddialar bu yuzden sabit
sayilar uzerine degil, SOZLESME uzerine kurulur.
"""

from __future__ import annotations

import pytest

#: Kimlik dogrulamasi ZORUNLU olan TUM parametresiz GET uclari (401 kontrolu).
#: Liste elle degil, `test_korumali_uc_listesi_uygulamayla_SENKRON` ile
#: OpenAPI semasina karsi dogrulanir.
KORUMALI_GET = [
    "/api/auth/me",
    "/api/contest/leaderboard",
    "/api/contest/today",
    "/api/contest/wallet",
    "/api/contest/wallet/history",
    "/api/conversations",
    "/api/dashboard/summary",
    "/api/economic-calendar",
    "/api/leads/autonomous-queue",
    "/api/leads/bsd-queue",
    "/api/leads/excluded",
    "/api/market/assets",
    "/api/market/candles",
    "/api/market/forecast",
    "/api/market/forecast-portfolio",
    "/api/market/history",
    "/api/market/news",
    "/api/market/ohlc",
    "/api/market/photo",
    "/api/market/quick-analysis",
    "/api/market/technical",
    "/api/oneriler",
    "/api/oneriler/ayarlar",
    "/api/portfolio/allocation",
    "/api/portfolio/holdings",
    "/api/portfolio/performance",
    "/api/portfolio/performance-v2",
    "/api/portfolio/summary",
    "/api/portfolio/transactions",
    "/api/risk/profile",
    "/api/trading/account",
    "/api/trading/orders",
]

#: `KORUMALI_GET`'in ALT KUMESI: zorunlu sorgu parametresi ISTEMEYEN ve
#: musteri roluyle 200 donen uclar - duman testi bunlari kullanir.
#: Disarida kalanlar ya zorunlu parametre ister (`/market/history?symbol=`)
#: ya da DANISMAN rolu ister (`/leads/*`); ikisi de 200 DONMEZ ve bu
#: beklenen davranistir.
TOKENLA_200_DONEN = [
    "/api/auth/me",
    "/api/contest/leaderboard",
    "/api/contest/today",
    "/api/contest/wallet",
    "/api/contest/wallet/history",
    "/api/conversations",
    "/api/dashboard/summary",
    "/api/economic-calendar",
    "/api/market/assets",
    "/api/market/news",
    "/api/oneriler",
    "/api/oneriler/ayarlar",
    "/api/portfolio/allocation",
    "/api/portfolio/holdings",
    "/api/portfolio/performance",
    "/api/portfolio/performance-v2",
    "/api/portfolio/summary",
    "/api/portfolio/transactions",
    "/api/risk/profile",
    "/api/trading/account",
    "/api/trading/orders",
]


def test_korumali_uc_listesi_uygulamayla_SENKRON():
    """Liste elle tutuluyor ve elle tutulan her liste bayatlar.

    OpenAPI semasi kaynagin KENDISIDIR: guvenlik semasi tasiyan, parametresiz
    her GET ucu listede olmali. Yeni bir uc eklenip listeye yazilmazsa bu
    test kirmizi yanar - `KORUMALI_GET` bir daha sessizce geride kalmaz.
    (Migrasyon sirasinda 13 uc listede yoktu; kimlik dogrulamasi
    zorunlulugu hic sinanmiyordu.)
    """
    from app.main import app

    sema = app.openapi()
    korumali = {
        yol
        for yol, ops in sema["paths"].items()
        if "get" in ops
        and yol.startswith("/api/")
        and "{" not in yol
        and ops["get"].get("security")
    }

    assert korumali - set(KORUMALI_GET) == set(), "listeye yazilmamis korumali uc var"
    assert set(TOKENLA_200_DONEN) <= set(KORUMALI_GET), "alt kume disina cikmis yol var"


@pytest.mark.parametrize("yol", KORUMALI_GET)
def test_korumali_uclar_token_ister(client, yol):
    """Yeni bir uc eklenip listeye yazilmazsa bu test onu gormez - liste
    `app/main.py`'deki router'larla birlikte guncellenmelidir."""
    assert client.get(yol).status_code == 401


@pytest.mark.parametrize("yol", TOKENLA_200_DONEN)
def test_korumali_uclar_gecerli_token_ile_200_doner(client, auth, yol):
    """Duman testi: rota kurulumu, sema uyumu ve servis zinciri ayakta mi."""
    assert client.get(yol, headers=auth).status_code == 200


# --- Saglik ---------------------------------------------------------------


def test_health_kimlik_dogrulamasi_ISTEMEZ(client):
    """Izleme araclari icin acik."""
    assert client.get("/health").status_code == 200


def test_health_hangi_veri_kaynaginin_bagli_oldugunu_SOYLER(client):
    """Yedekte oldugumuz GIZLENMEZ."""
    govde = client.get("/health").json()
    assert govde["status"] == "ok"
    assert govde["data_source"] == "in-memory"
    assert govde["notifications"]


def test_db_saglik_ucu_tanimsiz_ile_erisilemez_durumunu_AYIRT_EDER(client):
    """ "DB yok" bir HATA DEGILDIR; izleme araci ikisini karistirmamali."""
    govde = client.get("/health/db").json()
    assert govde["status"] == "disabled"
    assert "DATABASE_URL" in govde["detail"]


# --- Public ---------------------------------------------------------------


def test_public_seridi_token_istemez(client):
    assert client.get("/api/public/market-ticker").status_code == 200


def test_public_seridi_yalnizca_fiyati_olan_varliklari_listeler(client):
    for oge in client.get("/api/public/market-ticker").json()["items"]:
        assert oge["value"] > 0
        assert oge["source"] == "database"
        assert oge["label"]


def test_landing_onizlemesi_token_istemez_ve_demo_portfoy_doner(client):
    govde = client.get("/api/public/landing-preview").json()
    assert govde["holding_count"] > 0
    assert govde["total_value_try"] > 0
    assert len(govde["allocation"]) > 0
    assert sum(a["class_pct"] for a in govde["allocation"]) == pytest.approx(100, abs=1.5)


def test_landing_onizlemesi_aktif_veritabanindan_BAGIMSIZDIR(client):
    """Sabit demo verisinden uretilir - DB durumu ne olursa olsun ayni."""
    assert client.get("/api/public/landing-preview").json() == (
        client.get("/api/public/landing-preview").json()
    )


# --- Portfoy --------------------------------------------------------------


def test_portfoy_ozeti_zorunlu_alanlari_tasir(client, auth):
    govde = client.get("/api/portfolio/summary", headers=auth).json()
    assert {"total_value_try", "holding_count"} <= set(govde)
    assert govde["holding_count"] >= 0


def test_varliklar_deger_sirali_doner(client, auth):
    """⚠️ SIRA SOZLESMEDIR: risk servisi oynakligi olcerken ilk N varligi
    alir (`MAX_VOLATILITY_LOOKUPS`) ve MCP tool'u ayni siralamayi kullanir.
    Sira degisirse iki taraf FARKLI varliklari olcup farkli skor uretir."""
    degerler = [
        h["market_value_try"]
        for h in client.get("/api/portfolio/holdings", headers=auth).json()["items"]
    ]
    assert degerler == sorted(degerler, reverse=True)


def test_dagilim_yuzdeleri_yuze_yakin_toplanir(client, auth):
    yuzdeler = [
        a["class_pct"]
        for a in client.get("/api/portfolio/allocation", headers=auth).json()["items"]
    ]
    assert sum(yuzdeler) == pytest.approx(100, abs=1.5)


def test_islem_limiti_uygulanir(client, auth):
    govde = client.get("/api/portfolio/transactions", params={"limit": 2}, headers=auth).json()
    assert len(govde["items"]) <= 2


# --- Risk -----------------------------------------------------------------


def test_risk_profili_skor_ve_gerekce_dondurur(client, auth):
    govde = client.get("/api/risk/profile", headers=auth).json()
    assert 0 <= govde["risk_score"] <= 100
    assert govde["risk_level"]
    assert isinstance(govde["reasons"], list)


def test_dashboard_riski_ile_risk_ucu_AYNI_skoru_verir(client, auth):
    """27 Agustos 2026 regresyonu: dashboard oynakligi HIC olcmuyordu ve
    kullanici ekranda 70, sohbette 77 goruyordu."""
    dashboard = client.get("/api/dashboard/summary", headers=auth).json()
    risk = client.get("/api/risk/profile", headers=auth).json()
    assert dashboard["risk"]["risk_score"] == risk["risk_score"]


# --- Piyasa ---------------------------------------------------------------


def test_varlik_listesi_kategoriye_gore_suzulur(client, auth):
    tumu = client.get("/api/market/assets", headers=auth).json()["items"]
    kripto = client.get("/api/market/assets", params={"category": "CRYPTO"}, headers=auth).json()[
        "items"
    ]
    assert 0 < len(kripto) < len(tumu)
    assert all(a["asset_class"] == "CRYPTO" for a in kripto)


def test_bilinmeyen_kategori_bos_liste_doner(client, auth):
    """404 DEGIL: bos filtre sonucu gecerli bir yanittir."""
    yanit = client.get("/api/market/assets", params={"category": "YOK"}, headers=auth)
    assert yanit.status_code == 200
    assert yanit.json()["items"] == []


@pytest.fixture
def piyasa_gecmisi(monkeypatch):
    """`/api/market/history` ve `/api/market/candles` icin sahte depo.

    NEDEN GEREKLI: bellek ici depo bu iki metot icin BILEREK bos liste
    doner (`in_memory.py::get_history` - "dogrulanmis fiyat zaman serisi
    tutulmaz"). Yani bu uclar bellek ici yolda HER ZAMAN 404/bos verir ve
    sozlesmeleri hic sinanmazdi.

    ⚠️ Yamalanan yer `app.services.market.get_market_repository`, `deps`
    DEGIL: servis modulu ismi `from ... import` ile KENDI ad alanina
    baglamistir (`app/services/market.py:10`), kaynagi yamalamak servisi
    etkilemez.

    Bilinmeyen sembol icin bos liste doner - "sembol yoksa 404" testi
    boylece gecerli kalir.
    """
    from datetime import datetime, timedelta, timezone

    from app.services import market as market_servisi
    from tests.helpers.factories import candle, price_point
    from tests.helpers.fakes import StubRepo

    BILINEN = {"THYAO", "ASELS"}

    async def _gecmis(symbol, days=30, **kwargs):
        if symbol.upper() not in BILINEN:
            return []
        return [price_point(300.0 + i, gun_once=days - i) for i in range(min(days, 30))]

    async def _mumlar(symbol, interval="5m", days=5, **kwargs):
        # `ts` DATETIME olmali: `_unix_seconds` ISO metin/`datetime` bekler,
        # ham unix tamsayisi `fromisoformat`'i patlatir.
        if symbol.upper() not in BILINEN:
            return []
        baslangic = datetime(2026, 1, 2, tzinfo=timezone.utc)
        return [candle(ts=baslangic + timedelta(hours=i)) for i in range(24)]

    depo = StubRepo(get_history=_gecmis, get_candles=_mumlar)
    monkeypatch.setattr(market_servisi, "get_market_repository", lambda: depo)
    return depo


def test_gecmis_sembol_yoksa_404_verir(client, auth, piyasa_gecmisi):
    assert (
        client.get("/api/market/history", params={"symbol": "YOK_BOYLE"}, headers=auth).status_code
        == 404
    )


def test_gecmis_donen_days_KULLANICININ_istedigi_degerdir(client, auth, piyasa_gecmisi):
    """⚠️ Sorgu penceresi iceride `_MIN_SORGU_GUN` ile genisletilir (gunluk
    granulerlik yuzunden `days=1` her zaman bos donerdi) ama YANITTAKI
    `days` alani kullanicinin istedigi deger olarak kalmali."""
    govde = client.get(
        "/api/market/history", params={"symbol": "THYAO", "days": 1}, headers=auth
    ).json()
    assert govde["days"] == 1
    assert govde["symbol"] == "THYAO"


def test_sembol_buyuk_harfe_normalize_edilir(client, auth, piyasa_gecmisi):
    govde = client.get("/api/market/history", params={"symbol": "thyao"}, headers=auth).json()
    assert govde["symbol"] == "THYAO"


def test_mum_ucu_istenen_araligi_yansitir(client, auth, piyasa_gecmisi):
    govde = client.get(
        "/api/market/candles",
        params={"symbol": "THYAO", "interval": "1h", "range": "5d"},
        headers=auth,
    ).json()
    assert (govde["interval"], govde["range"]) == ("1h", "5d")


def test_haber_listesi_her_habere_gorsel_atar(client, auth):
    """Gercek gorsel yoksa kategoriye/basliga gore otomatik atanir - kart
    arayuzu bos gorsel kutusu cizmemeli."""
    for haber in client.get("/api/market/news", params={"limit": 5}, headers=auth).json()["items"]:
        assert haber["image_url"]


# --- Tahmin ---------------------------------------------------------------


def test_tahmin_ucu_ozellik_kapaliyken_null_doner(client, auth):
    """`null` HATA DEGILDIR: tahmin opsiyoneldir (FORECAST_MODEL bos ya da
    torch/timesfm kurulu degil). Frontend `null` gorunce kesikli cizgiyi
    cizmez, grafigin geri kalani calisir."""
    yanit = client.get("/api/market/forecast", params={"symbol": "THYAO"}, headers=auth)
    assert yanit.status_code == 200
    assert yanit.json() is None


def test_tahmin_sembolu_SORGU_parametresidir(client, auth):
    """⚠️ REGRESYON: sembol yol parcasiyken `USD/TRY` ve `EUR/TRY` icin 404
    aliniyordu - `encodeURIComponent` ile `USD%2FTRY` gonderilse de sunucu
    yolu yonlendirmeden ONCE cozuyor ve `/forecast/USD/TRY` hicbir rotaya
    uymuyordu. Frontend hatayi yuttugu icin doviz tahminleri sessizce hic
    cizilmiyordu."""
    yanit = client.get("/api/market/forecast", params={"symbol": "USD/TRY"}, headers=auth)
    assert yanit.status_code == 200


def test_portfoy_tahmini_ucu_de_null_donebilir(client, auth):
    assert client.get("/api/market/forecast-portfolio", headers=auth).json() is None


# --- Ekonomik takvim ------------------------------------------------------


def test_takvim_olaylari_tarihe_gore_siralidir(client, auth):
    """TR (DB) ve global (yfinance) olaylar TEK listede birlestirilir."""
    olaylar = client.get("/api/economic-calendar", headers=auth).json()["items"]
    tarihler = [e["event_date"] for e in olaylar]
    assert tarihler == sorted(tarihler)


def test_global_kaynak_bos_donse_de_TR_olaylari_gosterilir(client, auth, monkeypatch):
    """Global taraf (yfinance) gecici olarak cekilemezse SESSIZCE atlanir;
    TR'ye ozel (TCMB/TUIK) olaylar yine de doner."""
    from app.api.routes import economic_calendar as rota

    async def _bos(**kwargs):
        return []

    monkeypatch.setattr(rota, "fetch_global_events", _bos)

    yanit = client.get("/api/economic-calendar", headers=auth)
    assert yanit.status_code == 200
    assert len(yanit.json()["items"]) > 0


def test_takvim_TR_ve_global_olaylari_BIRLESTIRIR(client, auth, monkeypatch):
    from app.api.routes import economic_calendar as rota

    async def _tek_global(**kwargs):
        return [
            {
                "event_date": "2026-12-31",
                "event_name": "Fed Faiz Karari",
                "country": "US",
                "importance": "high",
                "source_label": "Yahoo Finance",
            }
        ]

    monkeypatch.setattr(rota, "fetch_global_events", _tek_global)

    olaylar = client.get("/api/economic-calendar", headers=auth).json()["items"]
    isimler = [e["event_name"] for e in olaylar]
    assert "Fed Faiz Karari" in isimler
    assert len(isimler) > 1  # TR olaylari da yerinde
