"""BaseAgent testleri (app/agents/base.py).

Bu sinifin en kritik ozelligi GRACEFUL DEGRADATION'dir: bir ajan zaman
asimina ugrarsa veya hata firlatirsa akis DURMAMALI, hata `agent_errors`
alanina yazilip diger ajanlarla devam edilmelidir. Testler bu davranisi
sabitler.
"""

import asyncio

import pytest

from app.agents.base import BaseAgent
from app.orchestration.models import AgentState


class BasariliAjan(BaseAgent):
    """Beklendigi gibi calisan ajan."""

    name = "basarili"

    async def _execute(self, state: AgentState) -> dict:
        return {"portfolio_data": {"toplam": 100}}


class YavasAjan(BaseAgent):
    """timeout_seconds degerinden uzun suren ajan."""

    name = "yavas"

    async def _execute(self, state: AgentState) -> dict:
        await asyncio.sleep(5)
        return {"portfolio_data": {"asla": "ulasilmaz"}}


class HataliAjan(BaseAgent):
    """Beklenmeyen bir istisna firlatan ajan."""

    name = "hatali"

    async def _execute(self, state: AgentState) -> dict:
        raise RuntimeError("MCP baglantisi koptu")


class SahteMCPClient:
    """get_tools cagrisini kaydeden sahte MCP client."""

    def __init__(self, tools=None):
        self.tools = tools if tools is not None else ["portfolio_get_holdings"]
        self.cagrilan_prefix = None

    async def get_tools(self, prefix=None):
        self.cagrilan_prefix = prefix
        return self.tools


@pytest.fixture
def state() -> AgentState:
    return AgentState(user_query="Portfoyum nasil?", user_id=1, thread_id=1)


# ---------------------------------------------------------------------------
# run() - normal akis
# ---------------------------------------------------------------------------


async def test_run_basarili_ajanin_ciktisini_aynen_dondurur(state):
    ajan = BasariliAjan(mcp_client=None, llm=None, timeout_seconds=5)

    sonuc = await ajan.run(state)

    assert sonuc == {"portfolio_data": {"toplam": 100}}
    assert "agent_errors" not in sonuc


# ---------------------------------------------------------------------------
# run() - timeout
# ---------------------------------------------------------------------------


async def test_run_timeout_durumunda_hata_dondurur_ama_firlatmaz(state):
    ajan = YavasAjan(mcp_client=None, llm=None, timeout_seconds=1)

    sonuc = await ajan.run(state)

    hatalar = sonuc["agent_errors"]
    assert len(hatalar) == 1
    assert hatalar[0].agent_name == "yavas"
    assert hatalar[0].error_type == "timeout"
    assert "1s" in hatalar[0].message


async def test_run_timeout_suresi_asilmadan_biterse_sonuc_doner(state):
    """Zaman asimi siniri genisse ajan normal calismalidir."""
    ajan = BasariliAjan(mcp_client=None, llm=None, timeout_seconds=1)

    sonuc = await ajan.run(state)

    assert sonuc["portfolio_data"] == {"toplam": 100}


# ---------------------------------------------------------------------------
# run() - beklenmeyen hata
# ---------------------------------------------------------------------------


async def test_run_istisnayi_yakalar_ve_agent_error_dondurur(state):
    ajan = HataliAjan(mcp_client=None, llm=None, timeout_seconds=5)

    sonuc = await ajan.run(state)

    hatalar = sonuc["agent_errors"]
    assert len(hatalar) == 1
    assert hatalar[0].agent_name == "hatali"
    assert hatalar[0].error_type == "unknown"
    assert "MCP baglantisi koptu" in hatalar[0].message


async def test_run_hicbir_durumda_istisna_sizdirmaz(state):
    """Akisin devam edebilmesi icin run() asla istisna firlatmamalidir."""
    for ajan_sinifi in (YavasAjan, HataliAjan):
        ajan = ajan_sinifi(mcp_client=None, llm=None, timeout_seconds=1)

        sonuc = await ajan.run(state)

        assert isinstance(sonuc, dict)
        assert "agent_errors" in sonuc


# ---------------------------------------------------------------------------
# Soyut sinif sozlesmesi
# ---------------------------------------------------------------------------


def test_base_agent_dogrudan_ornek_olusturulamaz():
    """_execute soyut oldugu icin BaseAgent tek basina kullanilamaz."""
    with pytest.raises(TypeError):
        BaseAgent(mcp_client=None, llm=None, timeout_seconds=5)


def test_constructor_bagimliliklari_saklar():
    mcp = SahteMCPClient()
    ajan = BasariliAjan(mcp_client=mcp, llm="sahte-llm", timeout_seconds=7)

    assert ajan.mcp_client is mcp
    assert ajan.llm == "sahte-llm"
    assert ajan.timeout_seconds == 7


# ---------------------------------------------------------------------------
# get_tools()
# ---------------------------------------------------------------------------


