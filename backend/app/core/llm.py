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

import asyncio
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


#: OpenRouter'in BIRLESIK akil-yurutme parametresi.
#:
#: NEDEN ZORUNLU (olculdu, 1 Eylul 2026): `ling-3.0-flash-fin` bir akil
#: yurutme modeli ve dusunme VARSAYILAN OLARAK ACIK geliyor. Bayraksiz
#: gonderilen istek 14,4 sn surdu, 1500 cikis token'inin TAMAMINI INGILIZCE
#: dusunce zincirine harcadi ve `content` BOS dondu. Bayrakla ayni istek
#: 2,6 sn ve 161 token - ustelik Turkcesi duzgun.
#:
#: Bu, NIM tarafindaki `_NIM_DUSUNME_KAPALI` ile ayni sorunun OpenRouter
#: karsiligidir; parametre adi farkli, sebep ayni.
_OPENROUTER_DUSUNME_KAPALI: dict[str, Any] = {"reasoning": {"enabled": False}}


def _ek_govde(saglayici: str, model: str) -> dict[str, Any]:
    """Saglayiciya gore `extra_body`. Uymayan her durumda BOS sozluk."""
    if settings.llm_nvidia_extra_body_off:
        return {}
    if saglayici == "openrouter":
        return dict(_OPENROUTER_DUSUNME_KAPALI)
    return _nim_ek_govde(model)


#: GECICI sunucu hatalari - yeniden denemeye deger.
#:
#: NEDEN VAR (olculdu, 1 Eylul 2026): ayni prompt `nemotron-3-super` ucuna
#: 5 kez gonderildi, 2'si `503 Service temporarily overloaded` dondu. Kodda
#: yeniden deneme olmadigi icin TEK bir 503 ajani komple dusuruyor ve
#: kullaniciya "portfolio ajani gecici olarak tamamlanamadi" yaziliyordu -
#: oysa hatanin adi zaten "gecici".
#:
#: 404 de listede: ayni uctan 404 alindigi goruldugu halde model katalogda
#: duruyordu ve saniyeler sonra ayni istek calisiyordu.
_GECICI_HATA_KODLARI = (408, 409, 429, 404, 500, 502, 503, 504)

#: Toplam deneme = 1 + bu sayi. Ust sinir bilincli olarak DUSUK: ajanin dis
#: zaman asimi 45 sn (`agent_timeout_seconds`), ic LLM butcesi bunun %60'i.
#: Uzun bir geri cekilme zinciri butceyi yer ve ajan zaten deterministik
#: ozete duser - beklemek kullaniciya hicbir sey kazandirmaz.
_YENIDEN_DENEME = 2
_BEKLEME_SANIYE = (1.0, 3.0)


def _gecici_hata_mi(hata: Exception) -> bool:
    """Sunucu tarafi GECICI bir hata mi (yeniden denemeye deger mi)?"""
    kod = getattr(hata, "status_code", None)
    if kod in _GECICI_HATA_KODLARI:
        return True
    metin = f" {hata} "
    return any(f" {k} " in metin or f"code: {k}" in metin for k in _GECICI_HATA_KODLARI)


def _ek_govde_reddedildi(hata: Exception) -> bool:
    """Sunucu istegi EK GOVDE yuzunden mi reddetti?

    Ayrimi kesin yapmak mumkun degil (400 baska sebeplerle de gelir) ama
    ek govdesiz bir kez daha denemek ucuz: baska bir 400 ise ayni hata tekrar
    gelir ve yukari birakilir.
    """
    return getattr(hata, "status_code", None) == 400 or " 400 " in f" {hata} "


class LLMClient(Protocol):
    async def generate(self, prompt: str, *, model: str | None = None) -> str: ...


#: Model adinda ACIK saglayici oneki olarak taninan degerler.
#: `openrouter:inclusionai/ling-3.0-flash-fin:free` -> ("openrouter", "inclusionai/...")
_SAGLAYICI_ONEKLERI = ("openrouter", "nvidia", "gemini")

#: OpenRouter'in ROTA son ekleri. Onek yazilmadan bu son eki tasiyan bir
#: kimlik gelirse saglayici yine de dogru anlasilir - kullanicilar model
#: adini siteden kopyalayip yapistiriyor ve `/` iceren her kimligi NIM sanan
#: eski kural bunu sessizce 404'e goturuyordu.
_OPENROUTER_ROTA_SONEKLERI = (":free", ":nitro", ":floor", ":online")


