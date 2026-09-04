# -*- coding: utf-8 -*-
"""MarketResearchAgent coklu varlik testleri (resolve_symbols entegrasyonu).

⚠️ `db` ISARETI KULLANILMAZ - `test_market_research_agent.py`'nin aksine
GERCEK MCP tool'larini (`build_servers()`, PostgreSQL) degil, TAMAMEN
sahte/bellek ici bir "market" sunucusu kullanir. Amac saf: `_execute`'un
YENI coklu-sembol dalinin (`_ek_sembolleri_getir`) dogru kablolandigini
dogrulamak, gercek veri katmanini degil.

CANLI BILDIRILEN HATA: "NVIDIA ve Apple hisseleri ne durumda" sorusuna
yalnizca BIRINCIL varligin (market_data.symbol - TEK alan) karti
donuyordu, ikinci varlik sessizce yok sayiliyordu.
"""

from __future__ import annotations

import pytest

from app.agents.market_research import MarketResearchAgent
from app.mcp.client import MCPClient, MCPServer
from app.mcp.server import fail, ok
from app.orchestration.models import AgentState

#: Gercek `market_list_symbols` ciktisiyla ayni sekil - kucuk bir katalog.
KATALOG = [
    {"symbol": "ASELS", "ad": "Aselsan", "asset_class": "STOCK"},
    {"symbol": "SASA", "ad": "Sasa Polyester", "asset_class": "STOCK"},
    {"symbol": "THYAO", "ad": "Türk Hava Yolları", "asset_class": "STOCK"},
]

#: Sembol -> sahte kotasyon. Testler kasitli olarak FARKLI fiyat/yon
#: kullanir ki "ayni veri iki kez donuyor" gibi bir hata gozden kacmasin.
KOTASYONLAR = {
    "ASELS": {"price": 390.25, "currency": "TRY", "daily_change_pct": 1.5},
    "SASA": {"price": 4.12, "currency": "TRY", "daily_change_pct": -2.3},
    "THYAO": {"price": 302.25, "currency": "TRY", "daily_change_pct": 0.4},
}


def _sahte_market_sunucusu(cagrilan_semboller: list[str] | None = None) -> MCPServer:
    sunucu = MCPServer("market")

    async def market_list_symbols() -> dict:
        return ok({"symbols": KATALOG})

    async def market_get_quote(symbol: str) -> dict:
        if cagrilan_semboller is not None:
            cagrilan_semboller.append(symbol)
        kotasyon = KOTASYONLAR.get(symbol)
        if kotasyon is None:
            return fail(f"'{symbol}' icin fiyat verisi bulunamadi.")
        return ok(
            {
                "symbol": symbol,
                "price": kotasyon["price"],
                "currency": kotasyon["currency"],
                "daily_change_pct": kotasyon["daily_change_pct"],
                "ts": "2026-09-03T10:00:00",
            }
        )

    sunucu.register_tool("market_list_symbols", market_list_symbols)
    sunucu.register_tool("market_get_quote", market_get_quote)
    return sunucu


def _ajan(cagrilan_semboller: list[str] | None = None) -> MarketResearchAgent:
    client = MCPClient({"market": _sahte_market_sunucusu(cagrilan_semboller)})
    return MarketResearchAgent(mcp_client=client, llm=None, timeout_seconds=5)


def _state(sorgu: str, sembol: str) -> AgentState:
    """`mode`/`symbol`'u ACIKCA verir - regex/NLP siniflandirmasina bagimli
    olmadan yalnizca `_execute`'un coklu-sembol dalini test eder."""
    return AgentState(
        user_query=sorgu,
        user_id=1,
        thread_id=1,
        agent_tasks={"market_research": {"mode": "live", "symbol": sembol}},
        requested_agents=["market_research"],
    )


@pytest.mark.asyncio
async def test_coklu_varlik_sorusunda_ikinci_sembol_de_market_datada_gorunur():
    ajan = _ajan()

    sonuc = await ajan._execute(_state("ASELS ve SASA hisseleri ne durumda", "ASELS"))

    ek = sonuc["market_data"]["additional_symbols"]
    assert [e["symbol"] for e in ek] == ["SASA"]
    assert ek[0]["price"] == 4.12


@pytest.mark.asyncio
async def test_ikinci_sembolun_ozeti_sentez_metnine_girer():
    """Kart gorunup de cevap metni ikinci varliktan HIC bahsetmemesi -
    kullaniciya kart ile metin arasinda tutarsizlik olarak gorunurdu."""
    ajan = _ajan()

    sonuc = await ajan._execute(_state("ASELS ve SASA hisseleri ne durumda", "ASELS"))

    assert "SASA" in sonuc["market_data"]["summary"]
    assert "4.12" in sonuc["market_data"]["summary"] or "4,12" in sonuc["market_data"]["summary"]


@pytest.mark.asyncio
async def test_tek_varlikli_soruda_additional_symbols_bos_kalir():
    """Eski (tek sembol) davranis DEGISMEMELI - regresyon korumasi."""
    ajan = _ajan()

    sonuc = await ajan._execute(_state("ASELS hissesi ne durumda", "ASELS"))

    assert sonuc["market_data"]["additional_symbols"] == []


@pytest.mark.asyncio
async def test_uc_varlik_sorulursa_ucu_de_gelir():
    ajan = _ajan()

    sonuc = await ajan._execute(_state("ASELS SASA ve THYAO nasil gidiyor", "ASELS"))

    ek = sonuc["market_data"]["additional_symbols"]
    assert {e["symbol"] for e in ek} == {"SASA", "THYAO"}


@pytest.mark.asyncio
async def test_ek_sembolun_fiyati_bulunamazsa_sessizce_atlanir():
    """MCP tool'u basarisiz olursa (sembol yok, gecici hata) o sembol
    SESSIZCE atlanir - birincil varligin cevabini BOZMAMALI."""
    ajan = _ajan()

    sonuc = await ajan._execute(_state("ASELS ve OLMAYANSEMBOL nasil", "ASELS"))

    # "OLMAYANSEMBOL" katalogda yok, resolve_symbols zaten bulamaz - test
    # asil onemli olani dogruluyor: katalogda olmayan bir kelime yuzunden
    # `_execute` PATLAMAZ, birincil varlik normal doner.
    assert sonuc["market_data"]["symbol"] == "ASELS"
    assert sonuc["market_data"]["additional_symbols"] == []


@pytest.mark.asyncio
async def test_ek_semboller_icin_yalnizca_fiyat_cekilir_tam_analiz_degil():
    """`_ek_sembolleri_getir` yalnizca `market_get_quote` cagirmali -
    `market_get_kap_disclosures` gibi ek tool'lar TETIKLENMEMELI (coklu
    varlikta her biri icin tam analiz cekmek gecikmeyi katlardi)."""
    cagrilan: list[str] = []
    ajan = _ajan(cagrilan)

    await ajan._execute(_state("ASELS ve SASA hisseleri ne durumda", "ASELS"))

    # Birincil (ASELS, `_run_live` uzerinden) + ikincil (SASA, `_ek_sembolleri_getir`
    # uzerinden) - ikisi de SADECE market_get_quote cagirir, sunucumuzda
    # baska tool kayitli bile degil (kayitli olmayani cagirsaydi patlardi).
    assert cagrilan == ["ASELS", "SASA"]
