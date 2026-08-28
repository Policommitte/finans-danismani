"""Hibrit router'in LLM ayagi.

Orchestrator once kural tabanli (keyword) yonlendirmeyi dener; hicbir keyword
eslesmezse bu modul devreye girer ve sorguyu bir LLM'e "hangi ajanlar
cagirilmali?" sorusuyla iletir.

TASARIM
-------
- LLM cagrisi PAHALIDIR: bu yuzden yalniz keyword eslesmesi olmayan sorgularda
  cagrilir. Ayni sorgu tekrar geldiginde cache'ten donulur (LRU + TTL).
- CIKTI YAPILIDIR: LLM'den serbest metin degil, {"agents": [...],
  "is_smalltalk": ...} JSON'u istenir. Ayristirilamayan ya da bilinmeyen ajan
  adi iceren yanit REDDEDILIR ve guvenli varsayilana dusulur (tum ajanlar
  cagirilir); boylece LLM'in yaraticiligi graph'i bozamaz.
- HATA/TIMEOUT durumunda akis KESILMEZ: fallback olarak tum kayitli ajanlar
  secilir. Yani hibrit router calismasa bile sistem bugunku kural motoru gibi
  davranir.
- LLM'ler iki farkli arayuz sunar (LangChain `ainvoke` / `LLMClient.generate`);
  ikisi de desteklenir - orchestrator'in `synthesizer_llm`'i ya da ajan LLM'i
  ayni sekilde gecirilebilir.

Bu modulun `RouterDecision` (mimari v4 §10.4) ile ADI benzer olsa da farkli
bir kavramdir: `RouterDecision` niyet + aciklama tasir, `LlmRouteDecision`
yalnizca hibrit karari (ajan listesi + smalltalk bayragi) tasir.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import OrderedDict
from typing import Iterable

from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)

#: Structured output icin markdown JSON blogunu yakalar.
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

#: Cache key uzunlugunu bagli tutmak icin ust sinir. Cok uzun sorgular
#: cache'te fazla yer kaplamamali; hash tabanli anahtar yerine metnin kisa
#: hali kullaniliyor cunku debug'ta okumak degerli.
_MAX_CACHE_KEY_LEN = 512

DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_CACHE_SIZE = 512
DEFAULT_CACHE_TTL_SECONDS = 3600


class LlmRouteDecision(BaseModel):
    """LLM router'in kararli ciktisi.

    `agents` bos gelebilir - ozellikle `is_smalltalk=True` durumunda uygundur:
    kullanici selamlasiyor, hicbir ajan calistirilmasin, dogrudan synthesizer'a
    gidilsin.
    """

    agents: list[str] = Field(default_factory=list)
    is_smalltalk: bool = False

    @field_validator("agents")
    @classmethod
    def _strip_and_dedupe(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for item in value:
            adi = str(item).strip()
            if adi and adi not in seen:
                seen.append(adi)
        return seen


_ROUTER_SYSTEM_PROMPT = """Sen bir finans asistaninin niyet ayirici modulusun.
Gorevin: kullanicinin sorusunu okuyup hangi uzman ajanlarin calistirilmasi
gerektigine karar vermek. Sadece asagida verilen JSON semasini dondur, baska
hicbir sey yazma.

Kullanabilecegin ajanlar:
- "portfolio": Kullanicinin kendi varliklari, hisseleri, bakiyesi, portfoy
  dagilimi, islem gecmisi hakkinda sorularda calisir.
- "market_research": Sirket haberleri, bilancolar, borsa endeksleri, makro
  ekonomi (faiz, enflasyon, kur), regulasyon, devlet kararlari gibi disaridaki
  piyasa bilgisi gerektiginde calisir.
- "risk_strategy": Kullanicinin portfoyu piyasa/haber gelismelerinden nasil
  etkilenir, riski nasil azaltir, cesitlendirme onerisi gibi kullanicinin
  kendi durumuna dair stratejik yorum gerektiginde calisir. Bu ajan yalniz
  portfolio ya da market_research'ten en az biri ile birlikte anlamli calisir.

Kurallar:
1. Yalniz gercekten gereken ajanlari sec. Emin degilsen o ajani ekleme.
2. Selamlasma, tesekkur, "nasilsin", "sen kimsin", "yardim edebilir misin"
   gibi sohbet sorularinda `is_smalltalk=true` yap ve `agents=[]` don.
3. Ticker sembolleri (THYAO, ASELS, BIST, XU100 vb.) genellikle
   portfolio + market_research demektir.
4. "Portfoyum bu haberden nasil etkilenir?" gibi bagli sorularda ucunu de sec.

Yanit formati (KESINLIKLE bu sema, ekstra alan yok):
{"agents": ["portfolio", "market_research"], "is_smalltalk": false}
"""


def _normalize_cache_key(query: str) -> str:
    """Ayni anlama gelen sorgularin cache'te ayni satiri paylasmasini saglar."""
    return query.strip().lower()[:_MAX_CACHE_KEY_LEN]


