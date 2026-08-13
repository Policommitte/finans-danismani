"""MCP tool sunucusu - sistemdeki TEK veri dokunma noktasi (NFR-04).

Mimari v4 bolum 6: tek bir MCP sunucusu vardir, ayrim tool ADI ile yapilir:
`user_*`, `portfolio_*`, `market_*`, `rag_*`. Ayri sunucu nesneleri yalnizca
kayit defteri olarak kullanilir; ajanlar tool adiyla calisir.

UC DEGISMEZ KURAL
-----------------
1. `user_id` TOOL SEMASINDA YOKTUR. LLM'in gordugu parametreler arasinda
   kimlik bulunmaz; kimlik `app.mcp.context` contextvar'indan alinir. Boylece
   "5 numarali kullanicinin portfoyunu getir" seklinde bir prompt injection
   baska birinin verisine ulasamaz.
2. Tum tool'lar AYNI zarfi doner: ``{"ok": bool, "data": dict, "error": str|None}``.
   Zarf `MCPClient.call_tool` icinde acilir; ajanlar `data` icerigini gorur,
   basarisiz cagri ise `MCPToolExecutionError`'a cevrilir (bkz. client.py).
3. Parasal degerler TRY'ye normalize doner ve alan adlari `*_try` ile biter.

Tool'lar is mantigi TASIMAZ; repository katmanini cagirir. Hesaplar DB
view'larinda tektir (mimari v4 bolum 9.2).
"""

from __future__ import annotations

import logging
from typing import Any

from app.mcp.client import MCPServer
from app.mcp.context import require_user_id
from app.repositories.deps import (
    get_market_repository,
    get_portfolio_repository,
    get_rag_repository,
    get_user_repository,
)

logger = logging.getLogger(__name__)

#: Tool gruplarinin kayitli oldugu sunucu adlari. Tek MCP sunucusu kullanilir;
#: bu adlar yalnizca yonlendirme icindir (bkz. modul docstring'i).
CORE_SERVER_NAME = "core"
RAG_SERVER_NAME = "rag"
MARKET_SERVER_NAME = "market"

#: `market_get_history` LLM'e ham zaman serisi DONDURMEZ (baglam sismesin).
#: Ozet disinda en fazla bu kadar ornek nokta gonderilir.
HISTORY_SAMPLE_POINTS = 8


def ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Basarili tool yaniti (ortak zarf)."""
    return {"ok": True, "data": data or {}, "error": None}


def fail(message: str) -> dict[str, Any]:
    """Basarisiz tool yaniti (ortak zarf).

    Istisna FIRLATILMAZ: "veri bulunamadi" bir cokme degil, gecerli bir
    sonuctur. Ajan bunu `tool_error` olarak raporlar ve akis devam eder.
    """
    return {"ok": False, "data": {}, "error": message}


# ---------------------------------------------------------------------------
# user_* grubu
# ---------------------------------------------------------------------------


async def user_get_profile() -> dict[str, Any]:
    """Kullanicinin risk profili ve gelir bilgisi. Parametre ALMAZ."""
    user_id = require_user_id()
    user = await get_user_repository().get_by_id(user_id)
    if user is None:
        return fail("Kullanici bulunamadi.")

    return ok(
        {
            "ad": f"{user['first_name']} {user['last_name']}".strip(),
            "risk_tolerance": user.get("risk_tolerance"),
            "monthly_income_try": _f(user.get("monthly_income")),
        }
    )


# ---------------------------------------------------------------------------
# portfolio_* grubu
# ---------------------------------------------------------------------------


async def portfolio_get_summary() -> dict[str, Any]:
    """Portfoy ozeti: toplam deger, maliyet, kar/zarar. Parametre ALMAZ."""
    user_id = require_user_id()
    summary = await get_portfolio_repository().get_summary(user_id)
    if summary is None:
        return fail("Kullanicinin portfoyunde varlik bulunmuyor.")

    return ok(
        {
            "holding_count": summary["holding_count"],
            "total_value_try": _f(summary["total_value_try"]),
            "total_cost_try": _f(summary["total_cost_try"]),
            "total_pnl_try": _f(summary["total_pnl_try"]),
            "total_pnl_pct": _f(summary["total_pnl_pct"]),
        }
    )


async def portfolio_get_holdings() -> dict[str, Any]:
    """Portfoydeki varliklar (deger sirali). Parametre ALMAZ."""
    user_id = require_user_id()
    holdings = await get_portfolio_repository().get_holdings(user_id)
    if not holdings:
        return fail("Kullanicinin portfoyunde varlik bulunmuyor.")

    return ok(
        {
            "holdings": [
                {
                    "symbol": h["symbol"],
                    "ad": h["asset_name"],
                    "asset_class": h["asset_class"],
                    "quantity": _f(h["quantity"]),
                    "average_buy_price": _f(h["average_buy_price"]),
                    "current_price": _f(h["current_price"]),
                    "market_value_try": _f(h["market_value_try"]),
                    "pnl_try": _f(h["pnl_try"]),
                    "pnl_pct": _f(h["pnl_pct"]),
                }
                for h in holdings
            ]
        }
    )


async def portfolio_get_allocation() -> dict[str, Any]:
    """Varlik sinifi bazinda dagilim (yuzde). Parametre ALMAZ."""
    user_id = require_user_id()
    rows = await get_portfolio_repository().get_allocation(user_id)
    if not rows:
        return fail("Dagilim hesaplanacak varlik bulunmuyor.")

    return ok(
        {
            "allocation": [
                {
                    "asset_class": r["asset_class"],
                    "class_value_try": _f(r["class_value"]),
                    "class_pct": _f(r["class_pct"]),
                }
                for r in rows
            ]
        }
    )


async def portfolio_get_transactions(limit: int = 20) -> dict[str, Any]:
    """Son islemler (en yeniden eskiye).

    Args:
        limit: Kac islem donsun (1-100 araligina kirpilir).
    """
    user_id = require_user_id()
    limit = max(1, min(int(limit or 20), 100))
    rows = await get_portfolio_repository().get_transactions(user_id, limit=limit)
    return ok(
        {"transactions": [{**r, "transaction_date": str(r["transaction_date"])} for r in rows]}
    )


# ---------------------------------------------------------------------------
# market_* grubu
# ---------------------------------------------------------------------------


async def market_get_quote(symbol: str) -> dict[str, Any]:
    """Bir varligin guncel fiyati.

    Args:
        symbol: Varlik kodu (orn. "THYAO", "BTC").
    """
    quote = await get_market_repository().get_quote(symbol)
    if quote is None:
        return fail(f"'{symbol}' icin fiyat verisi bulunamadi.")

    return ok(
        {
            "symbol": quote["symbol"],
            "ad": quote.get("name"),
            "price": _f(quote["price"]),
            "currency": quote.get("currency"),
            "daily_change_pct": _f(quote.get("daily_change_pct")),
            "weekly_change_pct": _f(quote.get("weekly_change_pct")),
            "ts": str(quote.get("ts")),
        }
    )


async def market_get_history(symbol: str, days: int = 30) -> dict[str, Any]:
    """Fiyat gecmisinin OZETI (ham seri degil).

    LLM baglaminin sismemesi icin (mimari v4 bolum 6.4) yuzlerce satir yerine
    ozet istatistikler ve en fazla birkac ornek nokta doner. Dashboard grafigi
    ham seriyi REST ucundan (`/api/market/history`) alir.

    Args:
        symbol: Varlik kodu.
        days: Kac gunluk gecmis (1-365).
    """
    days = max(1, min(int(days or 30), 365))
    series = await get_market_repository().get_history(symbol, days=days)
    if not series:
        return fail(f"'{symbol}' icin fiyat gecmisi bulunamadi.")

    prices = [_f(p["price"]) for p in series]
    ilk, son = prices[0], prices[-1]
    ortalama = sum(prices) / len(prices)
    # Oynaklik: ortalamaya gore standart sapmanin yuzdesi. Risk ajani bu
    # sayiyi kullanir; ayni hesabi iki yerde yapmamak icin burada uretilir.
    varyans = sum((p - ortalama) ** 2 for p in prices) / len(prices)
    oynaklik = (varyans**0.5) / ortalama * 100 if ortalama else 0.0

    adim = max(1, len(series) // HISTORY_SAMPLE_POINTS)
    ornekler = [
        {"ts": str(series[i]["ts"]), "price": prices[i]} for i in range(0, len(series), adim)
    ]

    return ok(
        {
            "symbol": symbol.upper(),
            "days": days,
            "point_count": len(series),
            "first_price": ilk,
            "last_price": son,
            "min_price": min(prices),
            "max_price": max(prices),
            "change_pct": round((son - ilk) / ilk * 100, 2) if ilk else None,
            "volatility_pct": round(oynaklik, 2),
            "samples": ornekler[:HISTORY_SAMPLE_POINTS],
        }
    )


async def market_get_kap_disclosures(symbol: str, since: str | None = None) -> dict[str, Any]:
    """Sirkete ait duyurular (KAP bildirimleri).

    Ayri bir KAP entegrasyonu YOKTUR: duyurular RAG indeksinde `tip='duyuru'`
    olarak durur ve buradan okunur. Gercek KAP API'si baglandiginda yalnizca
    bu fonksiyon degisir.

    Args:
        symbol: Sirket/varlik kodu.
        since: "YYYY-MM-DD" - bu tarihten yeni bildirimler.
    """
    rows = await get_rag_repository().search(query=symbol, top_k=10, sirket=symbol, tip="duyuru")
    if since:
        rows = [r for r in rows if str(r.get("tarih") or "") >= since]

    return ok(
        {
            "symbol": symbol.upper(),
            "disclosures": [
                {
                    "disclosure_id": str(r.get("doc_id") or r.get("chunk_id")),
                    "title": r.get("baslik"),
                    "summary": (r.get("content") or "")[:300],
                    "date": str(r.get("tarih") or ""),
                }
                for r in rows
            ],
        }
    )


# ---------------------------------------------------------------------------
# rag_* grubu
# ---------------------------------------------------------------------------


async def rag_search(
    query: str,
    top_k: int = 5,
    sirket: str | None = None,
    tip: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Haber/bilanco/rapor indeksinde arama.

    Sonuc YAPILANDIRILMIS doner (duz metin degil): kaynak metadata'si MCP
    sinirinda kaybolursa FR-RAG-04 izlenebilirligi karsilanamaz.

    ⚠️ Embedding modeli secilene kadar arama yalnizca BM25 (tam eslesme)
    ayagiyla calisir; hibrit arama (dense + BM25 -> RRF) model kararindan
    sonra acilir. Bkz. `app/repositories/sql.py::SqlRagRepository`.

    Args:
        query: Dogal dilde arama sorgusu.
        top_k: Kac chunk donsun (1-20).
        sirket: Sirket/sembol filtresi (orn. "THYAO").
        tip: haber | bilanco | analist_raporu | duyuru
        filters: Geriye donuk uyum - {"symbol": ..., "tip": ...} da kabul edilir.
    """
    filters = filters or {}
    sirket = sirket or filters.get("sirket") or filters.get("symbol")
    tip = tip or filters.get("tip")
    top_k = max(1, min(int(top_k or 5), 20))

    rows = await get_rag_repository().search(query=query, top_k=top_k, sirket=sirket, tip=tip)

    return ok({"query": query, "chunks": [_chunk_payload(r) for r in rows]})


