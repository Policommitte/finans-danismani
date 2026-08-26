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

import importlib

import pytest

import app.config
import app.core.llm
import app.engine.factory
from app.agents.base import BaseAgent
from app.agents.security_agent import SecurityAgent
from app.engine.orchestrator import Orchestrator, _mesajlari_metne_cevir
from app.orchestration.models import AgentState


@pytest.fixture
def ortam(monkeypatch):
    """Model/anahtar ortam degiskenlerini kurar ve modulleri yeniden yukler.

    `Settings` ornegi modul yuklenirken bir kez okundugu icin `monkeypatch.setenv`
    tek basina yetmez - config ve llm modullerinin yeniden yuklenmesi gerekir.

    ⚠️ DELENV YETMEZ, BOS STRING SART. `Settings` yalnizca ortam degiskenlerini
    degil `backend/.env` DOSYASINI da okur (`env_file=".env"`). Degiskeni
    silmek dosyadaki degeri ortaya cikarir: gercek bir NVIDIA anahtari ve
    `DEFAULT_MODEL` tanimlamis bir gelistiricide "model tanimli degilse None
    doner" testleri PATLAR - kod dogru olsa bile. Bos string atamak ise ortam
    degiskeni olarak .env'i EZER (pydantic-settings onceligi) ve testi
    gelistiricinin yerel kurulumundan bagimsiz kilar.
    """

    def _kur(**degiskenler: str):
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

    yield _kur

    # Diger test dosyalari orijinal ayarlarla devam etsin.
    importlib.reload(app.config)
    importlib.reload(app.core.llm)
    importlib.reload(app.engine.factory)


# ---------------------------------------------------------------------------
# get_streaming_llm
# ---------------------------------------------------------------------------