class LlmRouter:
    """Kural motoru bos donunce cagrilan LLM tabanli router.

    Kullanim:
        router = LlmRouter(llm=my_llm, known_agents={"portfolio", ...})
        karar = await router.decide("thyao neden dususte")

    LLM olusturulmadan yaratilabilir mi? Hayir: `llm` gerekli. Ancak
    Orchestrator tarafinda `llm_router=None` iken hibrit tamamen atlanir, yani
    LLM baglanmadigi surece bu sinif hic ornek edilmez (bkz. `factory.py`).
    """

    def __init__(
        self,
        llm,
        known_agents: Iterable[str],
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        if llm is None:
            raise ValueError("LlmRouter icin llm gereklidir.")

        self.llm = llm
        self.known_agents: set[str] = set(known_agents)
        self.timeout_seconds = timeout_seconds
        self.cache_size = cache_size
        self.cache_ttl_seconds = cache_ttl_seconds

        # OrderedDict LRU olarak kullaniliyor: her okumada oge sonuna tasiniyor.
        self._cache: OrderedDict[str, tuple[float, LlmRouteDecision]] = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def decide(self, query: str) -> LlmRouteDecision:
        """Sorgu icin LLM'e sor; cache/hata durumunda uygun kararla don.

        Sirasiyla:
          1. Cache hit -> hemen doner.
          2. LLM cagrisi + zaman siniri.
          3. Yanit ayristirma -> gecersizse fallback.
          4. Bilinmeyen ajanlar filtrelenir; kalan liste bos kalirsa fallback
             (ajan `[]` DEGIL, "hepsi") - yanlis LLM ciktisi bir soruyu sessiz
             cevapsiz birakmasin diye.
        """
        anahtar = _normalize_cache_key(query)

        onbellek = self._cache_get(anahtar)
        if onbellek is not None:
            logger.info(
                "llm router cache hit",
                extra={"via": "llm_cache", "agents": onbellek.agents},
            )
            return onbellek

        try:
            metin = await asyncio.wait_for(
                self._invoke_llm(query), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning("llm router zaman asimi", extra={"via": "fallback"})
            return self._fallback()
        except Exception:  # noqa: BLE001 - router hatasi akisi durdurmamali
            logger.exception("llm router beklenmeyen hata", extra={"via": "fallback"})
            return self._fallback()

        karar = self._parse(metin)
        if karar is None:
            return self._fallback()

        temizlenmis = self._filter_unknown_agents(karar)
        # Sadece "hepsi zaten fallback ile ayni" olmadikca cache'e yaz;
        # fallback donmus turleri cache'lersek kalici bir yaniltici deger sabitlemis
        # oluruz. Ancak dogru donmus [] + smalltalk gecerli bir cevaptir, cache'lenir.
        self._cache_set(anahtar, temizlenmis)
        logger.info(
            "llm router karar verdi",
            extra={
                "via": "llm",
                "agents": temizlenmis.agents,
                "is_smalltalk": temizlenmis.is_smalltalk,
            },
        )
        return temizlenmis

    # ------------------------------------------------------------------
    # LLM cagrisi
    # ------------------------------------------------------------------

    async def _invoke_llm(self, query: str) -> str:
        """LLM'i tek turda cagirir; hem LangChain hem LLMClient arayuzunu destekler.

        `synthesizer_llm` LangChain uyumludur (`ainvoke`), `LLMClient` protokolu
        ise `generate(prompt)` sunar (bkz. `app/core/llm.py`). Router iki durumu
        da desteklemek zorunda cunku "aynı model" karari (synthesizer_llm ile
        paylas) hem uretim hem test kolayligi getirir.
        """
        prompt = f"{_ROUTER_SYSTEM_PROMPT}\n\nKullanici sorusu: {query.strip()}"

        if hasattr(self.llm, "ainvoke"):
            response = await self.llm.ainvoke(prompt)
            return str(getattr(response, "content", response) or "")

        if hasattr(self.llm, "generate"):
            return await self.llm.generate(prompt)

        raise RuntimeError("LlmRouter'a verilen LLM ainvoke/generate sunmuyor.")

    # ------------------------------------------------------------------
    # Yanit ayristirma ve dogrulama
    # ------------------------------------------------------------------

    def _parse(self, text: str) -> LlmRouteDecision | None:
        """LLM ciktisindan `LlmRouteDecision` uretir; basarisizsa `None`."""
        if not text or not text.strip():
            logger.warning("llm router bos yanit dondu")
            return None

        json_bloklari = _JSON_BLOCK.search(text)
        if json_bloklari is None:
            logger.warning("llm router yanitinda JSON blogu yok")
            return None

        try:
            veri = json.loads(json_bloklari.group(0))
        except json.JSONDecodeError:
            logger.warning("llm router yaniti JSON olarak ayristirilamadi")
            return None

        try:
            return LlmRouteDecision.model_validate(veri)
        except ValidationError:
            logger.warning("llm router yaniti sema dogrulamasindan gecmedi")
            return None

    def _filter_unknown_agents(self, karar: LlmRouteDecision) -> LlmRouteDecision:
        """LLM olmayan bir ajan adi verirse sessizce ele.

        Bilinen ajan listesi disinda kalanlar cikarilir. Sonuc bos kalirsa VE
        smalltalk isaretlenmediyse fallback'e dusuluyor: LLM "risk_strategy_v2"
        gibi hayali bir ad verdiginde sessizce cevapsiz kalmayalim.
        """
        temiz = [a for a in karar.agents if a in self.known_agents]
        if not temiz and not karar.is_smalltalk:
            return self._fallback()
        return LlmRouteDecision(agents=temiz, is_smalltalk=karar.is_smalltalk)

    def _fallback(self) -> LlmRouteDecision:
        """Guvenli varsayilan: tum kayitli ajanlari sec, smalltalk isaretleme.

        Bu, mevcut kural motorunun "eslesme yoksa hepsini calistir" davranisiyla
        AYNIDIR - hibrit devre disi kalsa sistem regresyona ugramaz.
        """
        return LlmRouteDecision(agents=sorted(self.known_agents), is_smalltalk=False)

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _cache_get(self, key: str) -> LlmRouteDecision | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        timestamp, karar = entry
        if time.monotonic() - timestamp > self.cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        # LRU: son erisilen sona tasinsin.
        self._cache.move_to_end(key)
        return karar

    def _cache_set(self, key: str, karar: LlmRouteDecision) -> None:
        self._cache[key] = (time.monotonic(), karar)
        self._cache.move_to_end(key)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
