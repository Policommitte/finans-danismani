"""Lead motoru (BSD kuyrugu / otonom davet) ekrani sozlesmeleri.

Tum parasal alanlar TRY'ye normalize edilmistir ve `_try` ile biter.
"""

from datetime import date, datetime
from typing import Literal

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
    likit_para: float
    phone_number: str | None = None
    birth_date: date | None = Field(
        default=None, description="Yas EKRANDA bundan turetilir, ayrica saklanmaz"
    )
    tckn_last4: str | None = Field(default=None, description="Arayuzde '•••• 1234' gosterimi")
    registered_at: datetime | None = Field(
        default=None,
        description="Musterinin sisteme eklendigi an (`users.created_at`). "
        "Satirin `created_at` alaniyla KARISTIRILMAMALI: o, kaydin hangi "
        "taramada/temasta uretildigini soyler ve her taramada degisir.",
    )
    days_since_activity: int | None = None
    call_outcome: str | None = Field(
        default=None,
        description="Danismanin son isaretledigi gorusme sonucu: "
        "KABUL | ISTEMIYOR | ULASILAMADI. Hic isaretlenmediyse (ya da "
        "'ACIK' ile temizlendiyse) None.",
    )
    call_outcome_at: datetime | None = Field(
        default=None, description="Yukaridaki sonucun isaretlendigi an"
    )
    mail_gonderildi: bool = Field(
        default=False,
        description="Otonom kuyrukta anlamli: mail fiilen gonderildi mi, yoksa "
        "kota/hata freni/Gmail ayari nedeniyle beklemede mi",
    )
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


class LeadOutcomeRequest(BaseModel):
    """Danismanin telefon gorusmesinden sonra elle isaretledigi sonuc.

    `ACIK` bir sonuc DEGIL, "sonucu temizle" demektir: yanlis isaretlemeyi
    satir silmeden geri alir (`lead_call_outcomes` ekleme-only'dir).
    """

    outcome: Literal["KABUL", "ISTEMIYOR", "ULASILAMADI", "ACIK"]
    note: str | None = Field(default=None, max_length=500, description="Serbest not")
