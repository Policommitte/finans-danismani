"""Tum ajanlarin turedigi soyut temel sinif.

Bu dosya bir SOZLESME dosyasidir: orchestrator, kendisine enjekte edilen her
ajanin `name` ozelligine ve `run(state) -> dict` metoduna sahip oldugunu
varsayar. Buradaki taban sinifi ajanlarin ortak davranisini (timeout, hata
yakalama, MCP tool cagrisi, LLM erisimi) merkezilestirir.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod

from app.config import settings
from app.mcp.client import MCPClientError
from app.orchestration.models import AgentError, AgentState, ToolResult

logger = logging.getLogger(__name__)


class AgentLLMTimeout(TimeoutError):
    """Ajan ICINDEKI LLM cagrisi kendi butcesini asti.

    `asyncio.TimeoutError`'dan turer ama ondan AYIRT EDILEBILIR olmasi
    onemlidir: `BaseAgent.run()` dis zaman asimini yakalayip ajani komple
    "timeout" olarak isaretler, oysa bu istisna ajan ICINDE yakalanip
    deterministik ozete dusulmesi gereken - yani veriyi KURTARAN - durumdur.
    """


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

    def __init__(
        self,
        mcp_client,
        llm,
        timeout_seconds: int,
        llm_timeout_seconds: int | None = None,
    ) -> None:
        """
        Args:
            mcp_client: Uygulama genelinde TEK olan paylasilan MCP client.
                Ajanlar veritabanina dogrudan erismez (NFR-04); tum veri
                erisimi bu client uzerinden MCP tool'lari ile yapilir.
            llm: Bu ajana atanmis dil modeli. Ajan bazli model konfigurasyonu
                sayesinde ucuz modeller ajanlarda, guclu model synthesizer'da
                kullanilir (ucretsiz API kotasi korunur).
            timeout_seconds: DIS sinir - ajanin tamaminin ust siniri
                (`run()` icinde uygulanir). Emniyet subabidir.
            llm_timeout_seconds: IC sinir - yalnizca LLM cagrisini sarar
                (`generate()` icinde). `None` ise konfigurasyondan hesaplanir.
                Dis sinirdan KUCUK olmalidir; bkz. `Settings.
                agent_llm_budget_seconds`.
        """
        self.mcp_client = mcp_client
        self.llm = llm
        self.timeout_seconds = timeout_seconds
        # Ic sinir HER ZAMAN bu ajanin KENDI dis sinirindan kucuk tutulur.
        # Global butce yeterli degil: `SecurityAgent` varsayilan 10 sn ile
        # kurulur, global butce ise 27 sn olabilir - kirpilmasaydi dis iptal
        # once devreye girer ve ic sinir hic tetiklenmezdi.
        self.llm_timeout_seconds = max(
            3,
            min(
                (
                    llm_timeout_seconds
                    if llm_timeout_seconds is not None
                    else settings.agent_llm_budget_seconds
                ),
                timeout_seconds - 2,
            ),
        )

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
        except MCPClientError as exc:
            # MCP tool cagrisi coktu (sunucu/tool yok veya handler hata verdi).
            # "unknown" yerine dogru kategoriyle raporlanir; boylece loglarda
            # veri erisim sorunlari ile kod hatalari birbirine karismaz.
            logger.warning(
                "ajan mcp tool cagrisinda basarisiz oldu",
                extra={"agent": self.name, "hata": str(exc)},
            )
            return {
                "agent_errors": [
                    AgentError(
                        agent_name=self.name,
                        error_type="tool_error",
                        message=str(exc),
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
        filtre gerekiyorsa alt sinif bu metodu ezer - ornegin
        `MarketResearchAgent` iki ayri sunucudan (rag + market) tool kullandigi
        icin ad onegi filtresi yerine sunucu bazli listeleme yapar.
        """
        if self.mcp_client is None:
            return []
        return await self.mcp_client.get_tools(prefix=f"{self.name}_")

    async def call_tool(self, server: str, tool: str, arguments: dict | None = None) -> dict:
        """Paylasilan MCP client uzerinden tool cagirir ve gecikmeyi olcer.

        Ajanlar `self.mcp_client.call_tool(...)` yerine bu metodu kullanir;
        boylece her cagri icin `latency_ms` tek bir yerde loglanir (NFR-05
        izlenebilirlik) ve ileride yeniden deneme/onbellek gibi davranislar
        ajanlar degismeden buraya eklenebilir.

        Hata firlatirsa (`MCPClientError`) bilerek YUKARI birakilir: `run()`
        bunu yakalayip `error_type="tool_error"` olan bir `AgentError`'a cevirir
        ve akis kesilmeden devam eder.
        """
        if self.mcp_client is None:
            raise MCPClientError(f"'{self.name}' ajani icin MCP client baglanmadi.")

        baslangic = time.perf_counter()
        try:
            output = await self.mcp_client.call_tool(
                server=server, tool=tool, arguments=arguments, agent=self.name
            )
        except MCPClientError as exc:
            self._log_tool_result(
                ToolResult(
                    tool_name=f"{server}.{tool}",
                    output={},
                    latency_ms=self._gecen_ms(baslangic),
                    success=False,
                    error=str(exc),
                )
            )
            raise

        self._log_tool_result(
            ToolResult(
                tool_name=f"{server}.{tool}",
                output=output,
                latency_ms=self._gecen_ms(baslangic),
            )
        )
        return output

    async def generate(self, prompt: str) -> str:
        """Ajana atanmis dil modelini tek bir prompt ile calistirir.

        Iki farkli LLM arayuzunu birden destekler:
          * `generate(prompt)` -> `app.core.llm.LLMClient` protokolu (Gemini).
          * `ainvoke(prompt)`  -> LangChain chat modelleri.

        Boylece ajanlar hangi saglayicinin bagli oldugunu bilmek zorunda kalmaz.
        Cagri basarisiz olursa istisna yukari birakilir; ajan bunu yakalayip
        `error_type="llm_error"` uretebilir ya da deterministik bir alternatife
        dusebilir.

        ⚠️ CAGRI KENDI ZAMAN SINIRIYLA SARILIR (`llm_timeout_seconds`) ve
        asilirsa `AgentLLMTimeout` firlar. Bu, ajanin `_execute`'unu saran DIS
        sinirdan (`run()`) BILINCLI OLARAK AYRIDIR:

            dis sinir asilir  -> tum `_execute` iptal olur, o ana kadar
                                 hesaplanmis veri de KAYBOLUR
            ic sinir asilir   -> yalnizca bu cagri iptal olur; ajan istisnayi
                                 yakalayip deterministik ozete duser ve
                                 HESAPLANMIS VERIYI DONDURUR

        Ikinci davranis dogru olandir: rakamlar MCP tool'lariyla zaten
        hesaplanmistir, yalnizca yorum metni eksik kalir. Gerekce icin
        `Settings.agent_timeout_seconds` yanindaki nota bakin.
        """
        if self.llm is None:
            raise RuntimeError(f"'{self.name}' ajani icin LLM baglanmadi.")

        if hasattr(self.llm, "generate"):
            cagri = self.llm.generate(prompt)
        elif hasattr(self.llm, "ainvoke"):
            cagri = self._ainvoke_metni(prompt)
        else:
            raise RuntimeError(
                f"'{self.name}' ajanina verilen LLM nesnesi generate()/ainvoke() sunmuyor."
            )

        try:
            return await asyncio.wait_for(cagri, timeout=self.llm_timeout_seconds)
        except asyncio.TimeoutError as exc:
            logger.warning(
                "ajan ici LLM cagrisi zaman asimina ugradi, deterministik ozete dusulecek",
                extra={"agent": self.name, "limit_sn": self.llm_timeout_seconds},
            )
            raise AgentLLMTimeout(
                f"Model {self.llm_timeout_seconds} saniyede yanit vermedi; "
                f"hesaplanan veriler korundu, yalnizca yorum metni uretilemedi."
            ) from exc

    async def _ainvoke_metni(self, prompt: str) -> str:
        """LangChain chat modeli yanitini duz metne cevirir."""
        response = await self.llm.ainvoke(prompt)
        return str(getattr(response, "content", response))

    def _log_tool_result(self, result: ToolResult) -> None:
        """Tool cagrisinin sonucunu yapisal logla (icerik degil, metrik)."""
        logger.info(
            "mcp tool cagrisi",
            extra={
                "agent": self.name,
                "tool": result.tool_name,
                "latency_ms": result.latency_ms,
                "success": result.success,
            },
        )

    @staticmethod
    def _gecen_ms(baslangic: float) -> float:
        return round((time.perf_counter() - baslangic) * 1000, 2)

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
