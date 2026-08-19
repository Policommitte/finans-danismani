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

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

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

    def __init__(self, servers: dict[str, MCPServer] | None = None, audit=None) -> None:
        """
        Args:
            servers: Ad -> sunucu eslemesi.
            audit: `log_tool_call(record)` metoduna sahip denetim deposu
                (`app.repositories.base.AuditRepository`). Verilmezse denetim
                kaydi yalnizca loga yazilir. Denetim yazimi cagriyi ASLA
                dusurmez.
        """
        self._servers: dict[str, MCPServer] = dict(servers or {})
        self._audit = audit

    def     register_server(self, server: MCPServer) -> None:
        self._servers[server.name] = server

    def has_server(self, server: str) -> bool:
        return server in self._servers

    def server_names(self) -> list[str]:
        return list(self._servers)

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any] | None = None,
        agent: str = "system",
    ) -> dict[str, Any]:
        """Tool'u calistirir, ORTAK ZARFI ACAR ve cagriyi denetime yazar.

        Tool sozlesmesi `{"ok": ..., "data": ..., "error": ...}` zarfidir
        (mimari v4 bolum 6.2). Zarfi her ajanda tek tek acmak yerine sinir
        burasidir:

          * `ok=True`  -> `data` icerigi donulur.
          * `ok=False` -> `MCPToolExecutionError` firlatilir; `BaseAgent.run()`
            bunu `error_type="tool_error"` olan bir `AgentError`'a cevirir ve
            akis kesilmeden devam eder.

        Zarf TASIMAYAN cikti oldugu gibi donulur; boylece test/mock sunuculari
        ve zarf oncesi yazilmis tool'lar calismaya devam eder.
        """
        if server not in self._servers:
            raise MCPServerNotFoundError(server)

        baslangic = time.perf_counter()
        try:
            ham = await self._servers[server].call(tool, arguments or {})
        except MCPClientError as exc:
            await self._audit_call(agent, server, tool, arguments, False, baslangic, str(exc))
            raise

        if isinstance(ham, dict) and "ok" in ham:
            if not ham.get("ok"):
                hata = str(ham.get("error") or "Tool basarisiz sonuc dondurdu.")
                await self._audit_call(agent, server, tool, arguments, False, baslangic, hata)
                raise MCPToolExecutionError(server, tool, RuntimeError(hata))
            sonuc = ham.get("data") or {}
        else:
            sonuc = ham

        await self._audit_call(agent, server, tool, arguments, True, baslangic, None)
        return sonuc

    async def _audit_call(
        self,
        agent: str,
        server: str,
        tool: str,
        arguments: dict[str, Any] | None,
        success: bool,
        baslangic: float,
        error: str | None,
    ) -> None:
        """`tool_calls` kaydi (mimari v4 bolum 6.4).

        Denetim yazimi basarisiz olursa cagri ETKILENMEZ - hata yutulup
        loglanir. Argumanlar maskelenerek yazilir (PII sizintisi kontrolu).
        """
        if self._audit is None:
            return

        from app.mcp.context import get_current_user_id, get_request_id, get_session_id

        try:
            await self._audit.log_tool_call(
                {
                    "request_id": get_request_id() or None,
                    "session_id": get_session_id(),
                    "user_id": get_current_user_id(),
                    "agent_name": agent,
                    "tool_name": f"{server}.{tool}",
                    "args": mask_arguments(arguments or {}),
                    "success": success,
                    "latency_ms": round((time.perf_counter() - baslangic) * 1000, 2),
                    "error": error,
                }
            )
        except Exception:  # noqa: BLE001 - denetim akisi durdurmamali
            logger.exception("tool cagrisi denetime yazilamadi")

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


#: `tool_calls.args` icinde ASLA saklanmayacak alan adlari (PII / sir).
_MASKED_KEYS = frozenset(
    {"password", "sifre", "parola", "token", "api_key", "secret", "email", "tckn", "iban", "phone"}
)

#: Uzun serbest metinler (kullanici sorgusu, RAG icerigi) denetim kaydinda
#: kirpilir; tablo sismesin ve icerik sizmasin.
_MAX_AUDIT_VALUE = 200


def mask_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Tool argumanlarini denetim kaydi icin maskeler/kirpar."""
    masked: dict[str, Any] = {}
    for key, value in arguments.items():
        if key.lower() in _MASKED_KEYS:
            masked[key] = "***"
        elif isinstance(value, str) and len(value) > _MAX_AUDIT_VALUE:
            masked[key] = value[:_MAX_AUDIT_VALUE] + "..."
        elif isinstance(value, dict):
            masked[key] = mask_arguments(value)
        else:
            masked[key] = value
    return masked