def _chunk_payload(row: dict) -> dict[str, Any]:
    """RAG satirini tool ciktisina cevirir.

    Hem yeni alan adlari (`baslik`/`tarih`/`tip`) hem de MarketResearchAgent'in
    kullandigi eski adlar (`title`/`date`/`text`/`metadata`) birlikte doner;
    boylece ajan sozlesmesi kirilmaz.
    """
    baslik = row.get("baslik")
    tarih = str(row.get("tarih") or "")
    sirket = row.get("sirket")
    # Ajanlar sembolle calisir; dokumanda unvan yazili olabilir.
    sembol = row.get("symbol") or sirket

    return {
        "chunk_id": str(row.get("chunk_id") or row.get("doc_id") or ""),
        "doc_id": row.get("doc_id"),
        "baslik": baslik,
        "sirket": sirket,
        "symbol": sembol,
        "tarih": tarih,
        "tip": row.get("tip"),
        "content": row.get("content"),
        "score": _f(row.get("score")),
        # --- eski adlar (MarketResearchAgent) ---
        "title": baslik,
        "text": row.get("content"),
        "source": baslik,
        "date": tarih,
        "metadata": {"symbol": sembol, "topic": row.get("tip")},
    }


# ---------------------------------------------------------------------------
# Kayit
# ---------------------------------------------------------------------------

#: Tool adi -> handler. Yeni tool eklemek icin buraya bir satir ekleyip
#: mimari v4 bolum 6.2'deki katalogu guncellemek yeterlidir.
TOOL_GROUPS: dict[str, dict[str, Any]] = {
    CORE_SERVER_NAME: {
        "user_get_profile": user_get_profile,
        "portfolio_get_summary": portfolio_get_summary,
        "portfolio_get_holdings": portfolio_get_holdings,
        "portfolio_get_allocation": portfolio_get_allocation,
        "portfolio_get_transactions": portfolio_get_transactions,
    },
    MARKET_SERVER_NAME: {
        "market_get_quote": market_get_quote,
        "market_get_history": market_get_history,
        "market_get_kap_disclosures": market_get_kap_disclosures,
    },
    RAG_SERVER_NAME: {
        "rag_search": rag_search,
    },
}


def build_servers() -> list[MCPServer]:
    """Kayitli tool gruplarini MCPServer nesnelerine cevirir."""
    servers: list[MCPServer] = []
    for server_name, tools in TOOL_GROUPS.items():
        server = MCPServer(name=server_name)
        for tool_name, handler in tools.items():
            server.register_tool(tool_name, handler)
        servers.append(server)
    return servers


def _f(value: Any) -> float | None:
    """Decimal/None guvenli float donusumu.

    psycopg NUMERIC kolonlari `Decimal` dondurur; JSON'a cevrilmeden once
    float'a alinir, aksi halde SSE/REST serilestirmesi patlar.
    """
    if value is None:
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None
