"""Ortak veri modellerinin testleri (app/orchestration/models.py).

Burada ozellikle REDUCER kurallari sinanir: paralel calisan node'lar ayni
alana yazdiginda verinin uzerine yazilmasi degil, BIRIKMESI gerekir. Reducer
yanlis tanimlanirsa graph hata firlatmaz ama veri sessizce kaybolur - bu
yuzden testle sabitlenmistir.
"""

import operator
from typing import get_args, get_origin

import pytest
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from app.orchestration.models import (
    RESET,
    AgentError,
    AgentState,
    RouterDecision,
    Source,
    ToolResult,
    add_or_reset,
)


def _reducer_of(field_name: str):
    """AgentState alanindaki `Annotated[...]` reducer fonksiyonunu doner."""
    annotation = AgentState.model_fields[field_name].rebuild_annotation()
    assert get_origin(annotation) is not None, f"{field_name} Annotated degil"
    return get_args(annotation)[1]


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------


def test_source_zorunlu_alanlarla_olusur():
    source = Source(doc_id="d1", baslik="X Sirketi 3. Ceyrek Bilancosu")

    assert source.doc_id == "d1"
    assert source.sirket is None
    assert source.score is None


def test_source_opsiyonel_alanlari_kabul_eder():
    source = Source(
        doc_id="d1",
        baslik="Baslik",
        sirket="X A.S.",
        tarih="2026-01-15",
        tip="bilanco",
        score=0.87,
    )

    assert source.tip == "bilanco"
    assert source.score == 0.87


def test_source_doc_id_zorunludur():
    with pytest.raises(ValidationError):
        Source(baslik="Baslik")


# ---------------------------------------------------------------------------
# AgentError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("error_type", ["timeout", "tool_error", "llm_error", "unknown"])
def test_agent_error_gecerli_tipleri_kabul_eder(error_type):
    hata = AgentError(agent_name="portfolio", error_type=error_type, message="mesaj")

    assert hata.error_type == error_type


def test_agent_error_gecersiz_tipi_reddeder():
    """error_type Literal ile sinirlandirilmistir; yazim hatasi sessizce gecmemeli."""
    with pytest.raises(ValidationError):
        AgentError(agent_name="portfolio", error_type="zaman_asimi", message="mesaj")


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------


def test_tool_result_varsayilan_olarak_basarilidir():
    sonuc = ToolResult(tool_name="portfolio_get_holdings", output={"a": 1}, latency_ms=12.5)

    assert sonuc.success is True
    assert sonuc.error is None


def test_tool_result_hata_bilgisi_tasiyabilir():
    sonuc = ToolResult(
        tool_name="rag_search",
        output={},
        latency_ms=3.0,
        success=False,
        error="baglanti hatasi",
    )

    assert sonuc.success is False
    assert sonuc.error == "baglanti hatasi"


# ---------------------------------------------------------------------------
# AgentState - alanlar ve varsayilanlar
# ---------------------------------------------------------------------------


def test_agent_state_varsayilanlari():
    state = AgentState(user_query="soru", user_id=1, thread_id=1)

    assert state.messages == []
    assert state.requested_agents == []
    assert state.portfolio_data is None
    assert state.market_data is None
    assert state.risk_data is None
    assert state.sources == []
    assert state.agent_errors == []
    assert state.security_flags == []
    assert state.is_input_safe is True
    assert state.is_output_safe is True
    assert state.final_response is None


@pytest.mark.parametrize("eksik_alan", ["user_query", "user_id", "thread_id"])
def test_agent_state_girdi_alanlari_zorunludur(eksik_alan):
    alanlar = {"user_query": "soru", "user_id": 1, "thread_id": 1}
    del alanlar[eksik_alan]

    with pytest.raises(ValidationError):
        AgentState(**alanlar)


def test_agent_state_varsayilanlari_ornekler_arasinda_paylasilmaz():
    """default_factory kullanildigi icin listeler ornege ozel olmali."""
    birinci = AgentState(user_query="a", user_id=1, thread_id=1)
    ikinci = AgentState(user_query="b", user_id=1, thread_id=1)

    birinci.security_flags.append("prompt_injection")

    assert ikinci.security_flags == []


