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
