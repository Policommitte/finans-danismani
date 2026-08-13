"""Tum ajanlarin paylastigi MCP tool-cagri katmani.

Bu, gercek Model Context Protocol'un (JSON-RPC / stdio / SSE) tam bir
implementasyonu degildir -- su an hicbir MCP sunucusu ayri bir surecte
calismiyor (LlamaIndex indeksi, Postgres, Borsa/KAP entegrasyonlari henuz
yok). Bunun yerine, ajanlarin bagimli olacagi sozlesmeyi (`call_tool`)
saglayan, in-process bir yonlendirme/registry katmanidir:

    await mcp_client.call_tool(server="rag", tool="rag_search", arguments={...})

Ileride gercek bir sunucuya (orn. ayri bir MCP server sureci) baglanmak
gerektiginde, o sunucu icin `MCPServer.call`'i JSON-RPC uzerinden proxy'leyen
yeni bir `MCPServer` alt sinifi/adaptoru yazilip `register_server` ile eklenir;
`BaseAgent` ve alt siniflarinin kullandigi arayuz degismez.

TOOL KESFI
    `BaseAgent.get_tools()` sozlesmesi bir onek (prefix) filtresi bekler; bu
    yuzden istemci hem sunucu bazli hem onek bazli listeleme sunar:

        await client.get_tools(prefix="market_")          # tum sunucularda tara
        await client.get_tools(server="rag")              # tek sunucunun tool'lari

    Donen her kayit `{"server": ..., "tool": ...}` seklindedir; bir tool'un
    hangi sunucuda oldugu bilgisi kaybolmaz.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


class MCPClientError(Exception):
    """MCPClient uzerinden yapilan bir tool cagrisi basarisiz oldugunda firlatilir.

    NOT: `BaseAgent.run()` bu istisnayi ozel olarak yakalar ve
    `AgentError(error_type="tool_error")` uretir; boylece bir tool cokmesi
    "bilinmeyen hata" olarak degil, dogru kategoriyle raporlanir.
    """


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

    def tool_names(self) -> list[str]:
        """Bu sunucuda kayitli tool adlari (kesif icin)."""
        return list(self._tools)

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
    """Ajanlarin constructor'a enjekte edilerek kullandigi PAYLASILAN istemci.

    Her ajan kendi MCPClient'ini olusturmaz; uygulama tek bir MCPClient olusturup
    ilgili MCPServer'lari register eder, sonra ayni instance'i tum ajanlara
    (`BaseAgent.__init__` uzerinden) verir. Sunucular adla adreslenir
    ("rag", "market", "portfolio", ...) boylece bir ajan birden fazla sunucuya
    (orn. MarketResearchAgent -> "rag" ve "market") erisebilir.
    """

    def __init__(self, servers: dict[str, MCPServer] | None = None) -> None:
        self._servers: dict[str, MCPServer] = dict(servers or {})

    def register_server(self, server: MCPServer) -> None:
        self._servers[server.name] = server

    def has_server(self, server: str) -> bool:
        return server in self._servers

    def server_names(self) -> list[str]:
        return list(self._servers)

    async def call_tool(
        self, server: str, tool: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if server not in self._servers:
            raise MCPServerNotFoundError(server)
        return await self._servers[server].call(tool, arguments or {})

    async def get_tools(
        self, prefix: str | None = None, server: str | None = None
    ) -> list[dict[str, str]]:
        """Kayitli tool'lari `{"server": ..., "tool": ...}` kayitlari halinde doner.

        `BaseAgent.get_tools()` bu metodu onek filtresiyle cagirir. Gercek bir MCP
        sunucusuna gecildiginde listeleme bir ag cagrisina donusecegi icin metot
        simdiden `async` tanimlanmistir.

        Args:
            prefix: Yalnizca bu onekle baslayan tool'lar doner (orn. "market_").
            server: Yalnizca bu sunucudaki tool'lar taranir. Bilinmeyen sunucu
                adi verilirse bos liste doner (kesif cagrisi hata firlatmamali).
        """
        if server is not None:
            targets = [self._servers[server]] if server in self._servers else []
        else:
            targets = list(self._servers.values())

        return [
            {"server": srv.name, "tool": tool_name}
            for srv in targets
            for tool_name in srv.tool_names()
            if prefix is None or tool_name.startswith(prefix)
        ]
