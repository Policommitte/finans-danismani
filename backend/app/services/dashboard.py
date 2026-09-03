"""Dashboard ilk yukleme servisi.

Dashboard ilk acilista 4 ayri istek yerine TEK istek yapar; sekmeler ve
tazeleme granuler uclari kullanir (mimari v4 bolum 10.2). Ikisi de ayni
servis fonksiyonlarina dayandigi icin iki farkli rakam gorme ihtimali yoktur.
"""

from __future__ import annotations

import asyncio

from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.risk import RiskProfileResponse
from app.services import market as market_service
from app.services import portfolio as portfolio_service
from app.services import trading as trading_service
from app.services.risk import risk_profili_getir


async def get_dashboard_summary(
    user_id: int, portfolio_id: int | None = None
) -> DashboardSummaryResponse:
    """Dashboard'un ilk yuklemesi icin birlesik ozet.

    Bagimsiz sorgular PARALEL calisir: sirali beklemek ilk yuklemeyi bosuna
    uzatir. `return_exceptions=True` kullanilir cunku portfoyu bos bir
    kullanicida ozet sorgusu `NotFoundError` firlatir - bu bir hata degil,
    gecerli bir durumdur ve dashboard yine acilmalidir.
    """
    ozet, varliklar, dagilim, nakit, risk, hareketliler = await asyncio.gather(
        portfolio_service.ozet_getir(user_id, portfolio_id),
        portfolio_service.varliklar_getir(user_id, portfolio_id),
        portfolio_service.dagilim_getir(user_id, portfolio_id),
        trading_service.hesap_getir(user_id),
        risk_profili_getir(user_id, portfolio_id),
        market_service.top_movers(),
        return_exceptions=True,
    )

    return DashboardSummaryResponse(
        summary=ozet if not isinstance(ozet, Exception) else None,
        holdings=varliklar.items if not isinstance(varliklar, Exception) else [],
        allocation=dagilim.items if not isinstance(dagilim, Exception) else [],
        cash_account=nakit if not isinstance(nakit, Exception) else None,
        risk=RiskProfileResponse(**risk) if not isinstance(risk, Exception) else _empty_risk(),
        movers=hareketliler if not isinstance(hareketliler, Exception) else [],
    )


def _empty_risk() -> RiskProfileResponse:
    return RiskProfileResponse(
        risk_score=0,
        risk_level="hesaplanamadi",
        tolerance_alignment="bilinmiyor",
        holding_count=0,
        components={},
        reasons=["Risk profili su anda hesaplanamadi."],
        suggestions=[],
    )
