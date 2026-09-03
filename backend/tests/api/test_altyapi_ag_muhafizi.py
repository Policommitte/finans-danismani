"""Ag muhafizinin IKI YONU de burada sabitlenir (`conftest.py::_ag_kapali`).

NEDEN AYRI BIR DOSYA: muhafiz bir kez `socket.socket.__init__`'i topyekun
kapatiyordu. Bu, TestClient'in kurdugu asyncio olay dongusunun self-pipe'ini
(`socketpair`) da engelledigi icin API testlerinin TAMAMINI (99 test)
kiriyordu - ve hata "'ProactorEventLoop' object has no attribute '_ssock'"
diye gorundugu icin nedeni gizliyordu.

Yalnizca "dis cagri patliyor mu" diye test etseydik o regresyon yine
kacardi: muhafiz asiri genis oldugunda da o test YESIL kalir. Bu yuzden
ters yon - "ic trafik CALISIYOR mu" - de sabitlenir.

`tests/api/` altinda: sinanan sey muhafizin ASGI/TestClient yolunu bozmadigi.
"""

from __future__ import annotations

import asyncio
import socket

import pytest

# --- Muhafizin GECIRMESI gerekenler ---------------------------------------


def test_soket_yaratmak_serbesttir():
    """Yasak "soket yaratmak" degil "disari baglanmak"."""
    s = socket.socket()
    s.close()


def test_socketpair_calisir():
    """Her asyncio olay dongusu self-pipe'ini bununla acar."""
    a, b = socket.socketpair()
    a.close()
    b.close()


def test_olay_dongusu_kurulabilir():
    dongu = asyncio.new_event_loop()
    dongu.close()


def test_testclient_calisir(client):
    """ASGI cagrisi surec icidir; muhafiz onu engellememeli."""
    assert client.get("/health").status_code == 200


def test_geri_dongu_baglantisi_serbesttir():
    dinleyici = socket.socket()
    dinleyici.bind(("127.0.0.1", 0))
    dinleyici.listen(1)
    try:
        istemci = socket.socket()
        istemci.connect(("127.0.0.1", dinleyici.getsockname()[1]))
        istemci.close()
    finally:
        dinleyici.close()


# --- Muhafizin ENGELLEMESI gerekenler -------------------------------------


def test_dis_baglanti_create_connection_ile_yasak():
    with pytest.raises(RuntimeError, match="DIS ag baglantisi"):
        socket.create_connection(("finance.yahoo.com", 443), timeout=1)


def test_dis_baglanti_connect_ile_yasak():
    s = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="DIS ag baglantisi"):
            s.connect(("8.8.8.8", 53))
    finally:
        s.close()


def test_dis_baglanti_connect_ex_ile_yasak():
    s = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="DIS ag baglantisi"):
            s.connect_ex(("8.8.8.8", 53))
    finally:
        s.close()


def test_sinifi_dogrudan_import_eden_kutuphane_de_yakalanir():
    """⚠️ Yama `socket.socket` ISMINE degil SINIFA uygulanir.

    `requests`/`urllib3` gibi kutuphaneler `from socket import socket`
    yapar; modul ismini degistirmek onlari KACIRIRDI.
    """
    from socket import socket as duz_soket

    s = duz_soket()
    try:
        with pytest.raises(RuntimeError, match="DIS ag baglantisi"):
            s.connect(("example.com", 80))
    finally:
        s.close()


@pytest.mark.parametrize("hedef", [("1.1.1.1", 53), ("api.cohere.ai", 443)])
def test_bilinen_dis_hedefler_yasak(hedef):
    with pytest.raises(RuntimeError, match="DIS ag baglantisi"):
        socket.create_connection(hedef, timeout=1)
