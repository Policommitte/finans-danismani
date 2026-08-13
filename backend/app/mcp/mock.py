"""Gelistirme ve test icin sahte MCP kurulumu.

Gercek LlamaIndex / Borsa-KAP entegrasyonlari hazir olana kadar 'rag' ve
'market' sunucularini sahte veriyle ayaga kaldiran bir `MCPClient` uretir.
Gercek sunucular hazir oldugunda `app.engine.factory.build_mcp_client`
fabrikasi bu fonksiyonun yerine gercek wiring'i cagirir; ajanlar degismez.
"""

from __future__ import annotations

from app.mcp.client import MCPClient
from app.mcp.servers.market import build_market_server
from app.mcp.servers.rag import build_rag_server


def build_mock_mcp_client() -> MCPClient:
    client = MCPClient()
    client.register_server(build_rag_server())
    client.register_server(build_market_server())
    return client