def model_coz(model: str) -> tuple[str, str]:
    """Yapilandirmadaki model adini (saglayici, GERCEK model kimligi) yapar.

    Uc yol vardir, sirasiyla:

      1. ACIK ONEK   `openrouter:inclusionai/ling-3.0-flash-fin:free`
         Onek soyulur; geri kalan API'ye oldugu gibi gider. `:free` son eki
         model kimliginin PARCASI oldugu icin yalnizca ILK iki nokta ayrilir.
      2. ROTA SONEKI `inclusionai/ling-3.0-flash-fin:free`
         Onek unutulmus ama son ek OpenRouter'a ozgu - saglayici anlasilir.
      3. ESKI KURAL  `/` varsa NIM, yoksa Gemini (`saglayici_belirle`).
    """
    ham = (model or "").strip()
    if not ham:
        return "", ""

    onek, ayrac, kalan = ham.partition(":")
    if ayrac and onek.lower() in _SAGLAYICI_ONEKLERI and kalan:
        return onek.lower(), kalan

    if ham.lower().endswith(_OPENROUTER_ROTA_SONEKLERI):
        return "openrouter", ham

    return saglayici_belirle(ham), ham


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

    def __init__(
        self, api_key: str, default_model: str, base_url: str, saglayici: str = "nvidia"
    ) -> None:
        if not default_model:
            raise ValueError("LLM model adi bos olamaz (DEFAULT_MODEL tanimlanmali).")

        from openai import AsyncOpenAI  # gecikmeli import

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
        self._default_model = default_model
        #: `extra_body` secimi buna bakar. Varsayilan "nvidia" - eski
        #: cagrilar (ve testler) davranis degistirmeden calismaya devam eder.
        self._saglayici = saglayici

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
        govde = _ek_govde(self._saglayici, model or self._default_model)
        ek: dict[str, Any] = {"extra_body": govde} if govde else {}

        yanit = None
        kalan_deneme = _YENIDEN_DENEME
        while True:
            try:
                yanit = await self._cagir(model, prompt, ek)
                break
            except Exception as hata:  # noqa: BLE001 - tur openai paketine bagli
                # 1) Ek govde reddedildiyse ONU SUCLAMA, ama modeli de
                #    kaybetme: bayraksiz bir kez daha dene. Bu deneme
                #    yeniden-deneme butcesini HARCAMAZ - farkli bir sorun.
                if ek and _ek_govde_reddedildi(hata):
                    logger.warning(
                        "ek govde reddedildi; bayrak olmadan yeniden deneniyor",
                        extra={"model": model or self._default_model, "hata": str(hata)[:200]},
                    )
                    ek = {}
                    continue

                # 2) Gecici sunucu hatasi: kisa bir geri cekilmeyle tekrar dene.
                if kalan_deneme > 0 and _gecici_hata_mi(hata):
                    bekleme = _BEKLEME_SANIYE[_YENIDEN_DENEME - kalan_deneme]
                    logger.warning(
                        "gecici LLM hatasi; yeniden deneniyor",
                        extra={
                            "model": model or self._default_model,
                            "bekleme": bekleme,
                            "kalan": kalan_deneme,
                            "hata": str(hata)[:200],
                        },
                    )
                    kalan_deneme -= 1
                    await asyncio.sleep(bekleme)
                    continue

                raise

        if not yanit.choices:
            return ""
        mesaj = yanit.choices[0].message
        # Akil yurutme modelleri icerigi bos birakip dusunceyi ayri alanda
        # dondurebiliyor; o durumda bos string donmek yerine eldekini veriyoruz.
        #
        # ⚠️ ALAN ADI SAGLAYICIYA GORE DEGISIYOR. NIM `reasoning_content`
        # kullaniyor, OpenRouter `reasoning`. Yalnizca birine bakmak sessiz
        # bir bosluga yol acar: olculdu (1 Eylul 2026), OpenRouter yaniti
        # dolu geliyordu ama `reasoning_content` bos oldugu icin ajan bos
        # string alip deterministik ozete dusuyordu - hicbir hata vermeden.
        return (
            (mesaj.content or "")
            or (getattr(mesaj, "reasoning_content", "") or "")
            or (getattr(mesaj, "reasoning", "") or "")
        )


#: OpenRouter da OpenAI sozlesmesini konusur; ayni istemci yalnizca `base_url`
#: degisip kullanilir. NIM'e ozgu `extra_body` govdesi model adina bakan
#: `_nim_ek_govde()` tarafindan uretiliyor ve "nemotron" gecmeyen kimliklerde
#: BOS donuyor - yani OpenRouter'a NIM govdesi hic gitmez.
OpenAIUyumluLLMClient = NvidiaLLMClient

#: OpenAI uyumlu saglayicilar ve uclari. `get_streaming_llm` de bunu kullanir:
#: LangChain `ChatOpenAI` ikisiyle de calisir.
_OPENAI_UYUMLU_UCLAR = {
    "nvidia": lambda: settings.nvidia_base_url,
    "openrouter": lambda: settings.openrouter_base_url,
}


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
    saglayici, model = model_coz(settings.model_for(agent))
    if not model:
        return None

    if saglayici not in _OPENAI_UYUMLU_UCLAR:
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

    govde = _ek_govde(saglayici, model)
    ek: dict[str, Any] = {"extra_body": govde} if govde else {}

    return ChatOpenAI(
        model=model,
        api_key=anahtar,
        base_url=_OPENAI_UYUMLU_UCLAR[saglayici](),
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
    saglayici, model = model_coz(settings.model_for(agent))
    if not model:
        logger.info(
            "LLM baglanmadi, ajan modelsiz calisacak",
            extra={"agent": agent, "sebep": "model adi bos"},
        )
        return None

    anahtar = settings.api_key_for(saglayici)

    if not anahtar:
        logger.info(
            "LLM baglanmadi, ajan modelsiz calisacak",
            extra={"agent": agent, "model": model, "saglayici": saglayici, "sebep": "anahtar yok"},
        )
        return None

    if saglayici in _OPENAI_UYUMLU_UCLAR:
        return OpenAIUyumluLLMClient(
            api_key=anahtar,
            default_model=model,
            base_url=_OPENAI_UYUMLU_UCLAR[saglayici](),
            saglayici=saglayici,
        )
    if saglayici == "gemini":
        return GeminiLLMClient(api_key=anahtar, default_model=model)

    logger.warning(
        "Bilinmeyen LLM saglayicisi, ajan modelsiz calisacak",
        extra={"agent": agent, "saglayici": saglayici},
    )
    return None
