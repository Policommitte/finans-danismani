"""Ekonomik takvim sozlesmeleri."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class EconomicEvent(BaseModel):
    event_date: date
    event_time: str | None = Field(
        default=None, description="Europe/Istanbul saatiyle 'HH:MM' - bilinmiyorsa null"
    )
    country: str = Field(description="Iki-uc harfli ulke/bolge kodu (orn. TR, US, EU)")
    event_name: str
    importance: Literal["low", "medium", "high"]
    expected: str | None = None
    actual: str | None = None
    previous: str | None = None
    source_label: str = Field(
        description="Verinin kaynagi - orn. 'TCMB', 'TÜİK', 'Otomatik (Yahoo Finance)'"
    )


class EconomicCalendarResponse(BaseModel):
    items: list[EconomicEvent]
