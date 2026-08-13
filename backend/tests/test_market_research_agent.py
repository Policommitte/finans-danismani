"""MarketResearchAgent testleri (app/agents/market_research.py).

Ajan iki sozlesmeye birden uymak zorundadir:
  1. BaseAgent  -> `run(state)` DICT doner, istisna SIZDIRMAZ, timeout uygular.
  2. AgentState -> yalnizca kendi alanina (`market_data`) ve reducer'li
     `sources` alanina yazar.

Testler ayrica halusinasyon korumasini sabitler: kaynak bulunamadiginda LLM'e
HIC gidilmez, boylece model bosluktan icerik uretemez.
"""

import pytest

from app.agents.market_research import NO_RETRIEVAL_MESSAGE, MarketResearchAgent
from app.mcp.client import MCPClient, MCPServer
from app.mcp.mock import build_mock_mcp_client
from app.schema.models import AgentState, Source


class SahteLLM:
    """Gercek model cagrisi yapmadan sabit bir ozet doner."""

    def __init__(self, response: str = "Test ozeti.") -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.response


class CokenLLM:
    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        raise RuntimeError("model kotasi doldu")


def _state(sorgu: str, **kwargs) -> AgentState:
    return AgentState(user_query=sorgu, user_id="u1", thread_id="t1", **kwargs)


def _ajan(llm=None, mcp_client=None) -> MarketResearchAgent:
    return MarketResearchAgent(
        mcp_client=mcp_client if mcp_client is not None else build_mock_mcp_client(),
        llm=llm if llm is not None else SahteLLM(),
        timeout_seconds=5,
    )


def _gorev(**alanlar) -> dict:
    """Router'in uretecegi yapilandirilmis parametreleri taklit eder."""
    return {"agent_tasks": {"market_research": alanlar}}


# ---------------------------------------------------------------------------
# RAG yolu
# ---------------------------------------------------------------------------


async def test_rag_sorgusu_market_data_ve_kaynak_uretir():
    llm = SahteLLM()
    ajan = _ajan(llm=llm)

    sonuc = await ajan.run(
        _state("THYAO ikinci ceyrek karini nasil etkiledi", **_gorev(mode="rag"))
    )

    assert sonuc["market_data"]["summary"] == "Test ozeti."
    assert sonuc["market_data"]["live_data"] is None
    assert sonuc["market_data"]["confidence"] is not None
    assert len(llm.prompts) == 1


async def test_kaynaklar_source_modeli_olarak_doner():
    """Orchestrator `sources` alanini `Source` nesnesi olarak serilestirir."""
    ajan = _ajan()

    sonuc = await ajan.run(_state("THYAO bilancosu", **_gorev(mode="rag", symbol="THYAO")))

    kaynaklar = sonuc["sources"]
    assert kaynaklar and all(isinstance(k, Source) for k in kaynaklar)
    assert all(k.doc_id and k.baslik for k in kaynaklar)
    assert kaynaklar[0].sirket == "THYAO"
    assert kaynaklar[0].tip == "bilanco"  # metadata.topic="earnings" eslemesi


async def test_kaynak_alintilari_market_data_icinde_de_tasinir():
    """security_gate ham veriyi tarar; alintilar orada olmazsa denetlenemez."""
    ajan = _ajan()

    sonuc = await ajan.run(_state("THYAO bilancosu", **_gorev(mode="rag", symbol="THYAO")))

    alintilar = sonuc["market_data"]["sources"]
    assert alintilar and all(a["source"] and a["excerpt"] for a in alintilar)


async def test_bos_retrieval_da_llm_e_gidilmez():
    """Halusinasyon korumasi: kaynak yoksa model hic cagrilmaz."""
    llm = SahteLLM()
    ajan = _ajan(llm=llm)

    sonuc = await ajan.run(
        _state("bilinmeyen sirket haberi", **_gorev(mode="rag", symbol="YOKYOK"))
    )

    assert sonuc["sources"] == []
    assert sonuc["market_data"]["confidence"] == 0.0
    assert sonuc["market_data"]["summary"] == NO_RETRIEVAL_MESSAGE
    assert llm.prompts == []


# ---------------------------------------------------------------------------
# Canli veri yolu
# ---------------------------------------------------------------------------


async def test_canli_sorgu_fiyat_dondurur_ve_llm_cagirmaz():
    llm = SahteLLM()
    ajan = _ajan(llm=llm)

    sonuc = await ajan.run(_state("THYAO fiyati ne", **_gorev(mode="live", symbol="THYAO")))

    canli = sonuc["market_data"]["live_data"]
    assert canli["symbol"] == "THYAO"
    assert canli["price"] > 0
    assert sonuc["sources"] == []
    assert llm.prompts == []


async def test_both_modu_rag_ve_canli_veriyi_birlestirir():
    ajan = _ajan()

    sonuc = await ajan.run(
        _state("THYAO bugun neden yukseldi", **_gorev(mode="both", symbol="THYAO"))
    )

    assert sonuc["market_data"]["live_data"] is not None
    assert sonuc["sources"]
    assert "THYAO" in sonuc["market_data"]["summary"]


async def test_bilinmeyen_sembolde_canli_veri_bos_doner_ama_hata_olmaz():
    ajan = _ajan()

    sonuc = await ajan.run(_state("XXXXX fiyati", **_gorev(mode="live", symbol="XXXXX")))

    assert sonuc["market_data"]["live_data"] is None
    assert "bulunamadi" in sonuc["market_data"]["summary"].lower()
    assert "agent_errors" not in sonuc


# ---------------------------------------------------------------------------
# Parametre cikarimi (router yapilandirilmis gorev vermediginde)
# ---------------------------------------------------------------------------


