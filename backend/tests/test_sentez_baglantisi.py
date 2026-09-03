"""Sentez adiminin model baglantisi (app/core/llm.py + app/engine/factory.py).

NEDEN BU DOSYA VAR
------------------
`build_orchestrator` uzun sure `synthesizer_llm`'i HIC gecmiyordu. Sonuc:
`.env` icindeki `SYNTHESIZER_MODEL` okunuyor ama kullanilmiyor, sentez her
zaman `Orchestrator._fallback_response` ile yapiliyordu - yani kullaniciya
giden metin LLM'in yazdigi bir yanit degil, ajan ozetlerinin duz birlestirmesi
oluyordu ("Portfoy analizi: ... Piyasa arastirmasi: ...").

Hata sessizdi: hicbir istisna atilmiyor, log da uretilmiyordu. Yalnizca cikti
formatina dikkatle bakinca fark ediliyordu. Buradaki testler o baglantiyi
sabitler.
"""

import asyncio
import importlib
import time

import pytest

import app.config
import app.core.llm
import app.engine.factory
from app.agents.base import BaseAgent
from app.agents.security_agent import SecurityAgent
from app.engine.orchestrator import (
    KISMI_YANIT_NOTU,
    YATIRIM_TAVSIYESI_IBARESI,
    Orchestrator,
    _messages_to_text,
)
from app.orchestration.models import AgentState

#: Bu dosya import edilirken var olan ORIJINAL `Settings` NESNESI.
#:
#: `importlib.reload(app.config)` her cagrildiginda YENI bir nesne uretir. Ama
#: `from app.config import settings` diyerek daha once import edilmis moduller
#: (orn. `app.repositories.deps`) ESKI nesneye BAGLI KALIR - reload onlarin
#: referansini guncellemez.
#:
#: Teardown'da yalnizca `app.config`'i tekrar reload etmek bu yuzden YETMEZ:
#: o da ucuncu bir nesne uretir ve `app.config.settings` ile modullerin
#: gordugu nesne kalici olarak ayrisir.
#:
#: SOMUT ZARARI (CI'da yakalandi): `test_sql_repositories.py` fixture'i
#: `from app.config import settings` ile O ANKI nesneyi alip `database_url`'i
#: yamiyordu; `app.repositories.deps` ise hala ESKI nesneye bakip
#: "DATABASE_URL tanimli degil" diyerek bellek ici veriye dusuyordu. Yazma
#: bellege gidiyor, dogrulama Postgres'e bakiyor, satir bulunamiyordu.
#: Testler TEK BASINA gecip yalnizca bu dosyadan SONRA kosunca dusuyordu -
#: yerelde Postgres olmadigi icin atlandiklarindan sorun sadece CI'da
#: goruluyordu.
#:
#: Cozum: teardown yeni nesne uretmek yerine ORIJINAL nesneyi geri koyar.
_ORIJINAL_AYARLAR = app.config.settings


@pytest.fixture
def environment(monkeypatch):
    """Model/anahtar environment degiskenlerini kurar ve modulleri yeniden yukler.

    `Settings` ornegi modul yuklenirken bir kez okundugu icin `monkeypatch.setenv`
    tek basina yetmez - config ve llm modullerinin yeniden yuklenmesi gerekir.

    ⚠️ DELENV YETMEZ, BOS STRING SART. `Settings` yalnizca environment degiskenlerini
    degil `backend/.env` DOSYASINI da okur (`env_file=".env"`). Degiskeni
    silmek dosyadaki degeri ortaya cikarir: gercek bir NVIDIA anahtari ve
    `DEFAULT_MODEL` tanimlamis bir gelistiricide "model tanimli degilse None
    doner" testleri PATLAR - kod dogru olsa bile. Bos string atamak ise environment
    degiskeni olarak .env'i EZER (pydantic-settings onceligi) ve testi
    gelistiricinin yerel kurulumundan bagimsiz kilar.
    """

    def _setup(**degiskenler: str):
        for anahtar in (
            "DEFAULT_MODEL",
            "SYNTHESIZER_MODEL",
            "NVIDIA_API_KEY",
            "GEMINI_API_KEY",
            "LLM_API_KEY",
            "LLM_PROVIDER",
        ):
            monkeypatch.setenv(anahtar, "")
        # Bu alan `bool`: bos string pydantic'te ayristirilamaz
        # ("Input should be a valid boolean"), o yuzden "0" ile sifirlanir.
        monkeypatch.setenv("LLM_NVIDIA_EXTRA_BODY_OFF", "0")
        for anahtar, deger in degiskenler.items():
            monkeypatch.setenv(anahtar, deger)
        importlib.reload(app.config)
        importlib.reload(app.core.llm)
        importlib.reload(app.engine.factory)
        return app.core.llm, app.engine.factory

    yield _setup

    # Diger test dosyalari ORIJINAL NESNEYLE devam etsin - yeni bir nesneyle
    # DEGIL. Gerekcesi icin `_ORIJINAL_AYARLAR` notuna bakin.
    app.config.settings = _ORIJINAL_AYARLAR
    # llm ve factory reload sirasinda reload edilmis config'in nesnesine
    # baglandi; orijinaline geri baglanmalari icin onlar da tazelenir.
    importlib.reload(app.core.llm)
    importlib.reload(app.engine.factory)


