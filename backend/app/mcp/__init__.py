"""MCP (Model Context Protocol) katmani.

Ajanlar veritabanina veya dis servislere DOGRUDAN erismez (NFR-04); tum veri
erisimi bu paketteki paylasilan `MCPClient` uzerinden tool cagrilariyla yapilir.
"""

from app.mcp.client import (
    MCPClient,
    MCPClientError,
    MCPServer,
    MCPServerNotFoundError,
    MCPToolExecutionError,
    MCPToolNotFoundError,
)

__all__ = [
    "MCPClient",
    "MCPClientError",
    "MCPServer",
    "MCPServerNotFoundError",
    "MCPToolExecutionError",
    "MCPToolNotFoundError",
]