async def test_sembol_sorgudan_cikarilir():
    ajan = _ajan()

    sonuc = await ajan.run(_state("THYAO fiyati kac oldu, guncel"))

    assert sonuc["market_data"]["mode"] == "live"
    assert sonuc["market_data"]["live_data"]["symbol"] == "THYAO"


def test_bist_gibi_kisaltmalar_sembol_sayilmaz():
    ajan = _ajan()

    assert ajan._extract_symbol("BIST bugun nasil") is None
    assert ajan._extract_symbol("ASELS hisse yorumu") == "ASELS"


async def test_sembol_yoksa_rag_moduna_dusulur():
    """Canli fiyat yolu sembol olmadan anlamsizdir."""
    ajan = _ajan()

    sonuc = await ajan.run(_state("piyasada guncel fiyatlar nasil"))

    assert sonuc["market_data"]["mode"] == "rag"


async def test_router_gorevi_cikarimin_onune_gecer():
    ajan = _ajan()

    sonuc = await ajan.run(_state("THYAO fiyati ne", **_gorev(mode="rag", symbol="ASELS")))

    assert sonuc["market_data"]["mode"] == "rag"
    assert sonuc["sources"][0].sirket == "ASELS"


# ---------------------------------------------------------------------------
# Router entegrasyonu - ucuz no-op
# ---------------------------------------------------------------------------


async def test_router_istemediyse_ajan_calismaz():
    ajan = _ajan()

    sonuc = await ajan.run(_state("Portfoyum nasil?", requested_agents=["portfolio"]))

    assert sonuc == {}


async def test_router_istediyse_ajan_calisir():
    ajan = _ajan()

    sonuc = await ajan.run(_state("THYAO bilancosu", requested_agents=["market_research"]))

    assert sonuc["market_data"] is not None


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


async def test_mcp_sunucusu_yoksa_tool_error_uretir():
    """MCP cokmesi akisi durdurmamali, dogru kategoriyle raporlanmali."""
    ajan = _ajan(mcp_client=MCPClient())

    sonuc = await ajan.run(_state("THYAO bilancosu"))

    hatalar = sonuc["agent_errors"]
    assert len(hatalar) == 1
    assert hatalar[0].agent_name == "market_research"
    assert hatalar[0].error_type == "tool_error"


async def test_tool_icinde_hata_olusursa_tool_error_uretir():
    async def bozuk_rag_search(query, top_k=5, filters=None):
        raise ValueError("indeks bozuk")

    sunucu = MCPServer(name="rag")
    sunucu.register_tool("rag_search", bozuk_rag_search)
    ajan = _ajan(mcp_client=MCPClient({"rag": sunucu}))

    sonuc = await ajan.run(_state("THYAO bilancosu"))

    assert sonuc["agent_errors"][0].error_type == "tool_error"


async def test_llm_cokerse_rag_verisi_korunur():
    """KRITIK: model cokse bile bulunan kaynaklar bosa gitmemeli."""
    ajan = _ajan(llm=CokenLLM())

    sonuc = await ajan.run(_state("THYAO bilancosu", **_gorev(mode="rag", symbol="THYAO")))

    assert sonuc["sources"]  # kaynaklar duruyor
    assert sonuc["market_data"]["summary"]  # deterministik alintiya dusuldu
    assert sonuc["agent_errors"][0].error_type == "llm_error"


async def test_llm_yoksa_kaynaklardan_deterministik_ozet_uretilir():
    """LLM bagli olmamak bir HATA degildir; ajan alinti yaparak calisir."""
    ajan = MarketResearchAgent(mcp_client=build_mock_mcp_client(), llm=None, timeout_seconds=5)

    sonuc = await ajan.run(_state("THYAO bilancosu", **_gorev(mode="rag", symbol="THYAO")))

    assert "agent_errors" not in sonuc
    assert "Dunya Gazetesi" in sonuc["market_data"]["summary"]


async def test_bos_sorgu_hata_dondurur_ama_firlatmaz():
    ajan = _ajan()

    sonuc = await ajan.run(_state("   "))

    assert sonuc["agent_errors"][0].error_type == "unknown"


# ---------------------------------------------------------------------------
# Tool kesfi - yetki ayrimi
# ---------------------------------------------------------------------------


async def test_ajan_yalnizca_rag_ve_market_tool_larini_gorur():
    """NFR-04: bu ajan portfoy sunucusuna ERISEMEZ."""
    client = build_mock_mcp_client()
    client.register_server(MCPServer(name="portfolio"))
    ajan = _ajan(mcp_client=client)

    tools = await ajan.get_tools()

    assert {t["server"] for t in tools} == {"rag", "market"}


async def test_mcp_client_yoksa_tool_listesi_bostur():
    ajan = MarketResearchAgent(mcp_client=None, llm=None, timeout_seconds=5)

    assert await ajan.get_tools() == []


# ---------------------------------------------------------------------------
# Timeout - BaseAgent sozlesmesi ajan uzerinde de gecerli
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sorgu", ["THYAO bilancosu", "THYAO fiyati guncel"])
async def test_yavas_tool_timeout_uretir(sorgu):
    import asyncio

    async def yavas(**kwargs):
        await asyncio.sleep(5)
        return {}

    sunucu_rag = MCPServer(name="rag")
    sunucu_rag.register_tool("rag_search", yavas)
    sunucu_market = MCPServer(name="market")
    sunucu_market.register_tool("market_get_quote", yavas)

    ajan = MarketResearchAgent(
        mcp_client=MCPClient({"rag": sunucu_rag, "market": sunucu_market}),
        llm=SahteLLM(),
        timeout_seconds=1,
    )

    sonuc = await ajan.run(_state(sorgu))

    assert sonuc["agent_errors"][0].error_type == "timeout"
