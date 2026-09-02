"""Uygulama wiring'i: MCP client, ajanlar ve orchestrator tek yerden kurulur.

Orchestrator hicbir ajani kendisi olusturmaz (bkz. `orchestrator.py`); ajanlar
disaridan ENJEKTE edilir. Bu modul o enjeksiyonu yapan tek noktadir:

    orchestrator = build_orchestrator()

Boylece "hangi MCP tool'lari kayitli", "hangi ajan hangi modelle calisiyor"
sorularinin cevabi tek dosyada toplanir; FastAPI endpoint'i yalnizca hazir
orchestrator'i kullanir.

⚠️ MODEL KARARI HENUZ VERILMEDI: `build_agent_llm` model adi tanimli degilse
`None` doner ve ajanlar LLM'siz calisir. Sistem bu haliyle uctan uca calisir;
model secildiginde `.env` disinda hicbir sey degismez.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.agents.base import BaseAgent
from app.agents.market_research import MarketResearchAgent
from app.agents.portfolio import PortfolioAgent
from app.agents.risk_strategy import RiskStrategyAgent
from app.agents.security_agent import SecurityAgent
from app.config import settings
from app.core.llm import get_llm_client, get_streaming_llm
from app.engine.orchestrator import (
    AGENT_MARKET_RESEARCH,
    AGENT_PORTFOLIO,
    AGENT_RISK_STRATEGY,
    Orchestrator,
)
from app.mcp.client import MCPClient
from app.mcp.server import build_servers
from app.repositories.deps import get_audit_repository

logger = logging.getLogger(__name__)


def build_mcp_client() -> MCPClient:
    """Uygulama genelinde TEK olan paylasilan MCP client'i uretir.

    Tool'lar `app/mcp/server.py` icinde tanimlidir ve repository katmanina
    konusur; yani DB bagliysa Postgres'e, degilse bellek ici veriye giderler.
    Ajanlar bu ayrimi GORMEZ.
    """
    client = MCPClient(audit=get_audit_repository())
    for server in build_servers():
        client.register_server(server)
    return client


def build_agent_llm(agent: str):
    """Ajan icin dil modeli uretir; anahtar veya model tanimli degilse `None`.

    LLM baglanmamis olmasi hata DEGILDIR: ajanlar LLM'siz de calisir
    (deterministik ozet/alinti uretirler). Bu sayede sistem API anahtari ve
    model karari olmadan da uctan uca calistirilabilir.
    """
    try:
        return get_llm_client(agent)
    except Exception:  # noqa: BLE001 - model kurulumu wiring'i dusurmemeli
        logger.exception("ajan icin LLM olusturulamadi", extra={"agent": agent})
        return None


def build_synthesizer_llm():
    """Sentez adimi icin model; iki kademeli.

    1. `get_streaming_llm` -> LangChain `ChatOpenAI` (NIM). Token token akar.
    2. Kurulamazsa `build_agent_llm` -> tek seferlik istemci. Sentez YINE LLM
       ile yapilir, yalnizca akis olmaz: `stream_request` token uretilmeyen
       yollarda nihai metni tek bir token olayi olarak gonderir, yani frontend
       icin davranis degismez - metin bir anda belirir.
    3. O da yoksa `None` -> `Orchestrator._fallback_response` (deterministik).

    ⚠️ 3. KADEME UZUN SURE FARK EDILMEDI. `build_orchestrator` eskiden
    `synthesizer_llm`'i HIC gecmiyordu; `.env` icindeki `SYNTHESIZER_MODEL`
    okunuyor ama kullanilmiyordu. Sonuc: yanitlar her zaman deterministik
    birlestirmeydi ("Portfoy analizi: ... Piyasa arastirmasi: ...") ve sentez
    LLM'i hic calismamisti. Model adini degistirmek tek basina bir sey
    degistirmiyordu - bu fonksiyon o baglantiyi kuruyor.
    """
    try:
        akitan = get_streaming_llm("synthesizer")
    except Exception:  # noqa: BLE001 - model kurulumu wiring'i dusurmemeli
        logger.exception("akitan sentez modeli olusturulamadi")
        akitan = None

    if akitan is not None:
        return akitan

    return build_agent_llm("synthesizer")


def build_agents(mcp_client: MCPClient) -> dict[str, BaseAgent]:
    """Node adi -> ajan ornegi eslemesi.

    Sozluk anahtarlari `orchestrator.py` icindeki node adi sabitleriyle AYNI
    olmak zorundadir; graph kenarlari bu adlardan uretilir.
    """
    return {
        AGENT_MARKET_RESEARCH: MarketResearchAgent(
            mcp_client=mcp_client,
            llm=build_agent_llm("market"),
            timeout_seconds=settings.agent_timeout_seconds,
            llm_timeout_seconds=settings.agent_llm_budget_seconds,
        ),
        AGENT_PORTFOLIO: PortfolioAgent(
            mcp_client=mcp_client,
            llm=build_agent_llm("portfolio"),
            timeout_seconds=settings.agent_timeout_seconds,
            llm_timeout_seconds=settings.agent_llm_budget_seconds,
        ),
        AGENT_RISK_STRATEGY: RiskStrategyAgent(
            mcp_client=mcp_client,
            llm=build_agent_llm("risk"),
            timeout_seconds=settings.agent_timeout_seconds,
            llm_timeout_seconds=settings.agent_llm_budget_seconds,
        ),
    }


def build_orchestrator(mcp_client: MCPClient | None = None, **kwargs) -> Orchestrator:
    """Uctan uca calismaya hazir orchestrator uretir.

    `synthesizer_llm` artik BAGLANIYOR (bkz. `build_synthesizer_llm`).
    Cagiran taraf `synthesizer_llm=` gecerek bunu ezebilir - testler oyle
    yapiyor.
    """
    client = mcp_client if mcp_client is not None else build_mcp_client()

    kwargs.setdefault("synthesizer_llm", build_synthesizer_llm())

    return Orchestrator(
        agents=build_agents(client),
        # Guvenlik ajanina model tanimliysa LLM verilir; degilse kural motoru
        # tek basina karar verir (fail-closed).
        security_agent=SecurityAgent(
            mcp_client=client,
            llm=build_agent_llm("security"),
            audit=get_audit_repository(),
        ),
        # LLM kapsam suzgeci ayni kucuk/hizli modeli kullanir (SECURITY_MODEL).
        # Model tanimli degilse None doner ve suzgec sessizce kapali kalir -
        # kapsam karari yalnizca kapsam.py kurallarinda verilir (fail-open).
        scope_llm=build_agent_llm("security") if settings.scope_llm_enabled else None,
        synthesizer_timeout_seconds=settings.synthesizer_timeout_seconds,
        synthesizer_stall_seconds=settings.synthesizer_stall_seconds,
        **kwargs,
    )


@lru_cache
def get_orchestrator() -> Orchestrator:
    """Uygulama omru boyunca TEK orchestrator.

    Her istekte yeniden kurulsaydi LangGraph graph'i tekrar derlenir ve
    checkpointer (konusma gecmisi) sifirlanirdi - cok turlu baglam
    (FR-CHAT-03) calismazdi.
    """
    return build_orchestrator()
