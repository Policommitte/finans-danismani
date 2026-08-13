"""Agent'larin RAG yanitlarini gruplamak icin kullandigi LLM istemci katmani.

Saglayici olarak Google Gemini secildi (google-genai SDK). Agent'lar dogrudan
GeminiLLMClient'a baglanmaz; LLMClient protokolune baglanir, boylece testlerde
gercek API cagrisi yapmadan sahte bir generate() implementasyonu enjekte
edilebilir.
"""

from __future__ import annotations

from typing import Protocol

from app.config import settings

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


class LLMClient(Protocol):
    async def generate(self, prompt: str, *, model: str | None = None) -> str: ...


class GeminiLLMClient:
    """google-genai SDK uzerinden Gemini'ye baglanan ince bir sarmalayici."""

    def __init__(self, api_key: str, default_model: str = DEFAULT_GEMINI_MODEL) -> None:
        from google import genai  # gecikmeli import: paket sadece gercekten kullanildiginda gerekli

        self._client = genai.Client(api_key=api_key)
        self._default_model = default_model

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        response = await self._client.aio.models.generate_content(
            model=model or self._default_model,
            contents=prompt,
        )
        return response.text or ""


def get_llm_client(agent: str) -> LLMClient:
    """settings uzerinden agent'a ozel model adiyla bir GeminiLLMClient olusturur."""
    if not settings.llm_api_key:
        raise RuntimeError(
            "LLM_API_KEY tanimli degil. .env dosyasina Gemini API anahtarini ekleyin."
        )
    return GeminiLLMClient(
        api_key=settings.llm_api_key,
        default_model=settings.model_for(agent) or DEFAULT_GEMINI_MODEL,
    )
