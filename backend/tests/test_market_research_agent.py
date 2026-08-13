import asyncio

from app.agents.market_research import MarketResearchAgent
from app.mcp.mock import build_mock_mcp_client


class FakeLLMClient:
    """Gercek Gemini cagrisi yapmadan test icin sabit bir ozet doner."""

    def __init__(self, response: str = "Test ozeti.") -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.response


def _run(coro):
    return asyncio.run(coro)


def _agent(llm: FakeLLMClient | None = None) -> tuple[MarketResearchAgent, FakeLLMClient]:
    fake_llm = llm or FakeLLMClient()
    agent = MarketResearchAgent(mcp_client=build_mock_mcp_client(), llm_client=fake_llm)
    return agent, fake_llm


def test_rag_only_query_returns_grounded_sources():
    agent, llm = _agent()
    task = {
        "query": "THYAO ikinci ceyrek karini nasil etkiledi",
        "mode": "rag",
        "symbol": "THYAO",
    }

    result = _run(agent.run(task))

    assert result.success is True
    assert result.agent_name == "market_research"
    assert result.data["live_data"] is None
    assert len(result.data["sources"]) > 0
    assert all(s["source"] and s["excerpt"] for s in result.data["sources"])
    assert result.data["confidence"] is not None
    assert len(llm.prompts) == 1


def test_live_only_query_returns_price_without_llm_call():
    agent, llm = _agent()
    task = {"query": "THYAO fiyati ne", "mode": "live", "symbol": "THYAO"}

    result = _run(agent.run(task))

    assert result.success is True
    assert result.data["live_data"]["symbol"] == "THYAO"
    assert result.data["live_data"]["price"] > 0
    assert result.data["sources"] == []
    assert llm.prompts == []  # canli veri yolu LLM cagirmamali


def test_combined_query_merges_rag_and_live():
    agent, _ = _agent()
    task = {"query": "THYAO bugun neden yukseldi", "mode": "both", "symbol": "THYAO"}

    result = _run(agent.run(task))

    assert result.success is True
    assert result.data["live_data"] is not None
    assert len(result.data["sources"]) > 0
    assert "THYAO" in result.data["summary"]


def test_empty_retrieval_does_not_hallucinate():
    agent, llm = _agent()
    task = {
        "query": "bilinmeyen bir sirket hakkinda haber var mi",
        "mode": "rag",
        "symbol": "TESTYOK",
    }

    result = _run(agent.run(task))

    assert result.success is True
    assert result.data["sources"] == []
    assert result.data["confidence"] == 0.0
    assert "bulunamadi" in result.data["summary"].lower()
    assert llm.prompts == []  # bos retrieval'de LLM'e hic gidilmemeli


def test_missing_query_returns_error_result():
    agent, _ = _agent()

    result = _run(agent.run({"mode": "rag"}))

    assert result.success is False
    assert result.error


def test_mode_inferred_from_query_when_not_provided():
    agent, llm = _agent()
    task = {"query": "THYAO fiyati kac oldu, guncel", "symbol": "THYAO"}

    result = _run(agent.run(task))

    assert result.success is True
    assert result.data["live_data"] is not None
    assert llm.prompts == []  # sadece live moda dusmus olmali