def test_nim_modeli_icin_akitan_istemci_kurulur(ortam):
    llm, _ = ortam(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    model = llm.get_streaming_llm("synthesizer")

    assert model is not None
    # LangGraph token akisi YALNIZCA LangChain chat modelleriyle calisir.
    assert hasattr(model, "astream")
    assert model.model_name == "nvidia/nemotron-3-ultra"
    assert model.openai_api_base.rstrip("/").endswith("/v1")
    assert model.streaming is True


def test_dusunme_kapali_gonderilir(ortam):
    """Akil yurutme izi hem sentez suresini uzatir hem de guvenlik ajaninin
    'ilk sayiyi oku' ayristiricisini bozar."""
    llm, _ = ortam(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    model = llm.get_streaming_llm("synthesizer")

    assert model.extra_body == {"chat_template_kwargs": {"enable_thinking": False}}


def test_dusunme_bayragi_top_level_GONDERILMEZ(ortam):
    """Canlida olculdu: top-level `enable_thinking` 400 aldiriyor.

    OpenAI uyumlu uc tanimadigi govde alanini yok saymiyor, istegi reddediyor.
    Bir ara "her ihtimale karsi ikisini birden gonderelim" denmisti; sonucu
    TUM LLM cagrilarinin patlamasi oldu (ajanlar `llm_error`, sentez
    deterministik ozet). Bu test o denemeyi geri gelmekten alikoyar.
    """
    llm, _ = ortam(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    assert "enable_thinking" not in llm.get_streaming_llm("synthesizer").extra_body


def test_extra_body_kapatma_anahtari_calisir(ortam):
    """Model ek alani tanimayip 400 donerse kacis kapisi olmali."""
    llm, _ = ortam(
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


def _nim_istemcisi(llm_modulu):
    return llm_modulu.NvidiaLLMClient(
        api_key="test", default_model="nvidia/nemotron-3-ultra", base_url="http://ornek/v1"
    )


async def test_ek_govde_reddedilirse_bayraksiz_tekrar_denenir(ortam):
    """Tek bir govde alani yuzunden tum LLM katmani durmamali."""
    llm, _ = ortam(NVIDIA_API_KEY="test")
    istemci = _nim_istemcisi(llm)
    cagrilar: list[dict] = []

    async def sahte(model, prompt, ek):
        cagrilar.append(ek)
        if ek:
            raise _Sahte400()
        return _SahteYanit()

    istemci._cagir = sahte

    assert await istemci.generate("selam") == "merhaba"
    assert len(cagrilar) == 2
    assert "extra_body" in cagrilar[0]
    assert cagrilar[1] == {}


async def test_400_disindaki_hata_tekrar_denenmez(ortam):
    """Gecersiz anahtari 'bayrak sorunu' sanip iki kez denemek yanlis olurdu."""
    llm, _ = ortam(NVIDIA_API_KEY="test")
    istemci = _nim_istemcisi(llm)
    cagrilar: list[dict] = []

    async def sahte(model, prompt, ek):
        cagrilar.append(ek)
        raise _Sahte401()

    istemci._cagir = sahte

    with pytest.raises(_Sahte401):
        await istemci.generate("selam")
    assert len(cagrilar) == 1


def test_ek_govde_reddi_yalnizca_400_de_dogru(ortam):
    llm, _ = ortam()

    assert llm._ek_govde_reddedildi(_Sahte400()) is True
    assert llm._ek_govde_reddedildi(_Sahte401()) is False
    assert llm._ek_govde_reddedildi(RuntimeError("baglanti koptu")) is False


def test_gemini_modelinde_akitan_istemci_kurulmaz(ortam):
    """`langchain-google-genai` bagimliligi yok; cagiran taraf duse duse
    tek seferlik istemciye iner."""
    llm, _ = ortam(SYNTHESIZER_MODEL="gemini-3.5-flash-lite", GEMINI_API_KEY="test")

    assert llm.get_streaming_llm("synthesizer") is None


def test_model_adi_yoksa_none_doner(ortam):
    llm, _ = ortam(NVIDIA_API_KEY="test")

    assert llm.get_streaming_llm("synthesizer") is None


def test_anahtar_yoksa_none_doner(ortam):
    llm, _ = ortam(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra")

    assert llm.get_streaming_llm("synthesizer") is None


def test_slashsiz_model_adi_gemini_sanilir(ortam):
    """`.env`'e 'nemotron-3-ultra' yazmak sessizce yanlis saglayiciya gider.

    Bu davranis BILINCLI (saglayici model adindan anlasiliyor) ama tuzak;
    test onu gorunur kiliyor.
    """
    llm, _ = ortam()

    assert llm.saglayici_belirle("nemotron-3-ultra") == "gemini"
    assert llm.saglayici_belirle("nvidia/nemotron-3-ultra") == "nvidia"


# ---------------------------------------------------------------------------
# factory: sentez modeli gercekten orchestrator'a gecirilir mi?
# ---------------------------------------------------------------------------


def test_factory_akitan_modeli_secer(ortam):
    _, factory = ortam(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    model = factory.build_synthesizer_llm()

    assert model is not None and hasattr(model, "astream")


def test_factory_akitan_kurulamazsa_tek_seferlige_duser(ortam):
    """Gemini sentezi: akis yok ama sentez YINE LLM ile yapilmali."""
    _, factory = ortam(SYNTHESIZER_MODEL="gemini-3.5-flash-lite", GEMINI_API_KEY="test")

    model = factory.build_synthesizer_llm()

    assert model is not None
    assert hasattr(model, "generate")
    assert not hasattr(model, "astream")


def test_model_tanimli_degilse_deterministik_kalir(ortam):
    _, factory = ortam()

    assert factory.build_synthesizer_llm() is None


def test_orchestrator_sentez_modelini_alir(ortam, monkeypatch):
    """Asil regresyon: `build_orchestrator` bu alani bos birakiyordu."""
    _, factory = ortam(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

    orchestrator = factory.build_orchestrator()

    assert orchestrator.synthesizer_llm is not None


def test_cagiran_taraf_sentez_modelini_ezebilir(ortam):
    _, factory = ortam(SYNTHESIZER_MODEL="nvidia/nemotron-3-ultra", NVIDIA_API_KEY="test")

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


async def test_astreamsiz_istemciyle_de_sentez_yapilir():
    """Deterministik ozete DUSMEMELI - LLM yine cagrilmali."""
    llm = TekSeferlikLLM()

    state = await _orchestrator(llm).graph.ainvoke(
        {"user_query": "Portfoyum nasil?", "user_id": 1, "thread_id": 1},
        config={"configurable": {"thread_id": "1"}},
    )

    assert llm.gorulen_prompt is not None
    assert state["final_response"].startswith("Sentezlenmis yanit")


async def test_astreamsiz_yolda_ajan_verisi_prompta_girer():
    llm = TekSeferlikLLM()

    await _orchestrator(llm).graph.ainvoke(
        {"user_query": "Portfoyum nasil?", "user_id": 1, "thread_id": 2},
        config={"configurable": {"thread_id": "2"}},
    )

    assert "toplam 100.000 TL" in llm.gorulen_prompt


async def test_astreamsiz_yanit_tek_token_olayi_olarak_gider():
    """Frontend'in tek render yolu korunur."""
    llm = TekSeferlikLLM()
    orchestrator = _orchestrator(llm)

    olaylar = [o async for o in orchestrator.stream_request("Portfoyum nasil?", 1, 3)]

    tokenlar = [o for o in olaylar if o["type"] == "token"]
    assert tokenlar
    assert "".join(o["content"] for o in tokenlar).startswith("Sentezlenmis yanit")


def test_mesajlar_rol_etiketiyle_duzlestirilir():
    """Rol ayrimi kaybolursa uyum kurallari kullanici metnine karisir."""
    from langchain_core.messages import HumanMessage, SystemMessage

    metin = _mesajlari_metne_cevir([SystemMessage(content="kural"), HumanMessage(content="soru")])

    assert "[SISTEM]" in metin and "[KULLANICI]" in metin
    assert metin.index("[SISTEM]") < metin.index("[KULLANICI]")
