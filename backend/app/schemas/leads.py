"""Lead motoru (BSD kuyrugu / otonom davet) ekrani sozlesmeleri.

Tum parasal alanlar TRY'ye normalize edilmistir ve `_try` ile biter.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class LeadQueueItem(BaseModel):
    """Danisman ekranindaki tek bir satir (BSD/otonom/dislanan)."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    decision: str = Field(description="BSD | AUTONOMOUS | EXCLUDED")
    exclusion_reason: str | None = Field(
        default=None, description="Yalnizca decision=EXCLUDED icin dolu"
    )
    score: int = Field(description="0-100 potansiyel skoru, siralama icin")
    score_components: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list, description="Turkce gerekceler")
    total_value_try: float
    monthly_income: float
    days_since_activity: int | None = None
    created_at: datetime


class LeadScanSummary(BaseModel):
    """Bir taramanin ozeti - kuyruk ekranlarinin ust bilgisi."""

    scan_id: int | None = None
    trigger: str | None = Field(default=None, description="startup | manual | test")
    started_at: datetime | None = None
    finished_at: datetime | None = None
    scanned_count: int = 0
    bsd_count: int = 0
    autonomous_count: int = 0
    excluded_count: int = 0
    emailed_count: int = 0
    skipped: bool = Field(default=False, description="Asgari araliktan dolayi atlandi mi")
    skip_reason: str | None = None


class LeadQueueResponse(BaseModel):
    items: list[LeadQueueItem]
    count: int
    scan: LeadScanSummary


class LeadScanRequest(BaseModel):
    force: bool = Field(default=False, description="Asgari aralik kontrolunu atla")
