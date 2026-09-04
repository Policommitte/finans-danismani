"""Hata sozlesmesi - TUM uclarin uydugu tek zarf.

Frontend `error.code`'a gore dallanir (`401` -> login'e at, `409` -> alan
bazli uyari goster). Zarf degisirse her ekran ayni anda bozulur; bu yuzden
sozlesme burada merkezi olarak sinanir.
"""

from __future__ import annotations

import pytest


def hata(yanit) -> dict:
    govde = yanit.json()
    assert set(govde) == {"error"}, "zarf yalnizca `error` anahtarini tasimali"
    return govde["error"]


def test_bulunmayan_yol_zarfa_uyar(client):
    yanit = client.get("/boyle-bir-yol-yok")
    assert yanit.status_code == 404
    e = hata(yanit)
    assert e["code"] == "http_error"
    assert e["request_id"]


def test_request_id_hem_govdede_hem_basliktadir(client):
    """Kullanici destege bir kimlik verebilsin, log'da aranabilsin."""
    yanit = client.get("/boyle-bir-yol-yok")
    assert hata(yanit)["request_id"] == yanit.headers["X-Request-ID"]


def test_her_istek_farkli_request_id_alir(client):
    ilk = client.get("/health").headers["X-Request-ID"]
    ikinci = client.get("/health").headers["X-Request-ID"]
    assert ilk != ikinci


def test_dogrulama_hatasi_alan_bazli_ayrinti_tasir(client):
    """Frontend hatayi ilgili input'un altina yazabilmeli."""
    yanit = client.post("/api/auth/login", json={"email": "gecersiz", "password": ""})
    assert yanit.status_code == 422

    e = hata(yanit)
    assert e["code"] == "validation_error"
    alanlar = {d["field"] for d in e["details"]}
    assert "email" in alanlar
    assert all({"field", "message", "type"} <= set(d) for d in e["details"])


def test_dogrulama_hatasinda_field_body_onekini_tasimaz(client):
    """`loc` FastAPI'de `("body", "email")` gelir; kullaniciya gosterilen
    alan adi `email` olmali."""
    yanit = client.post("/api/auth/login", json={"email": "x", "password": "y"})
    assert all(not d["field"].startswith("body") for d in hata(yanit)["details"])


def test_kimlik_dogrulama_hatasi_401_ve_kod_dondurur(client):
    yanit = client.get("/api/portfolio/summary")
    assert yanit.status_code == 401
    assert hata(yanit)["code"] == "unauthorized"


def test_401_mesaji_NEDENI_ayirt_etmez(client):
    """ "token suresi doldu" ile "imza gecersiz" ayrimi saldirgana bilgi
    verir; ayrinti yalnizca logdadir."""
    eksik = hata(client.get("/api/portfolio/summary"))["message"]
    gecersiz = hata(
        client.get("/api/portfolio/summary", headers={"Authorization": "Bearer bozuk.token.x"})
    )["message"]
    assert eksik != "" and gecersiz != ""
    assert "imza" not in gecersiz.lower() and "expired" not in gecersiz.lower()


def test_yetki_hatasi_403_dondurur(client, auth):
    """Musteri hesabi danisman ucuna erisemez (lead verileri)."""
    yanit = client.get("/api/leads/bsd-queue", headers=auth)
    assert yanit.status_code == 403
    assert hata(yanit)["code"] == "forbidden"


def test_bulunmayan_kaynak_404_ve_not_found_kodu(client, auth):
    yanit = client.get("/api/market/history", params={"symbol": "BOYLE_SEMBOL_YOK"}, headers=auth)
    assert yanit.status_code == 404
    assert hata(yanit)["code"] == "not_found"


def test_beklenmeyen_hata_icerideki_ayrintiyi_SIZDIRMAZ(client_no_raise, auth, monkeypatch):
    """Traceback loga gider, kullaniciya jenerik metin doner."""
    from app.services import market as market_service

    async def _patla(*a, **kw):
        raise RuntimeError("gizli detay: postgresql://kullanici:parola@host")

    monkeypatch.setattr(market_service, "list_assets", _patla)

    yanit = client_no_raise.get("/api/market/assets", headers=auth)
    assert yanit.status_code == 500
    e = hata(yanit)
    assert e["code"] == "internal_error"
    assert "parola" not in e["message"]
    assert "RuntimeError" not in e["message"]


@pytest.mark.parametrize(
    "yol,parametreler",
    [
        ("/api/portfolio/transactions", {"limit": 0}),
        ("/api/portfolio/transactions", {"limit": 101}),
        # ⚠️ `/performance` PR #81'de yeniden tasarlandi: artik `hours` DEGIL
        # `range` (1G|1H|1A|1Y) aliyor, saat tabanli uc `-v2`ye tasindi.
        # Eski satirlar `hours`'u taniNMAYAN bir parametre yaptigi icin 200
        # donuyordu - yani sinir kontrolu artik hicbir sey sinamiyordu.
        ("/api/portfolio/performance", {"range": "5Y"}),
        ("/api/portfolio/performance-v2", {"hours": 0}),
        ("/api/portfolio/performance-v2", {"hours": 721}),
        ("/api/market/history", {"symbol": "THYAO", "days": 731}),
        ("/api/market/candles", {"symbol": "THYAO", "interval": "3h"}),
        ("/api/market/candles", {"symbol": "THYAO", "range": "10y"}),
    ],
)
def test_sinir_disi_sorgu_parametreleri_422_dondurur(client, auth, yol, parametreler):
    """Sinirlar KOD icinde degil ROTA imzasinda tanimli - servis katmani
    hicbir zaman aralik disi bir deger gormemeli."""
    assert client.get(yol, params=parametreler, headers=auth).status_code == 422
