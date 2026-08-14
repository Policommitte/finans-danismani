"""Risk paneli sozlesmesi."""

from pydantic import BaseModel, Field


class RiskComponents(BaseModel):
    """Skorun kirilimi - RiskPanel bunu cubuk grafik olarak gosterebilir."""

    concentration: float = Field(default=0, description="Yogunlasma (0-40)")
    asset_type: float = Field(default=0, description="Varlik tipi riski (0-35)")
    volatility: float = Field(default=0, description="Oynaklik (0-15)")
    single_position: float = Field(default=0, description="Tek pozisyon agirligi (0-10)")


class RiskProfileResponse(BaseModel):
    risk_score: int = Field(description="0-100, yuksek = riskli")
    risk_level: str = Field(description="dusuk | orta | yuksek | cok yuksek | hesaplanamadi")
    risk_tolerance: str | None = Field(default=None, description="Kullanicinin beyani")
    tolerance_alignment: str = Field(description="uyumlu | tolerans ustu | tolerans alti")
    holding_count: int
    top_class: str | None = None
    top_class_pct: float | None = None
    avg_volatility_pct: float | None = None
    components: RiskComponents
    reasons: list[str]
    suggestions: list[str]