async def test_get_tools_ajan_adiyla_filtreler():
    mcp = SahteMCPClient(tools=["portfolio_get_holdings"])
    ajan = BasariliAjan(mcp_client=mcp, llm=None, timeout_seconds=5)

    tools = await ajan.get_tools()

    assert mcp.cagrilan_prefix == "basarili_"
    assert tools == ["portfolio_get_holdings"]


async def test_get_tools_mcp_client_yoksa_bos_liste_doner():
    ajan = BasariliAjan(mcp_client=None, llm=None, timeout_seconds=5)

    assert await ajan.get_tools() == []


# ---------------------------------------------------------------------------
# is_requested()
# ---------------------------------------------------------------------------


def test_is_requested_liste_bossa_true_doner(state):
    """Router henuz karar vermediyse ajan calisir (guvenli varsayilan)."""
    ajan = BasariliAjan(mcp_client=None, llm=None, timeout_seconds=5)

    assert ajan.is_requested(state) is True


def test_is_requested_ajan_listedeyse_true_doner(state):
    state.requested_agents = ["basarili", "portfolio"]
    ajan = BasariliAjan(mcp_client=None, llm=None, timeout_seconds=5)

    assert ajan.is_requested(state) is True


def test_is_requested_ajan_listede_degilse_false_doner(state):
    state.requested_agents = ["portfolio"]
    ajan = BasariliAjan(mcp_client=None, llm=None, timeout_seconds=5)

    assert ajan.is_requested(state) is False


# ---------------------------------------------------------------------------
# IKI KADEMELI ZAMAN ASIMI
# ---------------------------------------------------------------------------
#
# Bu bolum GERCEK bir uretim hatasini sabitler: ajanlar once veriyi HESAPLAR
# (MCP tool'lari), sonra LLM'e yorum yazdirir. Tek bir DIS sinir `_execute`'un
# tamamini sardigi icin, LLM yavas kaldiginda dis iptal devreye giriyor ve
# `return` satirina hic ulasilamiyordu - yani zaten hesaplanmis DOGRU RAKAMLAR
# da kayboluyordu. Ardindan risk ajani portfoy verisi bulamayip `tool_error`
# veriyor, kullaniciya "veriye ulasilamadi" donuyordu.


class _AsilanLLM:
    """Hic yanit vermeyen model - asiri yuklu bir saglayiciyi taklit eder."""

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        await asyncio.sleep(3600)


class VeriSonraYorumAjani(BaseAgent):
    """Gercek ajanlarla AYNI sirayi izler: once veri, sonra LLM, sonra donus."""

    name = "veri_sonra_yorum"

    async def _execute(self, state: AgentState) -> dict:
        veri = {"toplam": 2_160_634}  # hizli adim - "MCP tool'lari"
        try:
            veri["yorum"] = await self.generate("yorumla")
        except Exception:  # noqa: BLE001 - LLM cokse de rakamlar korunmali
            veri["yorum"] = "(deterministik ozet)"
        return {"portfolio_data": veri}


async def test_llm_asilirsa_hesaplanan_veri_KORUNUR():
    """Ic sinir tetiklenir, ajan deterministik ozete duser, VERI DONER."""
    ajan = VeriSonraYorumAjani(
        mcp_client=None, llm=_AsilanLLM(), timeout_seconds=10, llm_timeout_seconds=1
    )

    sonuc = await ajan.run(AgentState(user_query="s", user_id=1, thread_id=1))

    assert sonuc["portfolio_data"]["toplam"] == 2_160_634
    assert sonuc["portfolio_data"]["yorum"] == "(deterministik ozet)"
    # Ajan komple "timeout" olarak isaretlenmemeli - is BASARIYLA bitti.
    assert "agent_errors" not in sonuc


async def test_ic_sinir_her_zaman_dis_sinirdan_kucuktur():
    """YAPISAL GUVENCE: dis iptalin veriyi yutmasi imkansiz olmali.

    Cagiran taraf ic siniri dis sinirdan BUYUK verse bile kirpilir; aksi halde
    dis iptal once devreye girer ve iki kademeli yapinin anlami kalmaz.
    """
    for dis in (5, 10, 20, 45, 90):
        ajan = VeriSonraYorumAjani(
            mcp_client=None, llm=_AsilanLLM(), timeout_seconds=dis, llm_timeout_seconds=9_999
        )
        assert ajan.llm_timeout_seconds < dis, f"dis={dis}"


async def test_ic_sinir_asilsa_bile_dis_sinir_emniyet_subabi_kalir():
    """Tool'lar ya da beklenmedik bir dongu asilirsa dis sinir yine calismali."""

    class ToolAsanAjan(BaseAgent):
        name = "tool_asan"

        async def _execute(self, state: AgentState) -> dict:
            await asyncio.sleep(3600)  # LLM degil - tool/dongu asiliyor
            return {"portfolio_data": {}}

    ajan = ToolAsanAjan(mcp_client=None, llm=None, timeout_seconds=1)

    sonuc = await ajan.run(AgentState(user_query="s", user_id=1, thread_id=1))

    assert sonuc["agent_errors"][0].error_type == "timeout"