# ---------------------------------------------------------------------------
# AgentState - REDUCER kurallari (kritik)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alan", ["sources", "agent_errors", "security_flags"])
def test_parallel_written_fields_carry_add_or_reset_reducer(alan):
    """Bu alanlara birden fazla node yazar; reducer olmazsa veri kaybolur.

    Reducer `operator.add` DEGIL `add_or_reset`: birikime ek olarak tur basi
    sifirlamayi da anlamasi gerekir (bkz. asagidaki sentinel testleri).
    """
    assert _reducer_of(alan) is add_or_reset


def test_messages_alani_add_messages_reducer_tasir():
    """Cok turlu baglam (FR-CHAT-03) icin mesajlar birikmeli, ezilmemeli."""
    assert _reducer_of("messages") is add_messages


@pytest.mark.parametrize("alan", ["portfolio_data", "market_data", "risk_data"])
def test_ajan_ciktilari_reducer_tasimaz(alan):
    """Her ajan KENDI alanina yazdigi icin catisma yok, reducer gereksiz."""
    annotation = AgentState.model_fields[alan].rebuild_annotation()

    assert get_origin(annotation) is not dict  # tip: dict | None
    assert operator.add not in get_args(annotation)


def test_add_or_reset_merges_lists():
    """Reducer davranisinin kendisi: iki paralel node'un ciktisi birikir."""
    market_ciktisi = [Source(doc_id="d1", baslik="Piyasa haberi")]
    portfolio_ciktisi = [Source(doc_id="d2", baslik="Portfoy raporu")]

    birlesik = add_or_reset(market_ciktisi, portfolio_ciktisi)

    assert [s.doc_id for s in birlesik] == ["d1", "d2"]
    # Reducer birikimli oldugu icin operator.add ile ayni sonucu vermeli.
    assert birlesik == operator.add(market_ciktisi, portfolio_ciktisi)


def test_add_or_reset_sentinel_clears_channel():
    """Tur basi sifirlama: `[]` yazmak yetmez, sentinel gerekir."""
    mevcut = [Source(doc_id="d1", baslik="Onceki turdan kalan")]

    assert add_or_reset(mevcut, []) == mevcut, "bos liste SIFIRLAMAZ (reducer birikimli)"
    assert add_or_reset(mevcut, [RESET]) == []


def test_add_or_reset_can_write_in_same_turn_after_sentinel():
    """`[RESET, deger]`: once temizle, sonra bu turun degerini yaz."""
    mevcut = [Source(doc_id="eski", baslik="Onceki tur")]
    yeni = Source(doc_id="yeni", baslik="Bu tur")

    assert add_or_reset(mevcut, [RESET, yeni]) == [yeni]


def test_add_or_reset_ignores_none_update():
    mevcut = ["prompt_injection"]

    assert add_or_reset(mevcut, None) == mevcut


def test_router_decision_accepts_valid_intent():
    karar = RouterDecision(intent="karma", agents=["portfolio", "risk_strategy"], reasoning="test")

    assert karar.intent == "karma"
    assert karar.needs_clarification is False


def test_router_decision_rejects_invalid_intent():
    with pytest.raises(ValidationError):
        RouterDecision(intent="bilinmeyen")


def test_agent_state_new_fields():
    """§14-7: request_id, portfolio_id ve intent state'te tasiniyor."""
    state = AgentState(
        user_query="soru", user_id=1, thread_id=2, request_id="abc", portfolio_id=7, intent="risk"
    )

    assert (state.request_id, state.portfolio_id, state.intent) == ("abc", 7, "risk")


def test_agent_state_user_id_and_thread_id_must_be_int():
    """DB'de users.id ve chat_sessions.id SERIAL; MCP yetkilendirmesi int karsilastirir."""
    with pytest.raises(ValidationError):
        AgentState(user_query="soru", user_id="kullanici", thread_id="oturum")


def test_agent_state_dolu_haliyle_olusturulabilir():
    state = AgentState(
        user_query="Portfoyumun riski nedir?",
        user_id=1,
        thread_id=1,
        requested_agents=["portfolio", "risk_strategy"],
        portfolio_data={"toplam": 100_000},
        sources=[Source(doc_id="d1", baslik="Kaynak")],
        agent_errors=[
            AgentError(agent_name="market_research", error_type="timeout", message="20s")
        ],
        security_flags=["prompt_injection"],
        is_input_safe=False,
        final_response="yanit",
    )

    assert state.portfolio_data == {"toplam": 100_000}
    assert state.sources[0].doc_id == "d1"
    assert state.agent_errors[0].error_type == "timeout"
    assert state.is_input_safe is False
