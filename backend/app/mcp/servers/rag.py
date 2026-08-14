"""MCP Server 1 (LlamaIndex RAG) icin mock tool handler.

Gercek LlamaIndex indeksi ve embedding pipeline'i hazir olana kadar,
MarketResearchAgent'in bagimsiz test edilebilmesi icin sabit bir sahte
haber/rapor kumesi uzerinden calisir.
"""

from __future__ import annotations

from typing import Any

from app.mcp.client import MCPServer

RAG_SERVER_NAME = "rag"

_MOCK_CHUNKS: list[dict[str, Any]] = [
    {
        "chunk_id": "news-thyao-2026-08-10-1",
        "text": (
            "THY, 2026 yili 2. ceyrek finansal sonuclarinda net karini bir onceki "
            "yilin ayni donemine gore %18 artirdi. Sirket, yolcu doluluk oraninin "
            "%84 seviyesine ulastigini acikladi."
        ),
        "source": "Dunya Gazetesi",
        "date": "2026-08-10",
        "metadata": {"symbol": "THYAO", "topic": "earnings"},
        "score": 0.91,
    },
    {
        "chunk_id": "kap-thyao-2026-08-10-2",
        "text": (
            "THYAO, KAP'a yaptigi aciklamada yakit maliyetlerindeki dususun "
            "karlilik uzerinde olumlu etkisi oldugunu belirtti."
        ),
        "source": "KAP",
        "date": "2026-08-10",
        "metadata": {"symbol": "THYAO", "topic": "disclosure"},
        "score": 0.86,
    },
    {
        "chunk_id": "news-asels-2026-07-22-1",
        "text": (
            "ASELSAN, savunma sanayii ihracat gelirlerinde yillik bazda %25 "
            "artis kaydettigini duyurdu."
        ),
        "source": "Anadolu Ajansi",
        "date": "2026-07-22",
        "metadata": {"symbol": "ASELS", "topic": "earnings"},
        "score": 0.88,
    },
]


async def rag_search(
    query: str,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """LlamaIndex'in yerini tutan sahte semantik arama.

    filters destekledigi anahtarlar: symbol, date_from, date_to (YYYY-MM-DD).
    Gercek implementasyon embedding benzerligiyle siralar; burada sabit
    'score' alanina gore siralanir.
    """
    filters = filters or {}
    candidates = _MOCK_CHUNKS

    symbol = filters.get("symbol")
    if symbol:
        candidates = [c for c in candidates if c["metadata"].get("symbol") == symbol.upper()]

    date_from = filters.get("date_from")
    if date_from:
        candidates = [c for c in candidates if c["date"] >= date_from]

    date_to = filters.get("date_to")
    if date_to:
        candidates = [c for c in candidates if c["date"] <= date_to]

    ranked = sorted(candidates, key=lambda c: c["score"], reverse=True)[: max(top_k, 0)]

    return {"query": query, "chunks": ranked}


def build_rag_server() -> MCPServer:
    server = MCPServer(name=RAG_SERVER_NAME)
    server.register_tool("rag_search", rag_search)
    return server
