"""`app/engine/factory.py` wiring testleri.

Odak: `build_synthesizer_llm()` UC KADEMELI secim yapar (bkz. o fonksiyonun
docstring'i):

    1. `get_streaming_llm`  -> LangChain ChatOpenAI (NIM). Token token akar.
    2. `build_agent_llm`    -> tek seferlik istemci. Sentez YINE LLM ile
                               yapilir, yalnizca akis olmaz.
    3. ikisi de None        -> None. Orchestrator deterministik ozete duser.

⚠️ HER TEST IKI KADEMEYI DE TAKLIT ETMEK ZORUNDA. Yalnizca `build_agent_llm`
   yamalanirsa 1. kademe devrede kalir ve `backend/.env` icinde GERCEK bir
   NVIDIA anahtari tanimlamis her gelistiricide bu testler patlar - kod dogru
   olsa bile. Bu bir kez yasandi: anahtar eklenince uc test birden kirmiziya
   dondu.
"""

from __future__ import annotations

import pytest

from app.engine import factory
from app.engine.factory import build_synthesizer_llm


class _SahteAkitan:
    """1. kademe: LangChain chat modeli gibi `astream()` sunar."""

    async def astream(self, messages, config=None):
        yield None  # pragma: no cover - sadece imza icin


class _SahteTekSeferlik:
    """2. kademe: yalnizca `generate()` sunar (orn. GeminiLLMClient)."""

    async def generate(self, prompt: str) -> str:
        return "x"  # pragma: no cover


@pytest.fixture
def kademeler(monkeypatch):
    """Iki kademeyi de tek yerden kurar - biri unutulamaz.

    Kullanim: `kademeler(akitan=..., tek_seferlik=...)`; verilmeyen kademe
    `None` (yani "kurulamadi") sayilir.
    """

    def _kur(akitan=None, tek_seferlik=None):
        monkeypatch.setattr(factory, "get_streaming_llm", lambda agent: akitan)
        monkeypatch.setattr(factory, "build_agent_llm", lambda agent: tek_seferlik)

    return _kur


def test_akitan_model_varsa_oncelik_onundur(kademeler):
    """1. kademe kurulduysa 2. kademeye HIC bakilmamalidir."""
    akitan = _SahteAkitan()
    kademeler(akitan=akitan, tek_seferlik=_SahteTekSeferlik())

    assert build_synthesizer_llm() is akitan


def test_akitan_yoksa_tek_seferlik_istemciye_duser(kademeler):
    """Ornegin Gemini secildiginde: akis yok ama sentez YINE LLM ile yapilir.

    Bu kademe `None` DONDURMEZ - eskiden oyleydi, bilincli olarak degistirildi
    (bkz. `build_synthesizer_llm` docstring'i, 2. madde).
    """
    tek_seferlik = _SahteTekSeferlik()
    kademeler(akitan=None, tek_seferlik=tek_seferlik)

    assert build_synthesizer_llm() is tek_seferlik


def test_hicbir_llm_kurulamazsa_none_doner(kademeler):
    """3. kademe: anahtar/model tanimli degil -> deterministik ozete duser."""
    kademeler(akitan=None, tek_seferlik=None)

    assert build_synthesizer_llm() is None


def test_akitan_model_patlarsa_tek_seferlige_duser(monkeypatch):
    """`get_streaming_llm` istisna firlatirsa wiring DUSMEMELIDIR.

    Sentez modeli kurulamadi diye tum uygulamanin ayaga kalkmamasi kabul
    edilemez; hata loglanip 2. kademeye gecilir.
    """

    def _patla(agent):
        raise RuntimeError("NIM ucu kurulamadi")

    tek_seferlik = _SahteTekSeferlik()
    monkeypatch.setattr(factory, "get_streaming_llm", _patla)
    monkeypatch.setattr(factory, "build_agent_llm", lambda agent: tek_seferlik)

    assert build_synthesizer_llm() is tek_seferlik
