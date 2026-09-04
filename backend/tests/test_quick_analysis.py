# -*- coding: utf-8 -*-
"""Varlik karti "Polifin AI Analizi" kutusu icin `quick_analysis` testleri.

⚠️ `db` ISARETI KULLANILMAZ - ayni gerekce test_chat_attachments.py'de: bu
testler `get_orchestrator`'i SAHTE bir nesneyle degistirir, gercek
veritabanina hic dokunulmaz. Asil dogrulanan sey: bu yolun `chat_sessions`/
`chat_messages`'a HICBIR SEY YAZMADIGI (bkz. `chat_service.stream_quick_analysis`
docstring'i - varlik kartina tiklamak eskiden kullanicinin GERCEK sohbet
gecmisine bir mesaj yaziyordu).
"""

from __future__ import annotations

import pytest

from app.repositories.in_memory import InMemoryChatRepository
from app.services import chat as chat_service


class _SahteOrchestrator:
    """`stream_request` cagrisinin argumanlarini yakalar."""

    def __init__(self):
        self.son_cagri_kwargs: dict | None = None

    async def stream_request(self, **kwargs):
        self.son_cagri_kwargs = kwargs
        yield {
            "type": "meta",
            "request_id": kwargs.get("request_id", ""),
            "conversation_id": kwargs["thread_id"],
        }
        yield {"type": "status", "stage": "agents", "message": "Piyasa araştırması yapılıyor"}
        yield {"type": "token", "content": "GUMUS "}
        yield {"type": "token", "content": "kısa vadede yatay seyrediyor."}
        yield {"type": "done", "latency_ms": 42.0, "mentioned_assets": []}


@pytest.mark.asyncio
async def test_sorgu_beklenen_formatta_uretilir(monkeypatch):
    sahte = _SahteOrchestrator()
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    _ = [e async for e in chat_service.stream_quick_analysis(user_id=7, symbol="GUMUS")]

    assert sahte.son_cagri_kwargs["query"] == "GUMUS hakkında kısa bir yatırım analizi yap."
    assert sahte.son_cagri_kwargs["user_id"] == 7


@pytest.mark.asyncio
async def test_thread_id_negatif_gercek_oturumla_cakismaz(monkeypatch):
    """`chat_sessions.id` Postgres serial'dir, HER ZAMAN pozitiftir - negatif
    bir `thread_id` bu yuzden hicbir gercek oturumla cakisamaz (bkz.
    `stream_quick_analysis` docstring'i)."""
    sahte = _SahteOrchestrator()
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    _ = [e async for e in chat_service.stream_quick_analysis(user_id=1, symbol="BTC")]

    assert sahte.son_cagri_kwargs["thread_id"] < 0


@pytest.mark.asyncio
async def test_her_cagri_farkli_thread_id_uretir(monkeypatch):
    """Ayni surecte iki ardisik karti acmak AYNI negatif id'yi tekrar
    kullanmamali - LangGraph'in bellek ici checkpointer'i (MemorySaver) o
    zaman iki taleplerin gecmisini birbirine karistirirdi."""
    sahte = _SahteOrchestrator()
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    _ = [e async for e in chat_service.stream_quick_analysis(user_id=1, symbol="BTC")]
    ilk = sahte.son_cagri_kwargs["thread_id"]
    _ = [e async for e in chat_service.stream_quick_analysis(user_id=1, symbol="BTC")]
    ikinci = sahte.son_cagri_kwargs["thread_id"]

    assert ilk != ikinci


@pytest.mark.asyncio
async def test_olaylar_oldugu_gibi_iletilir(monkeypatch):
    sahte = _SahteOrchestrator()
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    olaylar = [e async for e in chat_service.stream_quick_analysis(user_id=1, symbol="GUMUS")]

    tipler = [o["type"] for o in olaylar]
    assert tipler == ["meta", "status", "token", "token", "done"]
    metin = "".join(o["content"] for o in olaylar if o["type"] == "token")
    assert metin == "GUMUS kısa vadede yatay seyrediyor."


@pytest.mark.asyncio
async def test_chat_repository_hic_cagrilmaz(monkeypatch):
    """EN KRITIK TEST: bu yol `chat_sessions`/`chat_messages`'a HICBIR SEY
    yazmamali. `get_chat_repository`'yi hic hazir olmayan bir seye (None)
    baglayip fonksiyonun ona DOKUNMADIGINI dogruluyoruz - dokunsaydi
    `AttributeError` firlardi."""
    sahte = _SahteOrchestrator()
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)
    monkeypatch.setattr(
        chat_service,
        "get_chat_repository",
        lambda: (_ for _ in ()).throw(
            AssertionError("stream_quick_analysis get_chat_repository'yi COGIRMAMALI")
        ),
    )

    olaylar = [e async for e in chat_service.stream_quick_analysis(user_id=1, symbol="GUMUS")]

    assert olaylar[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_gercek_bellek_ici_repo_bos_kalir(monkeypatch):
    """Yukaridaki testin GORSEL kaniti: gercek (bellek ici) bir repo
    baglansa bile hicbir oturum/mesaj olusmaz."""
    repo = InMemoryChatRepository()
    monkeypatch.setattr(chat_service, "get_chat_repository", lambda: repo)
    sahte = _SahteOrchestrator()
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    await repo.create_session(user_id=1, title="Gercek sohbet")
    onceki_oturum_sayisi = len(await repo.list_sessions(user_id=1))

    _ = [e async for e in chat_service.stream_quick_analysis(user_id=1, symbol="GUMUS")]

    assert len(await repo.list_sessions(user_id=1)) == onceki_oturum_sayisi
