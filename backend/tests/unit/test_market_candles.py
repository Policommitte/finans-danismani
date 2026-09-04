"""`app.services.market` - mum toplama ve pencere hesabi (saf kisim).

Grafik dogrulugunun tamami buradadir: yanlis kova, mumu yanlis saate
yazar; yanlis pencere ya bos grafik ya da yuz kilobaytlik gereksiz JSON
uretir.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.market import (
    HISTORY_ARCHIVE_DAYS,
    INTERVAL_SECONDS,
    RANGE_DAYS,
    _dort_saatlik_mumlara_topla,
    _history_day_count,
    _kaynak_mum_araligi,
    _ohlcv_dogrudan,
    _ohlcv_topla,
    _standart_mum_kovasi,
    _unix_seconds,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def satir(ts, *, o=100.0, h=110.0, low=90.0, c=105.0, v=1.0) -> dict:
    return {"ts": ts, "open": o, "high": h, "low": low, "close": c, "volume": v}


def istanbul(yil, ay, gun, saat=0, dakika=0) -> datetime:
    return datetime(yil, ay, gun, saat, dakika, tzinfo=ISTANBUL)


# --- Zaman cevirimi -------------------------------------------------------


def test_datetime_unix_saniyeye_cevrilir():
    an = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    assert _unix_seconds(an) == int(an.timestamp())


def test_zaman_dilimsiz_damga_utc_kabul_edilir():
    naif = datetime(2026, 9, 2, 12, 0)
    assert _unix_seconds(naif) == int(naif.replace(tzinfo=timezone.utc).timestamp())


@pytest.mark.parametrize(
    "ham",
    ["2026-09-02T12:00:00Z", "2026-09-02T12:00:00+00:00", "2026-09-02T12:00:00"],
)
def test_iso_metin_ve_z_soneki_ayni_ani_verir(ham):
    """Depo katmani `ts`'i datetime, ISO metin ya da `Z` sonekli metin
    donebilir; ucu de AYNI ana cozulmeli."""
    beklenen = int(datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc).timestamp())
    assert _unix_seconds(ham) == beklenen


# --- Kova hizalama --------------------------------------------------------


def test_gunluk_kova_utc_gun_sinirina_hizalanir():
    ts = int(datetime(2026, 9, 2, 15, 30, tzinfo=timezone.utc).timestamp())
    kova = _standart_mum_kovasi(ts, INTERVAL_SECONDS["1d"])
    assert kova == int(datetime(2026, 9, 2, tzinfo=timezone.utc).timestamp())


def test_gun_ici_kova_ISTANBUL_gece_yarisina_hizalanir():
    """Grafik Istanbul saatiyle okunur; UTC'ye hizalanan bir saatlik kova
    kullaniciya bir saat kaymis gorunurdu."""
    ts = int(istanbul(2026, 9, 2, 13, 45).timestamp())
    kova = _standart_mum_kovasi(ts, INTERVAL_SECONDS["1h"])
    assert datetime.fromtimestamp(kova, tz=ISTANBUL) == istanbul(2026, 9, 2, 13)


def test_ayni_kovadaki_iki_damga_ayni_kovayi_verir():
    a = _standart_mum_kovasi(int(istanbul(2026, 9, 2, 13, 1).timestamp()), 3600)
    b = _standart_mum_kovasi(int(istanbul(2026, 9, 2, 13, 59).timestamp()), 3600)
    assert a == b


def test_kova_sinirindaki_damga_bir_sonraki_kovaya_gecer():
    a = _standart_mum_kovasi(int(istanbul(2026, 9, 2, 13, 59).timestamp()), 3600)
    b = _standart_mum_kovasi(int(istanbul(2026, 9, 2, 14, 0).timestamp()), 3600)
    assert b == a + 3600


# --- OHLCV toplama --------------------------------------------------------


def test_ayni_kovadaki_mumlar_dogru_ohlc_uretir():
    """Acilis ILK, kapanis SON mumdan; yuksek/dusuk uc degerlerden."""
    baz = istanbul(2026, 9, 2, 10, 0)
    rows = [
        satir(baz, o=100, h=105, low=99, c=104),
        satir(baz + timedelta(minutes=20), o=104, h=120, low=95, c=110),
        satir(baz + timedelta(minutes=40), o=110, h=112, low=108, c=111),
    ]
    (mum,) = _ohlcv_topla(rows, INTERVAL_SECONDS["1h"])
    assert (mum.open, mum.high, mum.low, mum.close) == (100, 120, 95, 111)


def test_hacimler_toplanir():
    baz = istanbul(2026, 9, 2, 10, 0)
    rows = [satir(baz, v=10), satir(baz + timedelta(minutes=30), v=5)]
    (mum,) = _ohlcv_topla(rows, INTERVAL_SECONDS["1h"])
    assert mum.volume == 15


def test_hacimsiz_seri_none_hacim_dondurur():
    """Turetilmis varliklarda (gram altin) hacim yok - 0 yazmak yanlis
    olurdu."""
    rows = [satir(istanbul(2026, 9, 2, 10), v=None)]
    (mum,) = _ohlcv_topla(rows, INTERVAL_SECONDS["1h"])
    assert mum.volume is None


def test_mumlar_zamana_gore_sirali_doner():
    """Depodan sirasiz gelse bile grafik sirali bekler."""
    baz = istanbul(2026, 9, 2, 10, 0)
    rows = [satir(baz + timedelta(hours=2)), satir(baz), satir(baz + timedelta(hours=1))]
    mumlar = _ohlcv_topla(rows, INTERVAL_SECONDS["1h"])
    assert [m.time for m in mumlar] == sorted(m.time for m in mumlar)


def test_farkli_kovalar_ayri_mum_uretir():
    baz = istanbul(2026, 9, 2, 10, 0)
    rows = [satir(baz), satir(baz + timedelta(hours=1))]
    assert len(_ohlcv_topla(rows, INTERVAL_SECONDS["1h"])) == 2


def test_bos_girdi_bos_liste_verir():
    assert _ohlcv_topla([], 3600) == []


# --- Dogrudan gecis -------------------------------------------------------


def test_dogrudan_gecis_kaynak_zamanini_KORUR():
    """⚠️ 1h istegi 1h kaynagindan geliyorsa mum YENIDEN KOVALANMAZ. BIST
    seansi 10:00'da baslar ve Yahoo'nun saatlik mumu yarim saat ofset
    tasir; yeniden kovalamak o ofseti siler ve mum yanlis saate kayar."""
    an = istanbul(2026, 9, 2, 10, 30)
    (mum,) = _ohlcv_dogrudan([satir(an)])
    assert mum.time == int(an.timestamp())


def test_dogrudan_gecis_hacimsiz_satiri_tolere_eder():
    (mum,) = _ohlcv_dogrudan([satir(istanbul(2026, 9, 2, 10), v=None)])
    assert mum.volume is None


# --- 4 saatlik toplama ----------------------------------------------------


def test_dort_saatlik_mumlar_gunun_ILK_mumundan_baslar():
    """Sabit UTC kovasi kullanilsaydi BIST'in 10:00 acilisi bir onceki
    kovaya duser ve ilk 4h mumu yalnizca iki saati kapsardi."""
    baz = istanbul(2026, 9, 2, 10, 0)
    rows = [satir(baz + timedelta(hours=i)) for i in range(8)]
    mumlar = _dort_saatlik_mumlara_topla(rows)
    assert len(mumlar) == 2
    assert datetime.fromtimestamp(mumlar[0].time, tz=ISTANBUL) == baz


def test_dort_saatlik_mum_ohlc_yi_dogru_toplar():
    baz = istanbul(2026, 9, 2, 10, 0)
    rows = [
        satir(baz, o=100, h=105, low=98, c=102),
        satir(baz + timedelta(hours=1), o=102, h=130, low=90, c=120),
        satir(baz + timedelta(hours=2), o=120, h=125, low=118, c=119),
    ]
    (mum,) = _dort_saatlik_mumlara_topla(rows)
    assert (mum.open, mum.high, mum.low, mum.close) == (100, 130, 90, 119)


def test_gunler_birbirine_karismaz():
    """Her piyasa gunu KENDI ilk mumundan baslar."""
    gun1 = [satir(istanbul(2026, 9, 2, 10) + timedelta(hours=i)) for i in range(2)]
    gun2 = [satir(istanbul(2026, 9, 3, 10) + timedelta(hours=i)) for i in range(2)]
    mumlar = _dort_saatlik_mumlara_topla(gun1 + gun2)
    assert len(mumlar) == 2
    gunler = {datetime.fromtimestamp(m.time, tz=ISTANBUL).date() for m in mumlar}
    assert len(gunler) == 2


def test_dort_saatlik_sonuc_zamana_gore_siralidir():
    rows = [satir(istanbul(2026, 9, 3, 10)), satir(istanbul(2026, 9, 2, 10))]
    mumlar = _dort_saatlik_mumlara_topla(rows)
    assert [m.time for m in mumlar] == sorted(m.time for m in mumlar)


# --- Kaynak secimi ve pencere ---------------------------------------------


@pytest.mark.parametrize(
    "istenen,kaynak",
    [("1m", "1m"), ("1h", "1h"), ("4h", "1h"), ("1d", "1d"), ("5m", "5m"), ("15m", "5m")],
)
def test_kaynak_mum_araligi_secimi(istenen, kaynak):
    assert _kaynak_mum_araligi(istenen, "1m") == kaynak


@pytest.mark.parametrize(
    "aralik,kaynak,beklenen",
    [
        ("1m", "1h", 120),  # eskiden 730 idi
        ("3m", "1h", 180),
        ("1y", "1h", 730),  # tam arsiv - degismedi
        ("1d", "5m", 60),
    ],
)
def test_gecmis_penceresi_gorunen_araliкla_olceklenir(aralik, kaynak, beklenen):
    """⚠️ REGRESYON: pencere eskiden HER aralikta 730 gundu. Market
    sayfasinin varsayilan aylik/saatlik grafigi icin iki yillik arsivin
    tamami cekiliyor, ustelik 60 sn'de bir tazeleniyordu - ve bu istek
    sayfa gecis perdesinin bekledigi istekti."""
    assert _history_day_count(aralik, kaynak) == beklenen


@pytest.mark.parametrize("aralik", sorted(RANGE_DAYS))
@pytest.mark.parametrize("kaynak", ["1m", "5m", "1h", "1d"])
def test_pencere_hicbir_zaman_arsivi_asmaz(aralik, kaynak):
    """Depodaki en uzun arsiv 730 gun; otesini istemek bos donerdi."""
    assert _history_day_count(aralik, kaynak) <= HISTORY_ARCHIVE_DAYS


@pytest.mark.parametrize("aralik", sorted(RANGE_DAYS))
def test_pencere_gorunen_araligi_her_zaman_kapsar(aralik):
    """Sola kaydirma payi olmasa bile gorunen aralik eksiksiz gelmeli."""
    assert _history_day_count(aralik, "1h") >= RANGE_DAYS[aralik]
