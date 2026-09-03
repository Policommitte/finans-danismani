"""Cok turlu birikim testleri (§14-4).

Ertelenen bulgu: reducer'li alanlar (`sources`, `agent_errors`,
`security_flags`) checkpointer'da birikiyordu. Ayni `thread_id` ile ucuncu
turda kaynaklar ikiye/uce katlaniyor, bir turda hata veren ajan sonraki turda
duzelse bile synthesizer "su analizlere ulasilamadi" demeye devam ediyordu.

Olcum (duzeltme oncesi):
    Tur 1: state.sources = 2 · Tur 2: 4 · Tur 3: 6

Bu dosya duzeltmeyi SABITLER: tur sayisindan bagimsiz olarak state ayni
kaynak sayisini tasimali.
"""

import pytest

import app.engine.orchestrator as orchestrator_modulu
from app.agents.base import BaseAgent
from app.engine.orchestrator import Orchestrator
from app.orchestration.models import AgentError, AgentState, Source

THREAD = 42


class KaynakUretenAjan(BaseAgent):
    name = "market_research"

    def __init__(self) -> None:
        super().__init__(mcp_client=None, llm=None, timeout_seconds=5)

    async def _execute(self, state: AgentState) -> dict:
        return {
            "market_data": {"summary": "piyasa ozeti"},
            "sources": [
                Source(doc_id="d1", baslik="Dunya Gazetesi", tarih="2026-08-10"),
                Source(doc_id="d2", baslik="KAP", tarih="2026-08-10"),
            ],
        }


class IlkTurdaCokenAjan(BaseAgent):
    """Ilk turda hata verir, sonraki turlarda duzelir."""

    name = "portfolio"

    def __init__(self) -> None:
        super().__init__(mcp_client=None, llm=None, timeout_seconds=5)
        self.tur = 0

    async def _execute(self, state: AgentState) -> dict:
        self.tur += 1
        if self.tur == 1:
            return {
                "agent_errors": [
                    AgentError(
                        agent_name=self.name, error_type="timeout", message="20s icinde yanit yok"
                    )
                ]
            }
        return {"portfolio_data": {"summary": "portfoy ozeti"}}


class GecerGuvenlikAjani:
    async def check_input_node(self, state: AgentState) -> dict:
        return {"is_input_safe": True}

    async def security_gate_node(self, state: AgentState) -> dict:
        return {"is_output_safe": True}


@pytest.fixture
def orchestrator() -> Orchestrator:
    return Orchestrator(
        agents={"market_research": KaynakUretenAjan(), "portfolio": IlkTurdaCokenAjan()},
        security_agent=GecerGuvenlikAjani(),
    )


async def _tur(orchestrator: Orchestrator, soru: str) -> list[dict]:
    return [o async for o in orchestrator.stream_request(soru, user_id=1, thread_id=THREAD)]


def _state(orchestrator: Orchestrator) -> AgentState:
    return orchestrator.graph.get_state({"configurable": {"thread_id": str(THREAD)}}).values


async def test_kaynaklar_turlar_arasinda_birikmez(orchestrator):
    for tur in range(1, 4):
        await _tur(orchestrator, f"{tur}. turda portfoyum nasil?")
        assert len(_state(orchestrator)["sources"]) == 2, f"{tur}. turda kaynaklar birikti"


async def test_sse_kaynak_olayi_da_tek_kume_dondurur(orchestrator):
    await _tur(orchestrator, "portfoyum nasil?")
    olaylar = await _tur(orchestrator, "piyasa nasil?")

    kaynak_olaylari = [o for o in olaylar if o["type"] == "sources"]
    assert len(kaynak_olaylari) == 1
    assert len(kaynak_olaylari[0]["items"]) == 2


async def test_duzelen_ajanin_hatasi_sonraki_turda_tasinmaz(orchestrator):
    """Birinci turda coken ajan ikinci turda duzelirse 'ulasilamadi' KALMAMALI."""
    await _tur(orchestrator, "portfoyum nasil?")
    assert len(_state(orchestrator)["agent_errors"]) == 1

    olaylar = await _tur(orchestrator, "piyasa nasil?")

    assert _state(orchestrator)["agent_errors"] == []
    metin = "".join(o["content"] for o in olaylar if o["type"] == "token")
    assert "ulaşılamadı" not in metin


async def test_agent_error_olayi_yalnizca_ilgili_turda_yayinlanir(orchestrator):
    ilk = await _tur(orchestrator, "portfoyum nasil?")
    ikinci = await _tur(orchestrator, "piyasa nasil?")

    assert [o for o in ilk if o["type"] == "agent_error"]
    assert [o for o in ikinci if o["type"] == "agent_error"] == []


async def test_agent_error_event_leaks_no_internal_detail_in_production(orchestrator, monkeypatch):
    """Istisna metni tool adi, baglanti dizesi, dosya yolu tasiyabilir."""
    monkeypatch.setattr(orchestrator_modulu.settings, "app_env", "production")

    olaylar = await _tur(orchestrator, "portfoyum nasil?")

    hata = next(o for o in olaylar if o["type"] == "agent_error")
    assert set(hata) == {"type", "agent", "error_type"}
    assert hata["agent"] == "portfolio"
    assert hata["error_type"] == "timeout"


async def test_agent_error_event_also_carries_text_in_development(orchestrator, monkeypatch):
    """Karsit durum: gelistirirken "timeout" tek basina hicbir sey soylemiyor."""
    monkeypatch.setattr(orchestrator_modulu.settings, "app_env", "development")

    olaylar = await _tur(orchestrator, "portfoyum nasil?")

    hata = next(o for o in olaylar if o["type"] == "agent_error")
    assert hata["message"] == "20s icinde yanit yok"


async def test_mesaj_gecmisi_birikmeye_DEVAM_eder(orchestrator):
    """Sifirlama yalnizca reducer'li ajan alanlarina; baglam korunmali (FR-CHAT-03)."""
    await _tur(orchestrator, "portfoyum nasil?")
    await _tur(orchestrator, "piyasa nasil?")

    mesajlar = _state(orchestrator)["messages"]
    icerikler = [m.content for m in mesajlar]

    assert "portfoyum nasil?" in icerikler
    assert "piyasa nasil?" in icerikler
