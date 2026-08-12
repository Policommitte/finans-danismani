"""MarketResearchAgent: piyasa haberleri/rapor RAG'i (MCP Server 1) ve
canli fiyat/KAP verisi (MCP Server 3) icin sorumlu agent.

Bu, MCP Server 2'ye (Portfoy DB) hicbir sekilde erismeyen tek agent'tir --
o sunucu PortfolioAgent'in sorumlulugundadir. Bu agent Server 1 ve Server 3'e
birlikte erisen tek agent'tir.

Router/Orchestrator henuz bu repoda yok, dolayisiyla task icin sabit bir
sema da yok. Bu agent, router'in gonderebilecegini varsaydigimiz asagidaki
sozlesmeyi kullanir; router farkli bir alan adi/sekli kullanirsa burasi
guncellenmelidir:

    task = {
        "query": str,                        # zorunlu
        "mode": "rag" | "live" | "both",      # opsiyonel; yoksa sorgudan cikarilir
        "symbol": str | None,                 # sirket/hisse kodu (orn. "THYAO")
        "date_from": str | None,              # "YYYY-MM-DD", RAG filtresi
        "date_to": str | None,                # "YYYY-MM-DD", RAG filtresi
        "top_k": int | None,                  # RAG icin donecek chunk sayisi
        "include_disclosures": bool | None,   # live modda KAP bildirimi de ekle
        "since": str | None,                  # KAP bildirim filtresi
    }
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentResult, BaseAgent
from app.core.llm import LLMClient, get_llm_client
from app.mcp.client import MCPClient, MCPClientError
from app.mcp.servers.market import MARKET_SERVER_NAME
from app.mcp.servers.rag import RAG_SERVER_NAME

AGENT_NAME = "market_research"

_LIVE_KEYWORDS = ("fiyat", "kac para", "guncel", "canli", "kap bildir")
_CONTEXT_KEYWORDS = ("neden", "sebep", "nicin", "haber", "rapor", "analiz")

NO_RETRIEVAL_MESSAGE = (
    "Bu konuda indekslenmis haber/rapor bulunamadi; halihazirda erisilebilir "
    "kaynaklarda ilgili bir icerik yok."
)


class MarketResearchAgent(BaseAgent):
    def __init__(self, mcp_client: MCPClient, llm_client: LLMClient | None = None) -> None:
        super().__init__(name=AGENT_NAME, mcp_client=mcp_client)
        self._llm_client = llm_client

    async def run(self, task: dict[str, Any]) -> AgentResult:
        query = (task.get("query") or "").strip()
        if not query:
            return AgentResult(
                agent_name=self.name,
                data={},
                success=False,
                error="task['query'] bos olamaz.",
            )

        mode = self._resolve_mode(task, query)

        try:
            summary_parts: list[str] = []
            sources: list[dict[str, Any]] = []
            live_data: dict[str, Any] | None = None
            confidence: float | None = None

            if mode in ("rag", "both"):
                rag_summary, sources, confidence = await self._run_rag(task, query)
                if rag_summary:
                    summary_parts.append(rag_summary)

            if mode in ("live", "both"):
                live_summary, live_data = await self._run_live(task)
                if live_summary:
                    summary_parts.append(live_summary)

            summary = "\n\n".join(summary_parts) if summary_parts else NO_RETRIEVAL_MESSAGE

            return AgentResult(
                agent_name=self.name,
                data={
                    "summary": summary,
                    "sources": sources,
                    "live_data": live_data,
                    "confidence": confidence,
                },
                success=True,
            )
        except MCPClientError as exc:
            return AgentResult(agent_name=self.name, data={}, success=False, error=str(exc))

    def _resolve_mode(self, task: dict[str, Any], query: str) -> str:
        mode = task.get("mode")
        if mode in ("rag", "live", "both"):
            return mode

        query_lower = query.lower()
        wants_live = bool(task.get("symbol")) and any(k in query_lower for k in _LIVE_KEYWORDS)
        wants_context = any(k in query_lower for k in _CONTEXT_KEYWORDS)

        if wants_live and wants_context:
            return "both"
        if wants_live:
            return "live"
        return "rag"

    async def _run_rag(
        self, task: dict[str, Any], query: str
    ) -> tuple[str | None, list[dict[str, Any]], float | None]:
        filters: dict[str, Any] = {}
        if symbol := task.get("symbol"):
            filters["symbol"] = symbol
        if date_from := task.get("date_from"):
            filters["date_from"] = date_from
        if date_to := task.get("date_to"):
            filters["date_to"] = date_to

        result = await self._mcp_client.call_tool(
            server=RAG_SERVER_NAME,
            tool="rag_search",
            arguments={"query": query, "top_k": task.get("top_k", 5), "filters": filters},
        )
        chunks: list[dict[str, Any]] = result.get("chunks", [])

        if not chunks:
            return NO_RETRIEVAL_MESSAGE, [], 0.0

        sources = [
            {
                "source": chunk.get("source", "bilinmiyor"),
                "excerpt": chunk.get("text", "")[:400],
                "date": chunk.get("date"),
            }
            for chunk in chunks
        ]

        summary = await self._generate_grounded_summary(query, chunks)
        confidence = round(sum(c.get("score", 0.0) for c in chunks) / len(chunks), 3)
        return summary, sources, confidence

    async def _generate_grounded_summary(self, query: str, chunks: list[dict[str, Any]]) -> str:
        llm = self._get_llm()
        prompt = _build_rag_prompt(query, chunks)
        return await llm.generate(prompt)

    def _get_llm(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = get_llm_client("market")
        return self._llm_client

    async def _run_live(self, task: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
        symbol = task.get("symbol")
        if not symbol:
            return "Canli veri icin bir sembol (task['symbol']) belirtilmedi.", None

        quote = await self._mcp_client.call_tool(
            server=MARKET_SERVER_NAME,
            tool="market_get_quote",
            arguments={"symbol": symbol},
        )

        if not quote.get("found", False):
            return f"{symbol} icin canli fiyat verisi bulunamadi.", None

        live_data = {
            "symbol": quote["symbol"],
            "price": quote["price"],
            "timestamp": quote["timestamp"],
        }
        summary = (
            f"{live_data['symbol']} guncel fiyat: {live_data['price']} "
            f"{quote.get('currency', '')} ({quote.get('change_percent', 0):+.2f}%)."
        ).strip()

        if task.get("include_disclosures"):
            disclosures_result = await self._mcp_client.call_tool(
                server=MARKET_SERVER_NAME,
                tool="market_get_kap_disclosures",
                arguments={"symbol": symbol, "since": task.get("since")},
            )
            disclosures = disclosures_result.get("disclosures", [])
            if disclosures:
                latest = disclosures[0]
                summary += f" Son KAP bildirimi ({latest['date']}): {latest['title']}."

        return summary, live_data


def _build_rag_prompt(query: str, chunks: list[dict[str, Any]]) -> str:
    lines = [
        f"Kullanici sorusu: {query}",
        "",
        "Asagidaki kaynaklara dayanarak Turkce, kisa ve net bir yanit yaz. "
        "Sadece bu kaynaklarda yer alan bilgileri kullan, kaynaklarda olmayan "
        "hicbir bilgi uydurma.",
        "",
    ]
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "bilinmiyor")
        date = chunk.get("date") or "tarih yok"
        lines.append(f"[{i}] Kaynak: {source} ({date})")
        lines.append(chunk.get("text", ""))
        lines.append("")
    lines.append("Yanit:")
    return "\n".join(lines)
