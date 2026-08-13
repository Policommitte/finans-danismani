"""Risk paneli ucu."""

from fastapi import APIRouter

from app.auth.deps import CurrentUser
from app.schemas.risk import RiskProfileResponse
from app.services.risk import risk_profili_getir

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/profile", response_model=RiskProfileResponse)
async def profile(user: CurrentUser) -> RiskProfileResponse:
    """Portfoy risk skoru ve gerekceleri.

    Skor DETERMINISTIK olarak backend'de hesaplanir; sohbetteki risk ajani da
    ayni fonksiyonu kullanir, dolayisiyla iki ekran ayni sayiyi gosterir.
    """
    return RiskProfileResponse(**await risk_profili_getir(user["id"]))
