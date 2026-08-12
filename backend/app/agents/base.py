"""Tum ajanlarin turedigi soyut temel sinif.

Bu dosya bir SOZLESME dosyasidir: orchestrator, kendisine enjekte edilen her
ajanin `name` ozelligine ve `run(state) -> dict` metoduna sahip oldugunu
varsayar. Gercek ajan implementasyonlari (MarketResearchAgent, PortfolioAgent,
RiskStrategyAgent) ayri bir calisma dalinda gelistirilmektedir; buradaki taban
sinifi onlarin ortak davranisini (timeout, hata yakalama) merkezilestirir.
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from app.schema.models import AgentError, AgentState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Ajanlarin ortak davranisini tasiyan soyut sinif.

    NOT: `run()` AgentState degil, DICT dondurur. LangGraph node'lari yalnizca
    DEGISEN alanlari iceren bir sozluk dondurur; tum state'i dondurmek paralel
    calismada uzerine yazma (overwrite) hatasina yol acar.

    Alt siniflarin yapmasi gereken tek sey `_execute()` metodunu yazmaktir;
    timeout ve hata yonetimini bu sinif ustlenir.
    """

    #: Graph icindeki node adi. Alt siniflar mutlaka doldurur.
    name: str = "base"

    def __init__(self, mcp_client, llm, timeout_seconds: int) -> None:
        """
        Args:
            mcp_client: Uygulama genelinde TEK olan paylasilan MCP client.
                Ajanlar veritabanina dogrudan erismez (NFR-04); tum veri
                erisimi bu client uzerinden MCP tool'lari ile yapilir.
            llm: Bu ajana atanmis dil modeli. Ajan bazli model konfigurasyonu
                sayesinde ucuz modeller ajanlarda, guclu model synthesizer'da
                kullanilir (ucretsiz API kotasi korunur).
            timeout_seconds: Ajanin en fazla ne kadar calisabilecegi.
        """
        self.mcp_client = mcp_client
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def _execute(self, state: AgentState) -> dict:
        """Asil is mantigi. Alt siniflar bunu uygular.

        Yalnizca degistirdigi state alanlarini iceren bir sozluk dondurmelidir.
        Ornek: ``{"portfolio_data": {...}}``
        """
        ...

    async def run(self, state: AgentState) -> dict:
        """LangGraph node fonksiyonu.

        Timeout ve hata yakalama burada MERKEZI olarak yapilir: bir ajan
        cokerse akis DEVAM eder ve hata `agent_errors` alanina yazilir.
        Synthesizer daha sonra bu listeye bakip eksik veriyi durustce belirtir.
        Boylece tek bir ajanin cokmesi tum istegi dusurmez.
        """
        try:
            return await asyncio.wait_for(self._execute(state), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("ajan zaman asimina ugradi", extra={"agent": self.name})
            return {
                "agent_errors": [
                    AgentError(
                        agent_name=self.name,
                        error_type="timeout",
                        message=f"{self.timeout_seconds}s icinde yanit alinamadi",
                    )
                ]
            }
        except Exception as exc:  # noqa: BLE001 - ajan hatasi akisi durdurmamali
            logger.exception("ajan beklenmeyen hata verdi", extra={"agent": self.name})
            return {
                "agent_errors": [
                    AgentError(
                        agent_name=self.name,
                        error_type="unknown",
                        message=str(exc),
                    )
                ]
            }

    async def get_tools(self) -> list:
        """Ajanin kullanacagi MCP tool alt kumesini doner.

        Varsayilan davranis: ajanin adiyla ayni onege sahip tool'lari getirir
        (ornegin `portfolio` ajani -> `portfolio_*` tool grubu). Farkli bir
        filtre gerekiyorsa alt sinif bu metodu ezer.
        """
        if self.mcp_client is None:
            return []
        return await self.mcp_client.get_tools(prefix=f"{self.name}_")

    def is_requested(self, state: AgentState) -> bool:
        """Bu ajanin mevcut sorgu icin calismasi anlamli mi?

        Router node'u `requested_agents` listesini doldurur. Kenarlar statik
        oldugu icin ajan yine de cagrilir; ancak bu kontrol sayesinde ajan
        kendini erken sonlandirabilir (ucuz no-op) ve gereksiz LLM/tool
        cagrisi yapilmaz.

        Liste bos ise (router henuz calismadi veya karar veremedi) guvenli
        varsayilan olarak True doner - yani ajan calisir.
        """
        if not state.requested_agents:
            return True
        return self.name in state.requested_agents
