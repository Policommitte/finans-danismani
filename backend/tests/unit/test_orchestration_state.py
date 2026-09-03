"""`app.orchestration.models` - reducer ve state sozlesmesi.

`add_or_reset` graph'in DOGRU CALISMASININ temelidir. Reducer'li alanlar
checkpointer'da BIRIKIR; `[]` yazarak sifirlanamazlar cunku LangGraph giris
degerini checkpoint'teki degere REDUCER ILE uygular ve `[] + mevcut`
"hicbir sey ekleme" demektir. Sentinel olmadan ikinci turda kaynaklar ikiye
katlanir ve duzelen bir ajan icin "ulasilamadi" uyarisi ekranda kalir.
"""

from __future__ import annotations

import pytest
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

# --- add_or_reset ---------------------------------------------------------


def test_normal_birikim():
    assert add_or_reset(["a"], ["b"]) == ["a", "b"]


def test_reset_kanali_temizler():
    assert add_or_reset(["a", "b"], [RESET]) == []


def test_reset_ve_yeni_deger_ayni_guncellemede():
    """`stream_request` tur basinda `[RESET]` yazar; ayni node yeni veri de
    uretebilir."""
    assert add_or_reset(["eski"], [RESET, "yeni"]) == ["yeni"]


def test_bos_liste_sifirlama_ANLAMINA_GELMEZ():
    """Sentinel'in var olma sebebi tam olarak budur."""
    assert add_or_reset(["a"], []) == ["a"]


def test_none_guncelleme_mevcut_degeri_korur():
    assert add_or_reset(["a"], None) == ["a"]


def test_mevcut_deger_none_ise_bos_listeden_baslar():
    assert add_or_reset(None, ["a"]) == ["a"]
    assert add_or_reset(None, None) == []


def test_liste_olmayan_guncelleme_tek_elemana_sarilir():
    assert add_or_reset(["a"], "b") == ["a", "b"]


def test_demet_guncelleme_de_kabul_edilir():
    assert add_or_reset(["a"], ("b", "c")) == ["a", "b", "c"]


def test_reducer_girdiyi_YERINDE_degistirmez():
    """Aksi halde LangGraph'in checkpoint kopyasi bozulurdu."""
    mevcut = ["a"]
    add_or_reset(mevcut, ["b"])
    assert mevcut == ["a"]


def test_reset_sentineli_serilesebilir_bir_stringtir():
    """Checkpointer msgpack kullanir; ozel bir sinif serilestirilemezdi."""
    assert isinstance(RESET, str)


# --- Modeller -------------------------------------------------------------


def test_source_yalnizca_doc_id_ve_baslik_zorunlu():
    """Canli veri yolundan gelen chunk'larda tarih/url bos olabilir."""
    s = Source(doc_id="1", baslik="Baslik")
    assert s.kaynak_url is None and s.score is None


def test_kaynak_url_opsiyoneldir():
    """Eski dokumanlarda bos; arayuz o zaman karti duz metin cizer."""
    assert Source(doc_id="1", baslik="B", kaynak_url="https://x").kaynak_url == "https://x"


@pytest.mark.parametrize("tip", ["timeout", "tool_error", "llm_error", "unknown"])
def test_agent_error_yalnizca_bilinen_tipleri_kabul_eder(tip):
    assert AgentError(agent_name="market", error_type=tip, message="x").error_type == tip


def test_taninmayan_hata_tipi_reddedilir():
    with pytest.raises(ValidationError):
        AgentError(agent_name="market", error_type="patladi", message="x")


def test_tool_result_varsayilan_olarak_basarilidir():
    r = ToolResult(tool_name="portfolio_get_summary", output={}, latency_ms=12.5)
    assert r.success is True and r.error is None


@pytest.mark.parametrize("intent", ["portfoy", "piyasa", "risk", "karma", "sohbet", "belirsiz"])
def test_router_karari_bilinen_niyetleri_kabul_eder(intent):
    assert RouterDecision(intent=intent).intent == intent


def test_router_karari_taninmayan_niyeti_reddeder():
    with pytest.raises(ValidationError):
        RouterDecision(intent="tahmin")


# --- AgentState -----------------------------------------------------------


def test_state_zorunlu_alanlari():
    with pytest.raises(ValidationError):
        AgentState(user_query="x")  # user_id / thread_id eksik


def test_state_varsayilanlari_guvenli_taraftadir():
    s = AgentState(user_query="portfoyum", user_id=1, thread_id=2)
    assert s.is_input_safe is True and s.is_output_safe is True
    assert s.sources == [] and s.agent_errors == [] and s.security_flags == []
    assert s.belge is None and s.document_report is None
    assert s.final_response is None


def test_kimlikler_int_tasinir():
    """DB'de `users.id` ve `chat_sessions.id` SERIAL; MCP yetkilendirmesi
    contextvar KARSILASTIRMASINA dayanir. Tip donusumu sinirda BIR KEZ
    yapilir, graph icinde hep int'tir."""
    s = AgentState(user_query="x", user_id="7", thread_id="9")
    assert (s.user_id, s.thread_id) == (7, 9)


def test_belge_raporu_document_data_dan_ayri_alanda_durur():
    """⚠️ BILEREK AYRI: `_ajan_metni()` bir ajan sozlugunde `summary_text`
    bulamazsa `str(veri)` yapar. PDF baytlari `document_data` icinde
    olsaydi ikili icerik kullaniciya giden METNE ve LLM prompt'una ham
    repr olarak dokulurdu."""
    s = AgentState(
        user_query="x",
        user_id=1,
        thread_id=1,
        document_data={"summary_text": "ozet"},
        document_report={"pdf_bytes": b"%PDF", "dosya_adi": "r.pdf"},
    )
    assert "pdf_bytes" not in s.document_data
    assert s.document_report["pdf_bytes"] == b"%PDF"


def test_reducer_li_alanlar_annotated_tasir():
    """Reducer'i olmayan bir alana iki node paralel yazarsa LangGraph
    catisma hatasi verir - ya da ikinci yazan birincinin verisini siler."""
    for alan in ("sources", "agent_errors", "security_flags"):
        meta = AgentState.model_fields[alan].metadata
        assert add_or_reset in meta, f"{alan} reducer tasimiyor"
