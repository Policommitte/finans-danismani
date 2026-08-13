"""Orchestrator'daki tum agent'larin paylastigi MCP tool-cagri katmani.

Bu, gercek Model Context Protocol'un (JSON-RPC / stdio / SSE) tam bir
implementasyonu degildir -- su an hicbir MCP sunucusu ayri bir surecte
calismiyor (LlamaIndex indeksi, Postgres, Borsa/KAP entegrasyonlari henuz
yok). Bunun yerine, agent'larin bagimli olacagi sozlesmeyi (call_tool)
saglayan, in-process bir yonlendirme/registry katmanidir:

    await mcp_client.call_tool(server="rag", tool="rag_search", arguments={...})

Ileride gercek bir sunucuya (orn. ayri bir MCP server sureci) baglanmak
gerektiginde, o sunucu icin MCPServer.call'i JSON-RPC uzerinden proxy'leyen
yeni bir MCPServer alt sinifi/adaptoru yazilip register_server ile eklenir;
BaseAgent ve alt siniflarinin (MarketResearchAgent dahil) kullandigi arayuz
degismez.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


class MCPClientError(Exception):
    """MCPClient uzerinden yapilan bir tool cagrisi basarisiz oldugunda fırlatılır."""


class MCPServerNotFoundError(MCPClientError):
    def __init__(self, server: str) -> None:
        super().__init__(f"MCP server bulunamadi: '{server}'")
        self.server = server


class MCPToolNotFoundError(MCPClientError):
    def __init__(self, server: str, tool: str) -> None:
        super().__init__(f"'{server}' sunucusunda tool bulunamadi: '{tool}'")
        self.server = server
        self.tool = tool


class MCPToolExecutionError(MCPClientError):
    def __init__(self, server: str, tool: str, cause: Exception) -> None:
        super().__init__(f"'{server}.{tool}' calisirken hata olustu: {cause}")
        self.server = server
        self.tool = tool
        self.cause = cause


class MCPServer:
    """Tek bir MCP sunucusunun (rag, market, portfolio, ...) tool kayit defteri."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._tools: dict[str, ToolHandler] = {}

    def register_tool(self, tool_name: str, handler: ToolHandler) -> None:
        self._tools[tool_name] = handler

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in self._tools:
            raise MCPToolNotFoundError(self.name, tool_name)
        try:
            return await self._tools[tool_name](**arguments)
        except MCPClientError:
            raise
        except Exception as exc:  # tool handler'in kendi hatasi
            raise MCPToolExecutionError(self.name, tool_name, exc) from exc


class MCPClient:
    """Agent'larin constructor'a enjekte edilerek kullandigi paylasilan istemci.

    Her agent kendi MCPClient'ini olusturmaz; Orchestrator tek bir MCPClient
    olusturup ilgili MCPServer'lari register eder, sonra ayni instance'i tum
    agent'lara (BaseAgent.__init__ uzerinden) verir. Sunucular adla adreslenir
    ("rag", "market", "portfolio", ...) boylece bir agent birden fazla
    sunucuya (orn. MarketResearchAgent -> "rag" ve "market") erisebilir.
    """

    def __init__(self, servers: dict[str, MCPServer] | None = None) -> None:
        self._servers: dict[str, MCPServer] = dict(servers or {})

    def register_server(self, server: MCPServer) -> None:
        self._servers[server.name] = server

    def has_server(self, server: str) -> bool:
        return server in self._servers

    async def call_tool(
        self, server: str, tool: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if server not in self._servers:
            raise MCPServerNotFoundError(server)
        return await self._servers[server].call(tool, arguments or {})
