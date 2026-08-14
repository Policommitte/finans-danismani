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
from app.core.llm import get_llm_client
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
        ),
        AGENT_PORTFOLIO: PortfolioAgent(
            mcp_client=mcp_client,
            llm=build_agent_llm("portfolio"),
            timeout_seconds=settings.agent_timeout_seconds,
        ),
        AGENT_RISK_STRATEGY: RiskStrategyAgent(
            mcp_client=mcp_client,
            llm=build_agent_llm("risk"),
            timeout_seconds=settings.agent_timeout_seconds,
        ),
    }


def build_orchestrator(mcp_client: MCPClient | None = None, **kwargs) -> Orchestrator:
    """Uctan uca calismaya hazir orchestrator uretir.

    `synthesizer_llm` bilincli olarak BAGLANMAZ: sentez adimi token token
    akitmak icin LangChain uyumlu (`astream`) bir chat modeli bekler; ajanlarin
    kullandigi Gemini istemcisi ise tek seferlik `generate()` sunar. Model
    karari verilip LangChain uyumlu bir istemci secilene kadar orchestrator
    deterministik ozet uretir (bkz. `Orchestrator._fallback_response`) - akis,
    olaylar ve testler bundan etkilenmez.
    """
    client = mcp_client if mcp_client is not None else build_mcp_client()

    return Orchestrator(
        agents=build_agents(client),
        # Guvenlik ajanina model tanimliysa LLM verilir; degilse kural motoru
        # tek basina karar verir (fail-closed).
        security_agent=SecurityAgent(
            mcp_client=client,
            llm=build_agent_llm("security"),
            audit=get_audit_repository(),
        ),
        synthesizer_timeout_seconds=settings.synthesizer_timeout_seconds,
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
