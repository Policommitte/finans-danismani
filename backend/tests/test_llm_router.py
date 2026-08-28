"""LlmRouter testleri (app/engine/llm_router.py).

Hibrit router'in LLM ayaginin uc davranisi burada dogrulanir:
  * Yapili cikti ayristirma: gecerli JSON, markdown fence, kirli metin, hatali sema.
  * Cache: hit, TTL bitisi, LRU dislama.
  * Hata izolasyonu: timeout / LLM istisnasi -> sistem cokmez, fallback doner.
"""

import asyncio

import pytest

from app.engine import llm_router as router_module
from app.engine.llm_router import LlmRouteDecision, LlmRouter

KAYITLI_AJANLAR = {"portfolio", "market_research", "risk_strategy"}


# ---------------------------------------------------------------------------
# Sahte LLM'ler
# ---------------------------------------------------------------------------


class SahteAinvokeLLM:
    """LangChain uyumlu (`ainvoke`) sahte LLM.

    `messages` sirali doner: birden fazla decide cagrisi test etmek icin.
    """

    def __init__(self, messages):
        self._messages = list(messages)
        self.cagri_sayisi = 0

    async def ainvoke(self, prompt):
        self.cagri_sayisi += 1
        if not self._messages:
            raise RuntimeError("SahteAinvokeLLM: yeterli mesaj yok")
        icerik = self._messages.pop(0)

        class _Msg:
            def __init__(self, content):
                self.content = content

        return _Msg(icerik)


class SahteGenerateLLM:
    """LLMClient protokolu (`generate`) uyumlu sahte LLM."""

    def __init__(self, messages):
        self._messages = list(messages)
        self.cagri_sayisi = 0

    async def generate(self, prompt, *, model=None):
        self.cagri_sayisi += 1
        if not self._messages:
            raise RuntimeError("SahteGenerateLLM: yeterli mesaj yok")
        return self._messages.pop(0)


class YavasLLM:
    async def ainvoke(self, prompt):
        await asyncio.sleep(5)
        return type("M", (), {"content": ""})()


class PatlayanLLM:
    async def ainvoke(self, prompt):
        raise RuntimeError("model erisilemez")


def _router(llm, **kwargs) -> LlmRouter:
    return LlmRouter(
        llm=llm,
        known_agents=KAYITLI_AJANLAR,
        timeout_seconds=kwargs.pop("timeout_seconds", 1.0),
        cache_size=kwargs.pop("cache_size", 32),
        cache_ttl_seconds=kwargs.pop("cache_ttl_seconds", 60),
    )


# ---------------------------------------------------------------------------
# Kurulum
# ---------------------------------------------------------------------------


def test_llm_none_ile_router_yaratilamaz():
    """LLM yoksa router'i hic yaratmayalim; wiring bunu factory'de yakalar."""
    with pytest.raises(ValueError):
        LlmRouter(llm=None, known_agents=KAYITLI_AJANLAR)


# ---------------------------------------------------------------------------
# Yapili cikti ayristirma
# ---------------------------------------------------------------------------


async def test_gecerli_json_yaniti_ayristirilir():
    llm = SahteAinvokeLLM(['{"agents": ["portfolio"], "is_smalltalk": false}'])

    karar = await _router(llm).decide("portfoyum nasil")

    assert karar == LlmRouteDecision(agents=["portfolio"], is_smalltalk=False)
    assert llm.cagri_sayisi == 1


async def test_markdown_fence_li_yanit_ayristirilir():
    """LLM ```json ...``` uretebilir; regex ilk `{...}` blogunu bulmali."""
    metin = 'Iste karar:\n```json\n{"agents": ["market_research"], "is_smalltalk": false}\n```'
    llm = SahteAinvokeLLM([metin])

    karar = await _router(llm).decide("piyasa haberleri")

    assert karar.agents == ["market_research"]
    assert karar.is_smalltalk is False


async def test_bos_yanit_fallback_e_duser():
    llm = SahteAinvokeLLM([""])

    karar = await _router(llm).decide("bilinmeyen")

    assert set(karar.agents) == KAYITLI_AJANLAR
    assert karar.is_smalltalk is False


async def test_gecersiz_json_fallback_e_duser():
    llm = SahteAinvokeLLM(["bu metin JSON degil"])

    karar = await _router(llm).decide("bilinmeyen")

    assert set(karar.agents) == KAYITLI_AJANLAR


async def test_yanlis_sema_fallback_e_duser():
    llm = SahteAinvokeLLM(['{"unrelated": true}'])

    karar = await _router(llm).decide("bilinmeyen")

    assert set(karar.agents) == KAYITLI_AJANLAR


# ---------------------------------------------------------------------------
# Ajan filtreleme
# ---------------------------------------------------------------------------


