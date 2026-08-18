"""MCP tool katmani testleri (§14-10).

En kritik iki kural (mimari v4 bolum 6):
  1. `user_id` tool SEMASINDA yoktur - LLM onu yazamaz, contextvar'dan gelir.
  2. Tum tool'lar ayni zarfi doner; zarf `MCPClient.call_tool` icinde acilir.
"""

import inspect

import pytest

from app.mcp.client import MCPClient, MCPToolExecutionError, mask_arguments
from app.mcp.context import MCPAuthorizationError, set_current_user_id
from app.mcp.server import (
    CORE_SERVER_NAME,
    MARKET_SERVER_NAME,
    RAG_SERVER_NAME,
    TOOL_GROUPS,
    build_servers,
    portfolio_get_summary,
    rag_search,
)

#: Mimari v4 bolum 6.2'deki tool katalogu.
KATALOG = {
    "user_get_profile",
    "portfolio_get_summary",
    "portfolio_get_holdings",
    "portfolio_get_allocation",
    "portfolio_get_transactions",
    "market_get_quote",
    "market_get_history",
    "rag_search",
}


@pytest.fixture
def mcp() -> MCPClient:
    client = MCPClient()
    for server in build_servers():
        client.register_server(server)
    return client


@pytest.fixture
def kimlik():
    """Tool cagrilari icin kimlik baglami (auth katmaninin yaptigi is)."""
    set_current_user_id(1)
    yield 1
    set_current_user_id(None)


def test_katalogdaki_tum_toollar_kayitli():
    kayitli = {tool for tools in TOOL_GROUPS.values() for tool in tools}

    assert KATALOG <= kayitli


@pytest.mark.parametrize("tool_adi", sorted(KATALOG))
def test_hicbir_tool_user_id_parametresi_almaz(tool_adi):
    """Prompt injection'in baskasinin verisini isteyebilmesini engelleyen kural."""
    handler = next(tools[tool_adi] for tools in TOOL_GROUPS.values() if tool_adi in tools)

    parametreler = set(inspect.signature(handler).parameters)
    assert "user_id" not in parametreler
    assert "portfolio_id" not in parametreler


@pytest.mark.db
async def test_tool_kimlik_baglami_yoksa_reddeder():
    """Fail-closed: kimlik cozulemediyse 'varsayilan kullanici' kacamagi YOK."""
    set_current_user_id(None)

    with pytest.raises(MCPAuthorizationError):
        await portfolio_get_summary()


@pytest.mark.db
async def test_tool_ortak_zarfi_doner(kimlik):
    sonuc = await portfolio_get_summary()

    assert set(sonuc) == {"ok", "data", "error"}
    assert sonuc["ok"] is True
    assert sonuc["error"] is None


@pytest.mark.db
async def test_client_zarfi_acar(mcp, kimlik):
    """Ajanlar `data` icerigini gorur; zarf sinirda acilir."""
    sonuc = await mcp.call_tool(CORE_SERVER_NAME, "portfolio_get_summary")

    assert "ok" not in sonuc
    assert sonuc["total_value_try"] > 0


@pytest.mark.db
async def test_basarisiz_zarf_tool_error_a_cevrilir(mcp, kimlik):
    """`ok=False` bir cokme degil ama ajan tarafinda `tool_error` olmali."""
    with pytest.raises(MCPToolExecutionError):
        await mcp.call_tool(MARKET_SERVER_NAME, "market_get_quote", {"symbol": "YOKBOYLE"})


async def test_zarfsiz_tool_ciktisi_oldugu_gibi_doner(mcp):
    """Zarf oncesi yazilmis tool'lar ve test sahteleri calismaya devam etmeli."""
    from app.mcp.client import MCPServer

    async def eski_usul(**_):
        return {"chunks": []}

    server = MCPServer(name="eski")
    server.register_tool("eski_tool", eski_usul)
    mcp.register_server(server)

    assert await mcp.call_tool("eski", "eski_tool") == {"chunks": []}


@pytest.mark.db
async def test_portfoy_toollari_kullanicinin_kendi_verisini_doner(kimlik):
    sonuc = await portfolio_get_summary()

    assert sonuc["data"]["holding_count"] == 3


