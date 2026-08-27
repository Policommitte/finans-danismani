"""Dashboard ilk yukleme sozlesmesi.

Dashboard'un ILK yuklemesi tek istekle gelir (4 istek yerine 1); sekmeler ve
tazeleme granuler uclari kullanir (mimari v4 bolum 10.2).
"""

from pydantic import BaseModel, Field

from app.schemas.market import Asset
from app.schemas.portfolio import AllocationSlice, Holding, PortfolioSummary
from app.schemas.risk import RiskProfileResponse
from app.schemas.trading import TradingAccount


class DashboardSummaryResponse(BaseModel):
    summary: PortfolioSummary | None = Field(default=None, description="Portfoy bossa None doner")
    holdings: list[Holding]
    allocation: list[AllocationSlice]
    cash_account: TradingAccount | None = Field(
        default=None,
        description="Portfoyun kullanilabilir ve emirlerde bloke sanal TRY bakiyesi",
    )
    risk: RiskProfileResponse
    movers: list[Asset] = Field(description="Gun icinde en cok hareket eden varliklar")
