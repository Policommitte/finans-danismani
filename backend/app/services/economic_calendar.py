"""Global ekonomik olay takvimi - yfinance'ten canli cekilir.

Turkiye'ye ozel olaylar (TCMB PPK, TUIK TUFE) BURADA DEGIL, `economic_events`
tablosunda (bkz. app/repositories/*.py -> EconomicCalendarRepository) - yfinance
bu olaylari icermiyor. Iki kaynak `app/api/routes/economic_calendar.py`'de
birlestirilir.

`app/services/pexels.py` ile AYNI felsefe: dis servis ASLA istegi cokertmez.
Hata/bos sonuc durumunda BOS LISTE doner, hic firlatilmaz.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, timedelta
from typing import Literal

logger = logging.getLogger(__name__)

#: yfinance senkron bir kutuphane; sonuc surec basina onbelleklenir ki her
#: istek WSDL/HTTP cagirisi yapmasin. "Gunde birkac kez yenilensin" istegi
#: icin 4 saat (~gunde 6 kez) yeterli - ekonomik olay takvimleri saatlik
#: degismez.
_CACHE_TTL_SECONDS = 4 * 3600

#: "Buyuk ekonomilerin verileri" (Fed FOMC, ECB gibi) - yfinance'in ham
#: verisi onlarca kucuk ulkeyi de icerir (orn. Malavi, Umman, Kuveyt gibi
#: gosterge kotasi haberleri); bunlarin piyasa acisindan bir anlami yok.
_MAJOR_REGIONS = {"US", "EU", "GB", "DE", "JP", "CN"}

#: Basit anahtar-kelime siniflandirmasi - yfinance "importance" alani
#: DONMUYOR. Bu liste kapsamli degil, sadece piyasayi en cok hareket
#: ettiren gosterge turlerini yakalar (enflasyon, buyume, faiz, istihdam).
_HIGH_IMPORTANCE_KEYWORDS = (
    "cpi",
    "gdp",
    "rate",
    "payroll",
    "pmi",
    "fomc",
    "unemployment",
    "retail sales",
    "inflation",
)

_cache: dict = {"data": None, "fetched_at": 0.0}


def _importance_for(event_name: str) -> Literal["low", "medium", "high"]:
    lowered = event_name.lower()
    if any(keyword in lowered for keyword in _HIGH_IMPORTANCE_KEYWORDS):
        return "high"
    return "medium"


def _metin(deger) -> str | None:
    """Pandas hucresini metne cevirir; None/NaN -> None."""
    if deger is None:
        return None
    try:
        if deger != deger:  # NaN kontrolu (pandas float NaN kendine esit degildir)
            return None
    except TypeError:
        pass
    return str(deger)


#: yfinance TEK cagrida en fazla 100 satir doner (kutuphanenin kendi siniri).
#: "Butun seneye yayilma" istegi icin sayfalama (offset) ile TUM mevcut
#: satirlar cekilir - ust sinir sadece sonsuz donguye karsi bir emniyet
#: subabidir, gercek veri CANLI TESTTE ~1100 satirda (tum bolgeler, ~4
#: haftalik pencere) tukeniyordu.
_MAX_SAYFA = 30
_SAYFA_BOYU = 100

#: Ekranda gosterilen saat, sitenin geri kalaniyla AYNI saat dilimindedir
#: (bkz. app/config.py -> market_day_timezone). yfinance UTC doner.
_GOSTERIM_SAAT_DILIMI = "Europe/Istanbul"


def _fetch_sync(days_ahead: int) -> list[dict]:
    """Senkron yfinance cagirisi - `asyncio.to_thread` icinde calistirilir.

    ONEMLI SINIRLAMA (canli test edildi, 2026-08-30): Yahoo'nun ucretsiz
    ekonomik takvimi sadece YAKIN VADELI (gozlemde ~4 hafta ileri) olaylari
    yayinliyor - `days_ahead` ne kadar buyuk verilirse verilsin, uzak
    gelecek icin BOS doner. Bu yfinance'in ya da bu kodun bir eksigi degil,
    veri kaynaginin kendi kapsaminin siniri. Turkiye'ye ozel taraf
    (economic_events tablosu) tam yila kadar ayri sekilde doludur.
    """
    import pandas as pd
    import yfinance as yf

    today = date.today()
    calendars = yf.Calendars(start=today, end=today + timedelta(days=days_ahead))

    frames = []
    for sayfa in range(_MAX_SAYFA):
        frame = calendars.get_economic_events_calendar(
            limit=_SAYFA_BOYU, offset=sayfa * _SAYFA_BOYU
        )
        if frame.empty:
            break
        frames.append(frame)

    if not frames:
        return []

    #: Ayni olay adi FARKLI tarihlerde tekrar eder (orn. "CPI YY*" haftanin
    #: her gunu ayri bir satir) - index (olay adi) TEK BASINA benzersiz
    #: DEGILDIR. Tekillik (olay adi + bolge + zaman) uclusuyle saglanir,
    #: yoksa sayfalar arasi CAKISMA farkli tarihli gercek satirlari da
    #: silerdi.
    combined = pd.concat(frames).reset_index(names="EventName")
    combined = combined.drop_duplicates(subset=["EventName", "Region", "Event Time"])

    events: list[dict] = []
    for _, row in combined.iterrows():
        event_name = row["EventName"]
        region = str(row.get("Region") or "").strip()
        if region not in _MAJOR_REGIONS:
            continue

        event_time = row.get("Event Time")
        if hasattr(event_time, "tz_convert"):
            local_time = event_time.tz_convert(_GOSTERIM_SAAT_DILIMI)
            event_date = local_time.date()
            event_hour = local_time.strftime("%H:%M")
        else:
            event_date = today
            event_hour = None

        events.append(
            {
                "event_date": event_date,
                "event_time": event_hour,
                "country": region,
                "event_name": str(event_name).rstrip("*").strip(),
                "importance": _importance_for(str(event_name)),
                "expected": _metin(row.get("Expected")),
                "actual": _metin(row.get("Actual")),
                "previous": _metin(row.get("Last")),
                "source_label": "Otomatik (Yahoo Finance)",
            }
        )

    return events


async def fetch_global_events(days_ahead: int = 365) -> list[dict]:
    """Buyuk ekonomilerin yaklasan ekonomik olaylarini doner.

    `days_ahead` yila kadar istenebilir ama Yahoo'nun ucretsiz verisi fiilen
    yalnizca yakin vadeyi (~4 hafta) kapsiyor - bkz. `_fetch_sync` docstring.
    Basarisiz olursa (ag hatasi, yfinance'in kendi hatasi, beklenmeyen veri
    bicimi) BOS LISTE doner - hata ASLA disari firlatilmaz, cagiran taraf
    (routes/economic_calendar.py) bunu "global veri su an yok" olarak
    yorumlar; TR'ye ozel olaylar (DB'den) yine de gosterilmeye devam eder.
    """
    now = time.time()
    if _cache["data"] is not None and now - _cache["fetched_at"] < _CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        events = await asyncio.to_thread(_fetch_sync, days_ahead)
    except Exception as exc:  # noqa: BLE001 - dis servis, asla cokmemeli
        logger.warning(
            "yfinance ekonomik takvim cekilemedi",
            extra={"hata": f"{type(exc).__name__}: {exc}"},
        )
        return _cache["data"] or []

    _cache["data"] = events
    _cache["fetched_at"] = now
    return events