@pytest.mark.db
async def test_baska_kullanici_baglaminda_baska_veri_doner():
    set_current_user_id(2)
    try:
        sonuc = await portfolio_get_summary()
        assert sonuc["data"]["holding_count"] == 2  # seed: 2 numarali kullanici
    finally:
        set_current_user_id(None)


@pytest.mark.db
async def test_rag_search_yapilandirilmis_doner(mcp):
    """Duz metin donerse kaynak metadata'si MCP sinirinda kaybolur (FR-RAG-04)."""
    sonuc = await mcp.call_tool(RAG_SERVER_NAME, "rag_search", {"query": "THYAO net kar"})

    chunk = sonuc["chunks"][0]
    assert {"doc_id", "baslik", "sirket", "symbol", "tarih", "tip", "content", "score"} <= set(
        chunk
    )


@pytest.mark.db
async def test_rag_search_eski_alan_adlarini_da_tasir(mcp):
    """MarketResearchAgent `title`/`text`/`date`/`metadata` bekliyor."""
    sonuc = await mcp.call_tool(RAG_SERVER_NAME, "rag_search", {"query": "THYAO net kar"})

    chunk = sonuc["chunks"][0]
    assert chunk["title"] == chunk["baslik"]
    assert chunk["text"] == chunk["content"]
    assert chunk["metadata"]["symbol"] == chunk["symbol"]


@pytest.mark.db
async def test_rag_search_filters_sozlugunu_de_kabul_eder():
    """Geriye donuk uyum: ajan `filters={"symbol": ...}` gonderiyor."""
    sonuc = await rag_search(query="maliyet", filters={"symbol": "SASA"})

    assert all(c["symbol"] == "SASA" for c in sonuc["data"]["chunks"])


@pytest.mark.db
async def test_market_get_history_ham_seri_yerine_ozet_doner(mcp):
    """LLM baglami sismesin diye (mimari v4 bolum 6.4)."""
    sonuc = await mcp.call_tool(
        MARKET_SERVER_NAME, "market_get_history", {"symbol": "THYAO", "days": 90}
    )

    # Asil kural: donen ornek sayisi ham seriden cok daha kucuk olmali.
    assert sonuc["point_count"] > 100
    assert len(sonuc["samples"]) <= 8
    assert sonuc["volatility_pct"] >= 0


@pytest.mark.db
async def test_tool_cagrisi_denetime_yazilir(kimlik):
    """`tool_calls` kaydi - denetim + demo icin (mimari v4 bolum 6.4)."""
    kayitlar: list[dict] = []

    class SahteDenetim:
        async def log_tool_call(self, record: dict) -> None:
            kayitlar.append(record)

    client = MCPClient(audit=SahteDenetim())
    for server in build_servers():
        client.register_server(server)

    await client.call_tool(CORE_SERVER_NAME, "portfolio_get_summary", agent="portfolio")

    assert len(kayitlar) == 1
    assert kayitlar[0]["agent_name"] == "portfolio"
    assert kayitlar[0]["tool_name"] == "core.portfolio_get_summary"
    assert kayitlar[0]["success"] is True
    assert kayitlar[0]["latency_ms"] >= 0


@pytest.mark.db
async def test_denetim_yazimi_cokerse_cagri_etkilenmez(kimlik):
    class BozukDenetim:
        async def log_tool_call(self, record: dict) -> None:
            raise RuntimeError("denetim veritabani kapali")

    client = MCPClient(audit=BozukDenetim())
    for server in build_servers():
        client.register_server(server)

    sonuc = await client.call_tool(CORE_SERVER_NAME, "portfolio_get_summary")

    assert sonuc["total_value_try"] > 0


def test_denetim_kaydinda_hassas_alanlar_maskelenir():
    maskeli = mask_arguments({"symbol": "THYAO", "password": "gizli", "query": "x" * 500})

    assert maskeli["symbol"] == "THYAO"
    assert maskeli["password"] == "***"
    assert maskeli["query"].endswith("...")
    assert len(maskeli["query"]) < 500