async def test_bilinmeyen_ajan_adi_sessizce_filtrelenir():
    """LLM 'risk_v2' gibi hayali bir ad verirse listeden dusurulur."""
    llm = SahteAinvokeLLM(
        ['{"agents": ["portfolio", "risk_v2"], "is_smalltalk": false}']
    )

    karar = await _router(llm).decide("portfoyum")

    assert karar.agents == ["portfolio"]


async def test_tum_ajanlar_bilinmiyorsa_fallback_e_duser():
    """LLM sadece hayali ad verirse sorguyu cevapsiz birakma - hepsini cagir."""
    llm = SahteAinvokeLLM(['{"agents": ["risk_v2"], "is_smalltalk": false}'])

    karar = await _router(llm).decide("test")

    assert set(karar.agents) == KAYITLI_AJANLAR


async def test_smalltalk_karari_ajan_listesini_bos_birakabilir():
    """Selamlasma icin agents=[] gecerli bir cevaptir, fallback'e dusurulmez."""
    llm = SahteAinvokeLLM(['{"agents": [], "is_smalltalk": true}'])

    karar = await _router(llm).decide("merhaba")

    assert karar.agents == []
    assert karar.is_smalltalk is True


async def test_ajan_listesi_tekrar_ve_bosluklardan_temizlenir():
    llm = SahteAinvokeLLM(
        ['{"agents": [" portfolio ", "portfolio", "market_research"], '
         '"is_smalltalk": false}']
    )

    karar = await _router(llm).decide("test")

    assert karar.agents == ["portfolio", "market_research"]


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


async def test_cache_ayni_sorguda_llm_i_atlar():
    llm = SahteAinvokeLLM(['{"agents": ["portfolio"], "is_smalltalk": false}'])
    router = _router(llm)

    ilk = await router.decide("Portfoyum nasil?")
    ikinci = await router.decide("portfoyum nasil?")  # sadece kucuk harf farki

    assert ilk == ikinci
    assert llm.cagri_sayisi == 1


async def test_cache_ttl_dolunca_llm_tekrar_cagrilir(monkeypatch):
    """TTL bitmisse cache miss olur; sonsuz saklama olmasin."""
    llm = SahteAinvokeLLM(
        [
            '{"agents": ["portfolio"], "is_smalltalk": false}',
            '{"agents": ["market_research"], "is_smalltalk": false}',
        ]
    )
    saat = {"deger": 1000.0}

    def sahte_monotonic():
        return saat["deger"]

    monkeypatch.setattr(router_module.time, "monotonic", sahte_monotonic)
    router = _router(llm, cache_ttl_seconds=10)

    await router.decide("kisa sorgu")
    saat["deger"] += 100  # TTL cok gecti

    ikinci = await router.decide("kisa sorgu")

    assert llm.cagri_sayisi == 2
    assert ikinci.agents == ["market_research"]


async def test_cache_kapasitesi_asilinca_en_eskiyi_atar():
    """LRU: cache dolunca EN ESKI erisim atilir, en yeni kalir."""
    llm = SahteAinvokeLLM(
        [
            '{"agents": ["portfolio"], "is_smalltalk": false}',
            '{"agents": ["market_research"], "is_smalltalk": false}',
            '{"agents": ["risk_strategy"], "is_smalltalk": false}',
            '{"agents": ["portfolio", "market_research"], "is_smalltalk": false}',
        ]
    )
    router = _router(llm, cache_size=2)

    await router.decide("bir")
    await router.decide("iki")
    await router.decide("uc")  # "bir"'i disari atmali

    # "bir" cache'ten dusmus olmali -> LLM'e tekrar gider.
    await router.decide("bir")

    assert llm.cagri_sayisi == 4


# ---------------------------------------------------------------------------
# Hata izolasyonu
# ---------------------------------------------------------------------------


async def test_timeout_fallback_e_duser():
    router = _router(YavasLLM(), timeout_seconds=0.05)

    karar = await router.decide("test")

    assert set(karar.agents) == KAYITLI_AJANLAR


async def test_llm_hatasinda_fallback_e_duser():
    router = _router(PatlayanLLM())

    karar = await router.decide("test")

    assert set(karar.agents) == KAYITLI_AJANLAR


# ---------------------------------------------------------------------------
# Farkli LLM arayuzleri
# ---------------------------------------------------------------------------


async def test_generate_arayuzu_de_desteklenir():
    """LLMClient protokolu (`generate`) icin de calisir - Gemini istemcisi bu tipte."""
    llm = SahteGenerateLLM(
        ['{"agents": ["risk_strategy"], "is_smalltalk": false}']
    )

    karar = await _router(llm).decide("riskimi degerlendir")

    assert karar.agents == ["risk_strategy"]
    assert llm.cagri_sayisi == 1


async def test_ainvoke_veya_generate_yoksa_fallback_e_duser():
    """LLM iki arayuzu de sunmuyorsa runtime error -> fallback."""

    class BosLLM:
        pass

    router = _router(BosLLM())

    karar = await router.decide("test")

    assert set(karar.agents) == KAYITLI_AJANLAR
