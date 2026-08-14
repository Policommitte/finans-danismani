"""MCP Server 3 (Borsa & KAP canli veri) icin mock tool handler'lar.

Gercek borsa/KAP API entegrasyonu hazir olana kadar, MarketResearchAgent'in
bagimsiz test edilebilmesi icin sabit bir sahte fiyat/aciklama kumesi
uzerinden calisir. Bu yol bir RAG/embedding islemi degildir; dogrudan
yapisal veri dondurur.
"""

from __future__ import annotations

# NOT: `datetime.UTC` kisayolu 3.11+ ile geldi; CI 3.13 kullansa da yerel
# gelistirme ortamlari 3.10 olabildigi icin esdegeri olan `timezone.utc`
# tercih edildi.
from datetime import datetime, timezone
from typing import Any

from app.mcp.client import MCPServer

MARKET_SERVER_NAME = "market"

_MOCK_QUOTES: dict[str, dict[str, Any]] = {
    "THYAO": {"price": 312.50, "currency": "TRY", "change_percent": 1.85},
    "ASELS": {"price": 68.90, "currency": "TRY", "change_percent": -0.72},
}

_MOCK_DISCLOSURES: dict[str, list[dict[str, Any]]] = {
    "THYAO": [
        {
            "disclosure_id": "kap-thyao-2026-08-10-1",
            "title": "2026 2. Ceyrek Finansal Sonuclari",
            "summary": (
                "Sirket, 2026 2. ceyrek net karinin bir onceki yila gore %18 " "arttigini acikladi."
            ),
            "date": "2026-08-10",
        }
    ],
}


async def market_get_quote(symbol: str) -> dict[str, Any]:
    """Guncel fiyat teklifini dondurur. Sembol bilinmiyorsa found=False doner."""
    quote = _MOCK_QUOTES.get(symbol.upper())
    if quote is None:
        return {"symbol": symbol.upper(), "found": False}
    return {
        "symbol": symbol.upper(),
        "found": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **quote,
    }


async def market_get_kap_disclosures(symbol: str, since: str | None = None) -> dict[str, Any]:
    """Sembole ait KAP bildirimlerini (en yeniden eskiye) dondurur."""
    disclosures = list(_MOCK_DISCLOSURES.get(symbol.upper(), []))
    if since:
        disclosures = [d for d in disclosures if d["date"] >= since]
    return {"symbol": symbol.upper(), "disclosures": disclosures}


def build_market_server() -> MCPServer:
    server = MCPServer(name=MARKET_SERVER_NAME)
    server.register_tool("market_get_quote", market_get_quote)
    server.register_tool("market_get_kap_disclosures", market_get_kap_disclosures)
    return server
