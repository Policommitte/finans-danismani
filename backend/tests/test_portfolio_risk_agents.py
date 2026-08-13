"""PortfolioAgent ve RiskStrategyAgent testleri (§14-9).

Iki ajan da LLM'SIZ calisabilmeli: model karari henuz verilmedi, bu yuzden
"model yoksa deterministik ozet" yolu birincil calisma modudur.
"""

import pytest

from app.agents.portfolio import PortfolioAgent
from app.agents.risk_strategy import RiskStrategyAgent
from app.mcp.client import MCPClient, MCPToolExecutionError
from app.mcp.context import set_current_user_id
from app.mcp.server import build_servers
from app.orchestration.models import AgentState


@pytest.fixture
def mcp() -> MCPClient:
    client = MCPClient()
    for server in build_servers():
        client.register_server(server)
    return client


@pytest.fixture(autouse=True)
def kimlik():
    set_current_user_id(1)
    yield
    set_current_user_id(None)


def _state(**kwargs) -> AgentState:
    kwargs.setdefault("user_query", "Portfoyum nasil?")
    return AgentState(user_id=1, thread_id=1, **kwargs)


# ---------------------------------------------------------------------------
# PortfolioAgent
# ---------------------------------------------------------------------------


async def test_portfoy_ajani_ozet_varlik_ve_dagilim_doner(mcp):
    sonuc = await PortfolioAgent(mcp_client=mcp).run(_state())

    veri = sonuc["portfolio_data"]
    assert veri["summary"]["total_value_try"] > 0
    assert len(veri["holdings"]) == 3
    assert veri["allocation"]


async def test_portfoy_ajani_llmsiz_deterministik_ozet_uretir(mcp):
    sonuc = await PortfolioAgent(mcp_client=mcp).run(_state())

    metin = sonuc["portfolio_data"]["summary_text"]
    assert "Portfoy toplam degeri" in metin
    assert "SASA" in metin  # zararda olan pozisyon belirtilmeli


async def test_portfoy_ajani_islem_gecmisini_yalnizca_istenince_ceker(mcp):
    ajan = PortfolioAgent(mcp_client=mcp)

    normal = await ajan.run(_state())
    istekli = await ajan.run(_state(user_query="Son işlem geçmişimi göster"))

    assert "transactions" not in normal["portfolio_data"]
    assert istekli["portfolio_data"]["transactions"]


async def test_portfoy_ajani_istenmediyse_calismaz(mcp):
    """Router baska ajan sectiyse ucuz no-op (tool cagrisi yapilmamali)."""
    sonuc = await PortfolioAgent(mcp_client=mcp).run(_state(requested_agents=["market_research"]))

    assert sonuc == {}


async def test_portfoy_ajani_tool_hatasini_agent_error_a_cevirir():
    """MCP cokerse akis DURMAZ; hata dogru kategoriyle raporlanir."""

    class BozukClient:
        async def call_tool(self, **_):
            raise MCPToolExecutionError("core", "portfolio_get_summary", RuntimeError("db down"))

        async def get_tools(self, **_):
            return []

    sonuc = await PortfolioAgent(mcp_client=BozukClient()).run(_state())

    assert sonuc["agent_errors"][0].error_type == "tool_error"


async def test_portfoy_ajani_piyasa_ve_rag_toollarina_erisemez(mcp):
    """Yetki ayrimi (mimari v4 bolum 6.3)."""
    tools = {t["tool"] for t in await PortfolioAgent(mcp_client=mcp).get_tools()}

    assert tools == {
        "portfolio_get_summary",
        "portfolio_get_holdings",
        "portfolio_get_allocation",
        "portfolio_get_transactions",
        "user_get_profile",
    }


# ---------------------------------------------------------------------------
# RiskStrategyAgent
# ---------------------------------------------------------------------------


async def test_risk_ajani_portfoy_verisi_olmadan_hata_dondurur(mcp):
    """SIRALI ajan: topoloji bozulursa sessizce yanlis skor uretmemeli."""
    sonuc = await RiskStrategyAgent(mcp_client=mcp).run(_state())

    assert sonuc["agent_errors"][0].error_type == "tool_error"
    assert "risk_data" not in sonuc


async def test_risk_ajani_skoru_servis_ile_ayni_hesaplar(mcp):
    portfoy = await PortfolioAgent(mcp_client=mcp).run(_state())
    sonuc = await RiskStrategyAgent(mcp_client=mcp).run(
        _state(portfolio_data=portfoy["portfolio_data"])
    )

    assert 0 < sonuc["risk_data"]["risk_score"] <= 100
    assert sonuc["risk_data"]["risk_tolerance"] == "HIGH"  # user_get_profile'dan geldi
    assert sonuc["risk_data"]["summary_text"]


async def test_risk_ajani_oynakligi_olcup_skora_katar(mcp):
    portfoy = await PortfolioAgent(mcp_client=mcp).run(_state())
    sonuc = await RiskStrategyAgent(mcp_client=mcp).run(
        _state(portfolio_data=portfoy["portfolio_data"])
    )

    assert sonuc["risk_data"]["avg_volatility_pct"] is not None
    assert sonuc["risk_data"]["components"]["volatility"] > 0


async def test_risk_ajani_istenmediyse_calismaz(mcp):
    sonuc = await RiskStrategyAgent(mcp_client=mcp).run(
        _state(requested_agents=["portfolio"], portfolio_data={"holdings": []})
    )

    assert sonuc == {}


async def test_risk_ajani_portfoy_toollarina_erisemez(mcp):
    """Risk ajani portfoy verisini state'ten alir, tekrar cekmez."""
    tools = {t["tool"] for t in await RiskStrategyAgent(mcp_client=mcp).get_tools()}

    assert tools == {"user_get_profile", "market_get_history"}
