"""Ekonomik takvim ucu - TR'ye ozel (DB) + global (yfinance) olaylarin birlesimi."""

from datetime import date, timedelta

from fastapi import APIRouter

from app.auth.deps import CurrentUser
from app.repositories.deps import get_economic_calendar_repository
from app.schemas.economic_calendar import EconomicCalendarResponse, EconomicEvent
from app.services.economic_calendar import fetch_global_events

router = APIRouter(prefix="/api/economic-calendar", tags=["economic-calendar"])

#: Ne kadar ileriye bakilacagi - "butun seneye yayilma" istegi icin 365
#: gune cikarildi. TR (DB) taraf bu pencerenin tamamini gercekten doldurur;
#: global (yfinance) taraf ise veri kaynaginin kendi sinirlamasi geregi
#: fiilen yalnizca yakin vadeyi (~4 hafta) doldurur - bkz.
#: app/services/economic_calendar.py::_fetch_sync docstring.
GUN_ARALIGI = 365


@router.get("", response_model=EconomicCalendarResponse)
async def economic_calendar(user: CurrentUser) -> EconomicCalendarResponse:
    """Turkiye'ye ozel (TCMB/TUIK) ve global (Fed/ECB gibi buyuk ekonomiler,
    yfinance'ten canli cekilir) ekonomik olaylari TEK, tarihe gore sirali
    bir listede birlestirir.

    Global taraf gecici olarak cekilemezse (bkz. app/services/economic_calendar.py)
    sessizce atlanir - hata FIRLATILMAZ, TR'ye ozel olaylar yine de doner.
    """
    today = date.today()
    end = today + timedelta(days=GUN_ARALIGI)

    tr_events = await get_economic_calendar_repository().list_events(today, end)
    global_events = await fetch_global_events(days_ahead=GUN_ARALIGI)

    #: TR taraf `source` (repository/DB kolon adi) doner, sema `source_label`
    #: bekler - "kaynak: TCMB/TUIK" etiketi icin ayni deger yeniden kullanilir.
    tr_items = [EconomicEvent(**{**row, "source_label": row["source"]}) for row in tr_events]
    global_items = [EconomicEvent(**row) for row in global_events]

    items = [*tr_items, *global_items]
    items.sort(key=lambda e: e.event_date)

    return EconomicCalendarResponse(items=items)
