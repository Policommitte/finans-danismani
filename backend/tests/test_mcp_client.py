import asyncio

import pytest

from app.mcp.client import (
    MCPClient,
    MCPServer,
    MCPServerNotFoundError,
    MCPToolExecutionError,
    MCPToolNotFoundError,
)


def _run(coro):
    return asyncio.run(coro)


async def _echo(value: str) -> dict:
    return {"value": value}


async def _boom() -> dict:
    raise ValueError("bozuk tool")


def test_call_tool_returns_handler_result():
    server = MCPServer(name="demo")
    server.register_tool("echo", _echo)
    client = MCPClient({"demo": server})

    result = _run(client.call_tool(server="demo", tool="echo", arguments={"value": "merhaba"}))

    assert result == {"value": "merhaba"}


def test_unknown_server_raises():
    client = MCPClient()

    with pytest.raises(MCPServerNotFoundError):
        _run(client.call_tool(server="yok", tool="echo", arguments={}))


def test_unknown_tool_raises():
    server = MCPServer(name="demo")
    client = MCPClient({"demo": server})

    with pytest.raises(MCPToolNotFoundError):
        _run(client.call_tool(server="demo", tool="yok", arguments={}))


def test_tool_exception_is_wrapped():
    server = MCPServer(name="demo")
    server.register_tool("boom", _boom)
    client = MCPClient({"demo": server})

    with pytest.raises(MCPToolExecutionError):
        _run(client.call_tool(server="demo", tool="boom", arguments={}))


# ---------------------------------------------------------------------------
# Tool kesfi - BaseAgent.get_tools() sozlesmesi
# ---------------------------------------------------------------------------


def _iki_sunuculu_client() -> MCPClient:
    rag = MCPServer(name="rag")
    rag.register_tool("rag_search", _echo)

    market = MCPServer(name="market")
    market.register_tool("market_get_quote", _echo)
    market.register_tool("market_get_kap_disclosures", _echo)

    return MCPClient({"rag": rag, "market": market})


def test_get_tools_sunucu_bazli_listeler():
    tools = _run(_iki_sunuculu_client().get_tools(server="market"))

    assert {t["tool"] for t in tools} == {"market_get_quote", "market_get_kap_disclosures"}
    assert all(t["server"] == "market" for t in tools)


def test_get_tools_onek_filtresi_uygular():
    tools = _run(_iki_sunuculu_client().get_tools(prefix="rag_"))

    assert [t["tool"] for t in tools] == ["rag_search"]


def test_get_tools_filtresiz_tum_sunuculari_tarar():
    tools = _run(_iki_sunuculu_client().get_tools())

    assert len(tools) == 3


def test_get_tools_bilinmeyen_sunucuda_bos_liste_doner():
    """Kesif cagrisi hata firlatmamali; ajan tool'suz da calisabilmeli."""
    assert _run(_iki_sunuculu_client().get_tools(server="yok")) == []
