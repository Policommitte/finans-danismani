"""Otonom oneri sozlesmeleri (FR-AUT-003, FR-AUT-011, FR-AUT-023)."""

from __future__ import annotations

from pydantic import BaseModel, Field

#: FR-AUT-023: ret gerekcesi SABIT kumedir - serbest metin alinmaz.
#: Gerekce sonraki oneri uretimine girdi olacagi icin (FR-AUT-024)
#: siniflandirilabilir olmasi gerekir.
RET_GEREKCELERI = (
    "NOT_INTERESTED",
    "TOO_RISKY",
    "NO_CASH",
    "BAD_TIMING",
    "NOT_UNDERSTOOD",
)


class RecommendationSource(BaseModel):
    """FR-AUT-003: kaynak baglantisi. BR-AUT-01: kaynaksiz oneri gosterilemez."""

    label: str = Field(description="Kullaniciya gosterilecek kaynak adi")
    kind: str = Field(description="rule | market | news | portfolio")
    url: str | None = Field(default=None, description="Varsa dis baglanti")


class Recommendation(BaseModel):
    """Oneri karti. FR-AUT-003'teki zorunlu alanlarin tamami buradadir."""

    id: int
    asset_symbol: str
    asset_name: str
    asset_class: str
    side: str = Field(description="BUY | SELL")
    quantity: float
    reference_price: float
    estimated_amount: float
    confidence: float = Field(description="0..1")
    rationale: list[str] = Field(description="En cok 5 madde (FR-AUT-003)")
    risk_note: str
    sources: list[RecommendationSource]
    personalization: dict = Field(
        default_factory=dict, description="FR-AUT-012 'neden bana geldi?' kirilimi"
    )
    status: str
    rejection_reason: str | None = None
    order_id: int | None = None
    expires_at: str
    created_at: str
    viewed_at: str | None = None
    decided_at: str | None = None
    #: BR-AUT-01 / FR-AUT-003: SPK uyarisi kart ile BIRLIKTE tasinir.
    #: Istemcinin kendi metnini uydurmasi degil, sunucunun verdigi metnin
    #: gosterilmesi beklenir.
    disclaimer: str


class RecommendationListResponse(BaseModel):
    items: list[Recommendation]
    #: FR-AUT-011: sekme rozetleri icin durum bazli sayimlar.
    counts: dict[str, int]


class RejectRequest(BaseModel):
    reason: str = Field(description=" | ".join(RET_GEREKCELERI))


class ApproveRequest(BaseModel):
    """FR-AUT-014: kullanici onerilen adedi onay ekraninda degistirebilir."""

    quantity: float | None = Field(
        default=None, description="Bos birakilirsa onerilen adet kullanilir"
    )


class AutonomousSettings(BaseModel):
    """FR-PRF-014 + FR-AUT-026: otonom akis limitleri ve acma/kapama."""

    autonomous_enabled: bool
    per_order_limit_try: float
    daily_limit_try: float
    allowed_asset_classes: list[str]
    max_daily_recommendations: int
