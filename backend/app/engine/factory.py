"""Uygulama wiring'i: MCP client, ajanlar ve orchestrator tek yerden kurulur.

Orchestrator hicbir ajani kendisi olusturmaz (bkz. `orchestrator.py`); ajanlar
disaridan ENJEKTE edilir. Bu modul o enjeksiyonu yapan tek noktadir:

    orchestrator = build_orchestrator()

Boylece "hangi MCP sunuculari ayakta", "hangi ajan hangi modelle calisiyor"
sorularinin cevabi tek dosyada toplanir; FastAPI endpoint'i yalnizca hazir
orchestrator'i kullanir.
"""

from __future__ import annotations

import logging

from app.agents.base import BaseAgent
from app.agents.market_research import MarketResearchAgent
from app.agents.security_agent import SecurityAgent
from app.config import settings
from app.core.llm import get_llm_client
from app.engine.orchestrator import AGENT_MARKET_RESEARCH, Orchestrator
from app.mcp.client import MCPClient
from app.mcp.mock import build_mock_mcp_client

logger = logging.getLogger(__name__)


def build_mcp_client() -> MCPClient:
    """Uygulama genelinde TEK olan paylasilan MCP client'i uretir.

    Su an 'rag' ve 'market' sunuculari sahte veriyle kayitlidir. Gercek
    entegrasyonlar (LlamaIndex indeksi, Borsa/KAP API'leri, Postgres) hazir
    oldugunda yalnizca bu fonksiyon degisir; ajanlar ayni tool adlarini
    cagirmaya devam eder.
    """
    return build_mock_mcp_client()


def build_agent_llm(agent: str):
    """Ajan icin dil modeli uretir; anahtar yoksa `None` doner.

    LLM baglanmamis olmasi hata DEGILDIR: ajanlar LLM'siz de calisir
    (MarketResearchAgent bu durumda kaynaklardan deterministik alinti uretir).
    Bu sayede sistem API anahtari olmadan da uctan uca calistirilabilir.
    """
    if not settings.llm_api_key:
        logger.info("LLM anahtari tanimli degil, ajan LLM'siz calisacak", extra={"agent": agent})
        return None

    try:
        return get_llm_client(agent)
    except Exception:  # noqa: BLE001 - model kurulumu wiring'i dusurmemeli
        logger.exception("ajan icin LLM olusturulamadi", extra={"agent": agent})
        return None


def build_agents(mcp_client: MCPClient) -> dict[str, BaseAgent]:
    """Node adi -> ajan ornegi eslemesini uretir.

    Sozluk anahtarlari `orchestrator.py` icindeki node adi sabitleriyle AYNI
    olmak zorundadir; graph kenarlari bu adlardan uretilir. Portfoy ve risk
    ajanlari hazir olduklarinda buraya birer satir olarak eklenecektir - eksik
    ajan graph'i bozmaz.
    """
    return {
        AGENT_MARKET_RESEARCH: MarketResearchAgent(
            mcp_client=mcp_client,
            llm=build_agent_llm("market"),
            timeout_seconds=settings.agent_timeout_seconds,
        ),
    }


def build_orchestrator(mcp_client: MCPClient | None = None, **kwargs) -> Orchestrator:
    """Uctan uca calismaya hazir orchestrator uretir.

    `synthesizer_llm` bilincli olarak BAGLANMAZ: sentez adimi token token
    akitmak icin LangChain uyumlu (`astream`) bir chat modeli bekler; ajanlarin
    kullandigi Gemini istemcisi ise tek seferlik `generate()` sunar. Model
    entegrasyonu tamamlanana kadar orchestrator deterministik ozet uretir
    (bkz. `Orchestrator._fallback_response`).
    """
    client = mcp_client if mcp_client is not None else build_mcp_client()

    return Orchestrator(
        agents=build_agents(client),
        # Guvenlik ajanina henuz LLM verilmiyor: ikincil siniflandirici
        # (`SecurityAgent._classify_with_llm`) implemente edilmedigi icin model
        # baglamak yalnizca her denetimde gereksiz hata logu uretirdi. Kural
        # motoru yereldir ve fail-closed davranir; denetim calismaya devam eder.
        security_agent=SecurityAgent(mcp_client=client),
        synthesizer_timeout_seconds=settings.synthesizer_timeout_seconds,
        **kwargs,
    )
