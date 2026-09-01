"""Ajanlarin kullandigi LLM istemci katmani.

⚠️ KODA HICBIR MODEL ADI GOMULU DEGILDIR. Kullanilacak model tamamen
    konfigurasyondan gelir:

        DEFAULT_MODEL=...        # tum ajanlar icin varsayilan
        SYNTHESIZER_MODEL=...    # ajan bazli override (opsiyonel)

    Model adi bos oldugu surece `get_llm_client()` `None` doner ve ajanlar
    LLM'SIZ calisir: MarketResearchAgent kaynaklardan deterministik alinti
    uretir, synthesizer deterministik ozet yazar, guvenlik ajani yalnizca kural
    motoruyla karar verir. Yani sistem model secilmeden de uctan uca calisir.

IKI SAGLAYICI DESTEKLENIR
-------------------------

    gemini   Google AI Studio      google-genai SDK
    nvidia   NVIDIA NIM (build.nvidia.com)   OpenAI uyumlu REST

Saglayici MODEL ADINDAN OTOMATIK ANLASILIR - ayri bir ayar gerekmez:

    DEFAULT_MODEL=gemini-3.5-flash-lite               -> gemini
    DEFAULT_MODEL=nvidia/nemotron-3-super-120b-a12b   -> nvidia
    DEFAULT_MODEL=meta/llama-3.3-70b-instruct         -> nvidia

Kural basit: NIM kimlikleri her zaman `yayinci/model` bicimindedir ve `/`
icerir; Gemini kimlikleri icermez. Bu ayrimi `LLM_PROVIDER` ile elle de
zorlayabilirsiniz (nadiren gerekir).

Ajanlar dogrudan istemci sinifina degil `LLMClient` protokoluna baglanir;
boylece testlerde gercek API cagrisi yapmadan sahte bir `generate()`
enjekte edilebilir ve saglayici degisirse yalnizca bu dosya degisir.

NEDEN IKI SAGLAYICI
-------------------
Model secim testi (`polifin-model-secimi/`) sirasinda ogrenildi: Gemini'nin
ucretsiz katmani gunde 20 istekte kesiliyor (`gemini-3.5-flash` icin hata
mesajinda birebir "limit: 20"), NIM'in kredisi ise bol. Ayrica bes haftada
alti aday model kapandi. Tek saglayiciya baglanmak, bir sonraki kapanmada
sistemi durdurur; iki saglayici arasinda gecis `.env`'de tek satir olmali.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.config import settings

logger = logging.getLogger(__name__)

#: NIM istekleri icin varsayilan ek govde alanlari.
#:
#: Nemotron 3 gibi akil yurutme modellerinde dusunme VARSAYILAN OLARAK ACIK ve
#: dusunce metni yanittan ONCE uretiliyor. Bu iki yerde zarar veriyor:
#:
#:   1. Guvenlik ajani (`security_agent.py::_classify_with_llm`) yanittaki ILK
#:      sayiyi skor olarak aliyor. Dusunce metninde gecen herhangi bir sayi
#:      skor sanilir - hata vermez, SESSIZCE YANLIS skor uretir.
#:   2. Sentezleyicinin 40 sn ust siniri var (`synthesizer_timeout_seconds`).
#:      Dusunce token'lari tam cevaba varis suresini uzatir.
#:
#: Bu yuzden dusunme kapali gonderiliyor.
#:
#: ⚠️ BICIM TEK: bayrak `chat_template_kwargs` ICINE gomulur. NVIDIA'nin kendi
#: ornegi birebir sudur:
#:
#:     extra_body={"chat_template_kwargs": {"enable_thinking": False}}
#:
#: Bir ara bunu "zararsiz olur" diyerek top-level `enable_thinking` ile BIRLIKTE
#: gonderdik. Zararsiz degil: OpenAI uyumlu uc tanimadigi govde alanini yok
#: saymiyor, 400 donuyor. Sonuc her LLM cagrisinin patlamasiydi - ajanlar
#: `llm_error` uretip deterministik ozete dustu, sentez de calismadi. Bu yuzden
#: "her ihtimale karsi ikisini birden gonder" YAPMAYIN.
#:
#: Yine de bir varyant reddedilirse `generate()` ek govdesiz bir kez daha dener
#: (bkz. asagisi); kalici olarak kapatmak icin `LLM_NVIDIA_EXTRA_BODY_OFF=1`.
_NIM_DUSUNME_KAPALI: dict[str, Any] = {"chat_template_kwargs": {"enable_thinking": False}}

#: Bu bayragi ANLAYAN model ailesi. NIM katalogunda 22 yayincinin 83 modeli var
#: (google/gemma-4, mistralai/..., deepseek-ai/..., openai/gpt-oss...) ve
#: `enable_thinking` bunlarin hicbirinde YOK - Nemotron'a ozgu bir sohbet
#: sablonu argumani.
#:
#: Herkese gondermek model degistirmeyi gereksizce riskli yapardi: bayragi
#: tanimayan uc 400 doner. Tek seferlik yolda ek govdesiz tekrar denemesi var
#: ama AKITAN yolda (ChatOpenAI) yok - sentez dogrudan duserdi.
_DUSUNME_BAYRAGINI_ANLAYAN = "nemotron"


def _nim_ek_govde(model: str) -> dict[str, Any]:
    """Modele gore NIM `extra_body` alanlari; uymuyorsa BOS sozluk.

    Bos donmesi "ayar unutuldu" degil, "bu model o bayragi tanimiyor"
    demektir - Nemotron disindaki modellerde dogru davranis budur.
    """
    if settings.llm_nvidia_extra_body_off:
        return {}
    if _DUSUNME_BAYRAGINI_ANLAYAN not in (model or "").lower():
        return {}
    return dict(_NIM_DUSUNME_KAPALI)


def _ek_govde_reddedildi(hata: Exception) -> bool:
    """Sunucu istegi EK GOVDE yuzunden mi reddetti?

    Ayrimi kesin yapmak mumkun degil (400 baska sebeplerle de gelir) ama
    ek govdesiz bir kez daha denemek ucuz: baska bir 400 ise ayni hata tekrar
    gelir ve yukari birakilir.
    """
    return getattr(hata, "status_code", None) == 400 or " 400 " in f" {hata} "


class LLMClient(Protocol):
    async def generate(self, prompt: str, *, model: str | None = None) -> str: ...


def saglayici_belirle(model: str) -> str:
    """Model adindan saglayiciyi cikarir: "gemini" | "nvidia".

    `LLM_PROVIDER` tanimliysa o kazanir. Aksi halde `/` iceren kimlikler NIM
    (`nvidia/...`, `meta/...`, `google/gemma-3-12b-it`), digerleri Gemini.
    """
    elle = (settings.llm_provider or "").strip().lower()
    if elle:
        return elle
    return "nvidia" if "/" in model else "gemini"


class GeminiLLMClient:
    """google-genai SDK uzerinden Gemini'ye baglanan ince bir sarmalayici.

    `default_model` ZORUNLUDUR ve konfigurasyondan gelir; sinif kendi icinde
    bir model adi varsaymaz (bkz. modul docstring'i).
    """

    def __init__(self, api_key: str, default_model: str) -> None:
        if not default_model:
            raise ValueError("LLM model adi bos olamaz (DEFAULT_MODEL tanimlanmali).")

        from google import genai  # gecikmeli import: paket sadece gercekten kullanildiginda gerekli

        self._client = genai.Client(api_key=api_key)
        self._default_model = default_model

    @property
    def model(self) -> str:
        return self._default_model

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        response = await self._client.aio.models.generate_content(
            model=model or self._default_model,
            contents=prompt,
        )
        return response.text or ""

    async def generate_with_image(
        self, prompt: str, image_bytes: bytes, mime_type: str, *, model: str | None = None
    ) -> str:
        """Goersel + metin girdiyle uretim - sohbet ek analizi icin
        (`app/services/chat_attachments.py`). `NvidiaLLMClient`'ta BILEREK
        YOK: NIM modellerinin coğu goersel desteklemez, cagiran taraf once
        `saglayici_belirle()` ile Gemini oldugunu dogrular."""
        from google.genai import types

        response = await self._client.aio.models.generate_content(
            model=model or self._default_model,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
        )
        return response.text or ""


class NvidiaLLMClient:
    """NVIDIA NIM (build.nvidia.com) - OpenAI uyumlu uc.

    NIM, OpenAI'nin API sozlesmesini konustugu icin ayri bir SDK'ya gerek yok;
    `openai` paketi `base_url` degistirilerek kullaniliyor.
    """

    def __init__(self, api_key: str, default_model: str, base_url: str) -> None:
        if not default_model:
            raise ValueError("LLM model adi bos olamaz (DEFAULT_MODEL tanimlanmali).")

        from openai import AsyncOpenAI  # gecikmeli import

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
        self._default_model = default_model

    @property
    def model(self) -> str:
        return self._default_model

    async def _cagir(self, model: str | None, prompt: str, ek: dict[str, Any]):
        return await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            **ek,
        )

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        govde = _nim_ek_govde(model or self._default_model)
        ek: dict[str, Any] = {"extra_body": govde} if govde else {}

        try:
            yanit = await self._cagir(model, prompt, ek)
        except Exception as hata:  # noqa: BLE001 - tur openai paketine bagli
            # Ek govde reddedildiyse ONU SUCLAMA, ama modeli de kaybetme:
            # bayraksiz bir kez daha dene. Bes haftada alti aday model
            # kapanan bir ortamda, tek bir govde alani yuzunden tum LLM
            # katmaninin durmasi kabul edilebilir degil.
            if not ek or not _ek_govde_reddedildi(hata):
                raise
            logger.warning(
                "NIM ek govdeyi reddetti; dusunme bayragi olmadan yeniden deneniyor",
                extra={"model": model or self._default_model, "hata": str(hata)[:200]},
            )
            yanit = await self._cagir(model, prompt, {})

        if not yanit.choices:
            return ""
        mesaj = yanit.choices[0].message
        # Akil yurutme modelleri icerigi bos birakip dusunceyi ayri alanda
        # dondurebiliyor; o durumda bos string donmek yerine eldekini veriyoruz.
        return (mesaj.content or "") or (getattr(mesaj, "reasoning_content", "") or "")


def get_streaming_llm(agent: str = "synthesizer"):
    """LangGraph'in TOKEN AKISINI besleyebilen chat modeli; kurulamazsa `None`.

    NEDEN AYRI BIR FONKSIYON
    ------------------------
    Bu dosyadaki `GeminiLLMClient` / `NvidiaLLMClient` ince istemcilerdir ve
    yalnizca tek seferlik `generate()` sunar. Sentez adiminda bu YETMEZ:

        LangGraph token'lari CALLBACK ZINCIRI uzerinden yakalar
        (`stream_mode="messages"`) ve o zincire yalnizca LangChain chat
        modelleri `AIMessageChunk` yayinlar.

    El yapimi bir `astream` metodu yazmak ise ise yaramaz - uretilen parcalar
    callback zincirine girmedigi icin `Orchestrator._extract_token` onlari HIC
    gormez. Bu yuzden akitan model LangChain'in kendi `ChatOpenAI` sinifidir;
    NIM OpenAI sozlesmesini konustugu icin yalnizca `base_url` degistirilir.

    Gemini icin `None` doner: `langchain-google-genai` bagimliligi eklenmedi.
    Cagiran taraf (`factory.build_synthesizer_llm`) o durumda tek seferlik
    istemciye duser - sentez yine LLM ile yapilir, sadece token token akmaz.
    """
    model = settings.model_for(agent)
    if not model:
        return None

    saglayici = saglayici_belirle(model)
    if saglayici != "nvidia":
        logger.info(
            "akitan sentez modeli kurulmadi, tek seferlik istemciye dusulecek",
            extra={"agent": agent, "model": model, "saglayici": saglayici},
        )
        return None

    anahtar = settings.api_key_for(saglayici)
    if not anahtar:
        return None

    try:
        from langchain_openai import ChatOpenAI  # gecikmeli import
    except ImportError:
        logger.warning(
            "langchain-openai kurulu degil; sentez token token akmayacak",
            extra={"agent": agent, "model": model},
        )
        return None

    govde = _nim_ek_govde(model)
    ek: dict[str, Any] = {"extra_body": govde} if govde else {}

    return ChatOpenAI(
        model=model,
        api_key=anahtar,
        base_url=settings.nvidia_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        streaming=True,
        **ek,
    )


def get_llm_client(agent: str) -> LLMClient | None:
    """Ajana ozel LLM istemcisi uretir; anahtar VEYA model tanimli degilse `None`.

    `None` donmesi bir hata DEGILDIR - "LLM'siz calis" demektir. Cagiran taraf
    (`app.engine.factory`) bunu dogal bir durum olarak isler.
    """
    model = settings.model_for(agent)
    if not model:
        logger.info(
            "LLM baglanmadi, ajan modelsiz calisacak",
            extra={"agent": agent, "sebep": "model adi bos"},
        )
        return None

    saglayici = saglayici_belirle(model)
    anahtar = settings.api_key_for(saglayici)

    if not anahtar:
        logger.info(
            "LLM baglanmadi, ajan modelsiz calisacak",
            extra={"agent": agent, "model": model, "saglayici": saglayici, "sebep": "anahtar yok"},
        )
        return None

    if saglayici == "nvidia":
        return NvidiaLLMClient(
            api_key=anahtar, default_model=model, base_url=settings.nvidia_base_url
        )
    if saglayici == "gemini":
        return GeminiLLMClient(api_key=anahtar, default_model=model)

    logger.warning(
        "Bilinmeyen LLM saglayicisi, ajan modelsiz calisacak",
        extra={"agent": agent, "saglayici": saglayici},
    )
    return None
