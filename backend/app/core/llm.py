"""Ajanlarin kullandigi LLM istemci katmani.

⚠️ MODEL KARARI HENUZ VERILMEDI (mimari v4 bolum 16).
    Bu dosyada HICBIR model adi sabit olarak yazili DEGILDIR. Kullanilacak
    model tamamen konfigurasyondan gelir:

        DEFAULT_MODEL=...        # tum ajanlar icin varsayilan
        SYNTHESIZER_MODEL=...    # ajan bazli override (opsiyonel)

    Model adi bos oldugu surece `get_llm_client()` `None` doner ve ajanlar
    LLM'SIZ calisir: MarketResearchAgent kaynaklardan deterministik alinti
    uretir, synthesizer deterministik ozet yazar, guvenlik ajani yalnizca kural
    motoruyla karar verir. Yani sistem model secilmeden de uctan uca calisir.
    Karar verildiginde tek yapilacak `.env` dosyasina model adini yazmaktir;
    KOD DEGISMEZ.

Saglayici olarak Google Gemini SDK'si (`google-genai`) baglidir. Ajanlar
dogrudan `GeminiLLMClient`'a degil `LLMClient` protokolune baglanir; boylece
testlerde gercek API cagrisi yapmadan sahte bir `generate()` enjekte edilebilir
ve saglayici degisirse yalnizca bu dosya degisir.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def generate(self, prompt: str, *, model: str | None = None) -> str: ...


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


def get_llm_client(agent: str) -> LLMClient | None:
    """Ajana ozel LLM istemcisi uretir; anahtar VEYA model tanimli degilse `None`.

    `None` donmesi bir hata DEGILDIR - "LLM'siz calis" demektir. Cagiran taraf
    (`app.engine.factory`) bunu dogal bir durum olarak isler.
    """
    model = settings.model_for(agent)

    if not settings.llm_api_key or not model:
        logger.info(
            "LLM baglanmadi, ajan modelsiz calisacak",
            extra={
                "agent": agent,
                "anahtar_var": bool(settings.llm_api_key),
                "model": model or "-",
            },
        )
        return None

    return GeminiLLMClient(api_key=settings.llm_api_key, default_model=model)
