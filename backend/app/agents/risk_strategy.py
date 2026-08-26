"""RiskStrategyAgent - risk skoru ve strateji yorumu.

SIRALI AJAN - fan-out'un parcasi DEGILDIR (mimari v4 bolum 5.2).
`portfolio_data` ve `market_data` dolmadan calisamaz; paralel konumlansaydi bu
alanlar `None` olurdu ve ajan bos veriyle "hata firlatmayan ama yanlis sonuc
ureten" bir cikti verirdi.

RISK SKORU NEREDE HESAPLANIR?
    Sayi BACKEND'DE DETERMINISTIK olarak hesaplanir (`app/services/risk.py`),
    ajan yalnizca yorumlar. Boylece dashboard'daki RiskPanel ile sohbetteki
    ajan AYNI skoru gosterir; iki ayri yerde hesaplansaydi iki farkli sayi
    cikardi (mimari v4 bolum 5.5 notu).
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.mcp.server import CORE_SERVER_NAME, MARKET_SERVER_NAME
from app.orchestration.models import AgentError, AgentState
from app.services.risk import risk_profili_hesapla

logger = logging.getLogger(__name__)

AGENT_NAME = "risk_strategy"

#: Oynaklik olcumu icin kac gunluk gecmise bakilir.
VOLATILITY_WINDOW_DAYS = 30

#: Oynaklik olcumu yapilacak en fazla varlik sayisi. Portfoydeki her varlik
#: icin ayri tool cagrisi yapmak istegi yavaslatir; en buyuk pozisyonlar
#: portfoy riskini zaten belirler.
MAX_VOLATILITY_LOOKUPS = 3


class RiskStrategyAgent(BaseAgent):
    """Portfoy riskini skorlar ve strateji onerisi yorumlar."""

    name = AGENT_NAME

    def __init__(
        self,
        mcp_client,
        llm=None,
        timeout_seconds: int = 20,
        llm_timeout_seconds: int | None = None,
    ) -> None:
        super().__init__(
            mcp_client=mcp_client,
            llm=llm,
            timeout_seconds=timeout_seconds,
            llm_timeout_seconds=llm_timeout_seconds,
        )

    async def _execute(self, state: AgentState) -> dict:
        if not self.is_requested(state):
            logger.debug("risk ajani atlandi", extra={"agent": self.name})
            return {}

        # SAVUNMACI KONTROL: topoloji dogruysa buraya portfoy verisiyle
        # gelinir. Gelinmiyorsa graph kenarlari bozulmus demektir; sessizce
        # yanlis skor uretmek yerine durum acikca raporlanir.
        if state.portfolio_data is None:
            return {
                "agent_errors": [
                    AgentError(
                        agent_name=self.name,
                        error_type="tool_error",
                        message="Portfoy verisi olmadan risk hesaplanamadi.",
                    )
                ]
            }

        profil = await self._profil_getir()
        oynakliklar = await self._oynaklik_olc(state.portfolio_data)

        # Skor tek yerde hesaplanir (services/risk.py) - dashboard da ayni
        # fonksiyonu cagirir.
        risk = risk_profili_hesapla(
            holdings=state.portfolio_data.get("holdings") or [],
            allocation=state.portfolio_data.get("allocation") or [],
            risk_tolerance=(profil or {}).get("risk_tolerance"),
            volatility_by_symbol=oynakliklar,
        )

        yorum, hata = await self._yorumla(state, risk)
        risk_data = {**risk, "summary_text": yorum}

        guncelleme: dict = {"risk_data": risk_data}
        if hata is not None:
            guncelleme["agent_errors"] = [hata]
        return guncelleme

    # ------------------------------------------------------------------
    # Veri toplama
    # ------------------------------------------------------------------

    async def _profil_getir(self) -> dict[str, Any] | None:
        """Kullanicinin beyan ettigi risk toleransi.

        Basarisiz olursa akis DURMAZ: tolerans bilinmiyorsa skor yalnizca
        portfoy yapisina gore hesaplanir.
        """
        try:
            return await self.call_tool(CORE_SERVER_NAME, "user_get_profile")
        except Exception:  # noqa: BLE001
            logger.warning("risk profili okunamadi, yalnizca portfoy yapisi kullanilacak")
            return None

    async def _oynaklik_olc(self, portfolio_data: dict) -> dict[str, float]:
        """En buyuk pozisyonlarin gecmis oynakligini olcer.

        `market_get_history` ozet doner ve `volatility_pct` alanini icerir;
        hesap MCP katmaninda tek yerde yapilir.
        """
        holdings = (portfolio_data.get("holdings") or [])[:MAX_VOLATILITY_LOOKUPS]
        sonuc: dict[str, float] = {}

        for holding in holdings:
            sembol = holding.get("symbol")
            if not sembol:
                continue
            try:
                gecmis = await self.call_tool(
                    MARKET_SERVER_NAME,
                    "market_get_history",
                    {"symbol": sembol, "days": VOLATILITY_WINDOW_DAYS},
                )
            except Exception:  # noqa: BLE001 - tek sembolun gecmisi yoksa devam
                logger.debug("oynaklik olculemedi", extra={"symbol": sembol})
                continue

            if gecmis.get("volatility_pct") is not None:
                sonuc[sembol] = float(gecmis["volatility_pct"])

        return sonuc

    # ------------------------------------------------------------------
    # Yorum
    # ------------------------------------------------------------------

    async def _yorumla(self, state: AgentState, risk: dict) -> tuple[str, AgentError | None]:
        if self.llm is None:
            return _deterministik_yorum(risk), None

        try:
            return await self.generate(_prompt_yaz(state, risk)), None
        except Exception as exc:  # noqa: BLE001 - LLM cokse de skor korunmali
            logger.exception("risk yorumu uretilemedi", extra={"agent": self.name})
            return _deterministik_yorum(risk), AgentError(
                agent_name=self.name,
                error_type="llm_error",
                message=f"Risk yorumu model tarafindan uretilemedi: {exc}",
            )

    async def get_tools(self) -> list:
        """Bu ajanin tool'lari: `user_get_profile` ve `market_get_history`.

        Portfoy tool'lari LISTEDE YOKTUR: risk ajani portfoy verisini state
        uzerinden (PortfolioAgent'in ciktisi) alir, kendisi tekrar cekmez
        (mimari v4 bolum 6.3).
        """
        if self.mcp_client is None:
            return []

        tools = await self.mcp_client.get_tools()
        return [t for t in tools if t["tool"] in ("user_get_profile", "market_get_history")]


def _deterministik_yorum(risk: dict) -> str:
    """LLM'siz yorum - hesaplanmis skoru ve gerekcelerini cumleye doker."""
    satirlar = [
        f"Portfoy risk skoru {risk['risk_score']}/100 ({risk['risk_level']}).",
    ]
    if risk.get("reasons"):
        satirlar.append("Gerekceler: " + " ".join(risk["reasons"]))
    if risk.get("suggestions"):
        satirlar.append("Degerlendirilebilecek adimlar: " + " ".join(risk["suggestions"]))
    return " ".join(satirlar)


def _prompt_yaz(state: AgentState, risk: dict) -> str:
    ozet = (state.portfolio_data or {}).get("summary") or {}
    piyasa = (state.market_data or {}).get("summary")

    satirlar = [
        f"Kullanici sorusu: {state.user_query}",
        "",
        f"Hesaplanan risk skoru: {risk['risk_score']}/100 ({risk['risk_level']})",
        f"Beyan edilen risk toleransi: {risk.get('risk_tolerance') or 'bilinmiyor'}",
        f"En yuksek agirlikli varlik sinifi: {risk.get('top_class')} "
        f"(%{risk.get('top_class_pct')})",
        f"Portfoy toplam degeri: {ozet.get('total_value_try')} TL",
    ]
    if risk.get("reasons"):
        satirlar.append("Skoru yukselten etkenler: " + " ".join(risk["reasons"]))
    if piyasa:
        satirlar += ["", f"Piyasa arastirmasi ozeti: {piyasa}"]

    satirlar += [
        "",
        "Bu verilere dayanarak Turkce, kisa (en fazla 4 cumle) bir risk degerlendirmesi "
        "yaz. Skoru YENIDEN HESAPLAMA, verilen skoru kullan. Kesin yatirim tavsiyesi "
        "verme; secenekleri degerlendirme dili kullan.",
        "",
        "Degerlendirme:",
    ]
    return "\n".join(satirlar)