# ---------------------------------------------------------------------------
# get_streaming_llm
# ---------------------------------------------------------------------------


def test_streaming_client_built_for_nim_model(environment):
    llm, _ = environment(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    model = llm.get_streaming_llm("synthesizer")

    assert model is not None
    # LangGraph token akisi YALNIZCA LangChain chat modelleriyle calisir.
    assert hasattr(model, "astream")
    assert model.model_name == "nvidia/nemotron-3-ultra"
    assert model.openai_api_base.rstrip("/").endswith("/v1")
    assert model.streaming is True


def test_thinking_sent_disabled(environment):
    """Akil yurutme izi hem sentez suresini uzatir hem de guvenlik ajaninin
    'ilk sayiyi oku' ayristiricisini bozar."""
    llm, _ = environment(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    model = llm.get_streaming_llm("synthesizer")

    assert model.extra_body == {"chat_template_kwargs": {"enable_thinking": False}}


def test_thinking_flag_NOT_sent_top_level(environment):
    """Canlida olculdu: top-level `enable_thinking` 400 aldiriyor.

    OpenAI uyumlu uc tanimadigi govde alanini yok saymiyor, istegi reddediyor.
    Bir ara "her ihtimale karsi ikisini birden gonderelim" denmisti; sonucu
    TUM LLM cagrilarinin patlamasi oldu (ajanlar `llm_error`, sentez
    deterministik ozet). Bu test o denemeyi geri gelmekten alikoyar.
    """
    llm, _ = environment(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    assert "enable_thinking" not in llm.get_streaming_llm("synthesizer").extra_body


def test_extra_body_kill_switch_works(environment):
    """Model ek alani tanimayip 400 donerse kacis kapisi olmali."""
    llm, _ = environment(
        SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra",
        NVIDIA_API_KEY="test",
        LLM_NVIDIA_EXTRA_BODY_OFF="1",
    )

    assert not llm.get_streaming_llm("synthesizer").extra_body


# ---------------------------------------------------------------------------
# Ek govde reddedilirse: bayraksiz tekrar dene
# ---------------------------------------------------------------------------


class _Sahte400(Exception):
    status_code = 400

    def __str__(self) -> str:
        return "Error code: 400 - extra fields not permitted"


class _Sahte401(Exception):
    status_code = 401

    def __str__(self) -> str:
        return "Error code: 401 - invalid api key"


class _SahteMesaj:
    content = "merhaba"
    reasoning_content = ""


class _SahteYanit:
    choices = [type("S", (), {"message": _SahteMesaj()})()]


def _nim_client(llm_modulu):
    return llm_modulu.NvidiaLLMClient(
        api_key="test", default_model="nvidia/nemotron-3-ultra", base_url="http://ornek/v1"
    )


async def test_retried_without_flag_when_extra_body_rejected(environment):
    """Tek bir govde alani yuzunden tum LLM katmani durmamali."""
    llm, _ = environment(NVIDIA_API_KEY="test")
    istemci = _nim_client(llm)
    cagrilar: list[dict] = []

    async def fake(model, prompt, ek):
        cagrilar.append(ek)
        if ek:
            raise _Sahte400()
        return _SahteYanit()

    istemci._call = fake

    assert await istemci.generate("selam") == "merhaba"
    assert len(cagrilar) == 2
    assert "extra_body" in cagrilar[0]
    assert cagrilar[1] == {}


async def test_non_400_error_not_retried(environment):
    """Gecersiz anahtari 'bayrak sorunu' sanip iki kez denemek yanlis olurdu."""
    llm, _ = environment(NVIDIA_API_KEY="test")
    istemci = _nim_client(llm)
    cagrilar: list[dict] = []

    async def fake(model, prompt, ek):
        cagrilar.append(ek)
        raise _Sahte401()

    istemci._call = fake

    with pytest.raises(_Sahte401):
        await istemci.generate("selam")
    assert len(cagrilar) == 1


def test_extra_body_rejection_true_only_on_400(environment):
    llm, _ = environment()

    assert llm._extra_body_rejected(_Sahte400()) is True
    assert llm._extra_body_rejected(_Sahte401()) is False
    assert llm._extra_body_rejected(RuntimeError("baglanti koptu")) is False


def test_no_streaming_client_for_gemini_model(environment):
    """`langchain-google-genai` bagimliligi yok; cagiran taraf duse duse
    tek seferlik istemciye iner."""
    llm, _ = environment(SYNTHESIZER_MODEL="gemini-3.5-flash-lite", GEMINI_API_KEY="test")

    assert llm.get_streaming_llm("synthesizer") is None


def test_returns_none_without_model_name(environment):
    llm, _ = environment(NVIDIA_API_KEY="test")

    assert llm.get_streaming_llm("synthesizer") is None


def test_returns_none_without_api_key(environment):
    llm, _ = environment(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra")

    assert llm.get_streaming_llm("synthesizer") is None


def test_model_name_without_slash_assumed_gemini(environment):
    """`.env`'e 'nemotron-3-ultra' yazmak sessizce yanlis saglayiciya gider.

    Bu davranis BILINCLI (saglayici model adindan anlasiliyor) ama tuzak;
    test onu gorunur kiliyor.
    """
    llm, _ = environment()

    assert llm.detect_provider("nemotron-3-ultra") == "gemini"
    assert llm.detect_provider("nvidia/nemotron-3-ultra") == "nvidia"


# ---------------------------------------------------------------------------
# factory: sentez modeli gercekten orchestrator'a gecirilir mi?
# ---------------------------------------------------------------------------


def test_factory_selects_streaming_model(environment):
    _, factory = environment(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    model = factory.build_synthesizer_llm()

    assert model is not None and hasattr(model, "astream")


def test_factory_falls_back_to_one_shot_when_streaming_unavailable(environment):
    """Gemini sentezi: akis yok ama sentez YINE LLM ile yapilmali."""
    _, factory = environment(SYNTHESIZER_MODEL="gemini-3.5-flash-lite", GEMINI_API_KEY="test")

    model = factory.build_synthesizer_llm()

    assert model is not None
    assert hasattr(model, "generate")
    assert not hasattr(model, "astream")


def test_stays_deterministic_when_model_undefined(environment):
    _, factory = environment()

    assert factory.build_synthesizer_llm() is None


def test_orchestrator_receives_synthesis_model(environment, monkeypatch):
    """Asil regresyon: `build_orchestrator` bu alani bos birakiyordu."""
    _, factory = environment(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    orchestrator = factory.build_orchestrator()

    assert orchestrator.synthesizer_llm is not None


def test_caller_can_override_synthesis_model(environment):
    _, factory = environment(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    orchestrator = factory.build_orchestrator(synthesizer_llm=None)

    assert orchestrator.synthesizer_llm is None


# ---------------------------------------------------------------------------
# Akitmayan istemciyle sentez
# ---------------------------------------------------------------------------


class SahteAjan(BaseAgent):
    def __init__(self, name: str, cikti: dict) -> None:
        super().__init__(mcp_client=None, llm=None, timeout_seconds=5)
        self.name = name
        self.cikti = cikti

    async def _execute(self, state: AgentState) -> dict:
        return self.cikti


class TekSeferlikLLM:
    """`astream`i OLMAYAN istemci - GeminiLLMClient / NvidiaLLMClient gibi."""

    def __init__(self) -> None:
        self.gorulen_prompt: str | None = None

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        self.gorulen_prompt = prompt
        return "Sentezlenmis yanit. Bu bilgiler yatirim tavsiyesi degildir."


def _orchestrator(llm) -> Orchestrator:
    return Orchestrator(
        agents={
            "portfolio": SahteAjan(
                "portfolio", {"portfolio_data": {"summary": "toplam 100.000 TL"}}
            ),
            "market_research": SahteAjan("market_research", {"market_data": {"summary": "yatay"}}),
        },
        security_agent=SecurityAgent(),
        synthesizer_llm=llm,
    )


async def test_synthesis_also_works_with_client_without_astream():
    """Deterministik ozete DUSMEMELI - LLM yine cagrilmali."""
    llm = TekSeferlikLLM()

    state = await _orchestrator(llm).graph.ainvoke(
        {"user_query": "Portfoyum nasil?", "user_id": 1, "thread_id": 1},
        config={"configurable": {"thread_id": "1"}},
    )

    assert llm.gorulen_prompt is not None
    assert state["final_response"].startswith("Sentezlenmis yanit")


async def test_agent_data_enters_prompt_on_non_streaming_path():
    llm = TekSeferlikLLM()

    await _orchestrator(llm).graph.ainvoke(
        {"user_query": "Portfoyum nasil?", "user_id": 1, "thread_id": 2},
        config={"configurable": {"thread_id": "2"}},
    )

    assert "toplam 100.000 TL" in llm.gorulen_prompt


async def test_non_streaming_reply_sent_as_single_token_event():
    """Frontend'in tek render yolu korunur."""
    llm = TekSeferlikLLM()
    orchestrator = _orchestrator(llm)

    olaylar = [o async for o in orchestrator.stream_request("Portfoyum nasil?", 1, 3)]

    tokenlar = [o for o in olaylar if o["type"] == "token"]
    assert tokenlar
    assert "".join(o["content"] for o in tokenlar).startswith("Sentezlenmis yanit")


def test_messages_flattened_with_role_labels():
    """Rol ayrimi kaybolursa uyum kurallari kullanici metnine karisir."""
    from langchain_core.messages import HumanMessage, SystemMessage

    metin = _messages_to_text([SystemMessage(content="kural"), HumanMessage(content="soru")])

    assert "[SISTEM]" in metin and "[KULLANICI]" in metin
    assert metin.index("[SISTEM]") < metin.index("[KULLANICI]")


# ---------------------------------------------------------------------------
# Dusunme bayragi YALNIZCA Nemotron'a gonderilir
#
# NIM katalogunda 22 yayincinin 83 modeli var; `enable_thinking` yalnizca
# Nemotron sohbet sablonunda tanimli. Bayragi herkese gondermek, model
# degistirmeyi gereksizce riskli yapardi (akitan yolda 400 = sentez duser).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [
        "google/gemma-4-31b-it",
        "mistralai/mistral-large-2-instruct",
        "openai/gpt-oss-120b",
        "deepseek-ai/deepseek-v4-flash-0731",
    ],
)
def test_no_extra_body_sent_to_non_nemotron_model(environment, model):
    llm, _ = environment(SYNTHESIZER_MODEL=model, NVIDIA_API_KEY="test")

    assert not llm.get_streaming_llm("synthesizer").extra_body


@pytest.mark.parametrize(
    "model",
    ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3.5-lightning-30b-a3b"],
)
def test_extra_body_sent_to_nemotron_model(environment, model):
    llm, _ = environment(SYNTHESIZER_MODEL=model, NVIDIA_API_KEY="test")

    ek = llm.get_streaming_llm("synthesizer").extra_body
    assert ek == {"chat_template_kwargs": {"enable_thinking": False}}


async def test_one_shot_path_also_decides_by_model(environment):
    """`generate()` ek govdeyi kendi model adina bakarak secmeli."""
    llm, _ = environment(NVIDIA_API_KEY="test")
    gorulen: list[dict] = []

    async def fake(model, prompt, ek):
        gorulen.append(ek)
        return _SahteYanit()

    gemma = llm.NvidiaLLMClient(
        api_key="test", default_model="google/gemma-4-31b-it", base_url="http://ornek/v1"
    )
    gemma._call = fake
    await gemma.generate("selam")

    nemotron = llm.NvidiaLLMClient(
        api_key="test",
        default_model="nvidia/nemotron-3-super-120b-a12b",
        base_url="http://ornek/v1",
    )
    nemotron._call = fake
    await nemotron.generate("selam")

    assert gorulen[0] == {}, "gemma'ya ek govde gitmemeli"
    assert "extra_body" in gorulen[1], "nemotron'a gitmeli"


# ---------------------------------------------------------------------------
# SENTEZDE IKI KADEMELI ZAMAN ASIMI
# ---------------------------------------------------------------------------
#
# 27 Agustos 2026 model testinde sentez iki kez zaman asimina ugradi ve
# kullanici EKRANDA YARIM CUMLEYLE kaldi:
#
#     "... Bu karin ana kaynagi BTC. Risk skoru 78/100 ile"
#     synthesizer ajani gecici olarak tamamlanamadi (timeout).
#
# Iki ayri kusur vardi:
#   1. TEK dis sinir vardi (90 sn) ve TOPLAM sureyi olcuyordu. Model ortada
#      takildiginda 90 saniye bosuna bekleniyordu.
#   2. Zaman asiminda uretilen metin ATILIP deterministik ozete donuluyordu -
#      ama token'lar KULLANICIYA COKTAN GITMISTI ve geri alinamiyordu; yeni
#      metin de `token_yayinlandi` yuzunden hic gonderilmiyordu.


class _TakilanAkis:
    """Anlamli metin uretir, sonra ORTADA takilir."""

    PARCALAR = (
        "Portfoyunuz genel olarak karda: toplam degeri 2.310.063,42 TL, ",
        "maliyeti 2.074.847,85 TL, yani %11,34 kar elde etmis durumdasiniz. ",
        "Bu karin ana kaynagi BTC. Risk skoru 78/100 ile",
    )

    async def astream(self, messages, config=None):
        for parca in self.PARCALAR:
            yield type("C", (), {"content": parca})()
        await asyncio.sleep(3600)


class _HicUretmeyenAkis:
    async def astream(self, messages, config=None):
        await asyncio.sleep(3600)
        yield None  # pragma: no cover


class _SahteGuvenlik:
    async def check_input_node(self, state):
        return {"is_input_safe": True}

    async def security_gate_node(self, state):
        return {"is_output_safe": True}


def _orkestratör(llm, *, dis: int = 60, ic: int = 2) -> Orchestrator:
    return Orchestrator(
        agents={},
        security_agent=_SahteGuvenlik(),
        synthesizer_llm=llm,
        synthesizer_timeout_seconds=dis,
        synthesizer_stall_seconds=ic,
    )


def _durum() -> AgentState:
    state = AgentState(user_query="Portfoyum nasil?", user_id=1, thread_id=1)
    state.portfolio_data = {"summary_text": "Portfoy toplam degeri 2.310.063 TL."}
    return state


async def test_akis_durursa_ic_sinir_erken_devreye_girer():
    """Dis sinir 60 sn olsa bile ic sinir (2 sn) beklemeyi kesmelidir."""
    orchestrator = _orkestratör(_TakilanAkis(), dis=60, ic=2)

    basla = time.perf_counter()
    await orchestrator.synthesize(_durum())
    gecen = time.perf_counter() - basla

    assert gecen < 10, f"ic sinir devreye girmedi, {gecen:.1f} sn beklendi"


async def test_yarim_kalan_sentez_KORUNUR():
    """Uretilmis analiz atilmamali - kullanicinin ekranina zaten gitti."""
    orchestrator = _orkestratör(_TakilanAkis())

    sonuc = await orchestrator.synthesize(_durum())
    metin = sonuc["final_response"]

    # Uretilen icerik duruyor
    assert "2.310.063,42 TL" in metin
    assert "%11,34" in metin
    # Yarim cumle ATILDI
    assert "Risk skoru 78/100 ile" not in metin
    # Durum notu ve uyum ibaresi EKLENDI
    assert KISMI_YANIT_NOTU in metin
    assert YATIRIM_TAVSIYESI_IBARESI in metin


async def test_kullanilamayacak_kadar_kisa_kisim_deterministik_ozete_duser():
    orchestrator = _orkestratör(_HicUretmeyenAkis(), dis=30, ic=1)

    metin = (await orchestrator.synthesize(_durum()))["final_response"]

    assert KISMI_YANIT_NOTU not in metin
    assert "2.310.063 TL" in metin  # deterministik ozet ajan verisinden geldi


def test_ic_sinir_dis_sinirdan_kucuk_tutulur():
    """YAPISAL GUVENCE: aksi halde dis iptal once girer, ic sinir hic calismaz."""
    for dis in (5, 30, 90):
        orchestrator = _orkestratör(_HicUretmeyenAkis(), dis=dis, ic=9_999)
        assert orchestrator.synthesizer_stall_seconds < dis, f"dis={dis}"
