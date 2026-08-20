"""Bellek ici veri - DATABASE_URL tanimli degilken kullanilir.

Bu veri kumesi `db/v5_schema_and_data.sql` icindeki dummy data'nin bir
ALT KUMESIDIR ve ayni sayilari uretir (ornegin 1 numarali portfoyun toplam
degeri her iki yolda da ayni cikar). Boylece DB'siz calisan bir gelistirici ile
DB'li calisan bir gelistirici ayni ekrani gorur; frontend sozlesmesi ikisinde
de aynidir.

Hesap zinciri de SQL'deki view zinciriyle AYNIDIR:
    holdings (deger + FX) -> allocation -> summary
Hesabi iki farkli yerde yazmamak icin `_holdings_valued()` tek kaynaktir.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# --- users ------------------------------------------------------------------
# password_hash degerleri SQL seed'inden birebir alinmistir; hepsinin sifresi
# "demo1234" (bcrypt, cost 10). Gercek bir sir degildir - dummy data.
_USERS: list[dict] = [
    {
        "id": 1,
        "first_name": "Mehmet",
        "last_name": "Yilmaz",
        "email": "mehmet@example.com",
        "password_hash": "$2b$10$IR711tECQxZE.JMPUjgWs.y9LzkCYTDDqbejiRAB7YkEYAvSdDIXW",
        "risk_tolerance": "HIGH",
        "monthly_income": 150000.0,
    },
    {
        "id": 2,
        "first_name": "Ayse",
        "last_name": "Kaya",
        "email": "ayse@example.com",
        "password_hash": "$2b$10$Yb8T7yJiAWQQD71v45o/EOpGCQVCWj9sAbJmjl5R6HKa39lyKW36S",
        "risk_tolerance": "LOW",
        "monthly_income": 75000.0,
    },
]

# --- assets -----------------------------------------------------------------
#: Varliklarin BASLANGIC degerleri. `_ASSETS` bunun kopyasidir; fiyat gorevi
#: (`apply_price_updates`) kopyayi gunceller, tohum veri degismez - boylece
#: `reset_data()` her zaman bilinen bir duruma donebilir.
_SEED_ASSETS: list[dict] = [
    {
        "id": 1,
        "symbol": "THYAO",
        "name": "Turk Hava Yollari",
        "asset_class": "STOCK",
        "currency": "TRY",
        "current_price": 315.50,
        "daily_change_pct": 1.2,
        "weekly_change_pct": 4.5,
        "yearly_change_pct": 65.2,
        "sim_volatility": 0.0200,
    },
    {
        "id": 2,
        "symbol": "GARAN",
        "name": "Garanti BBVA",
        "asset_class": "STOCK",
        "currency": "TRY",
        "current_price": 125.40,
        "daily_change_pct": -0.5,
        "weekly_change_pct": 2.1,
        "yearly_change_pct": 45.8,
        "sim_volatility": 0.0200,
    },
    {
        "id": 4,
        "symbol": "SASA",
        "name": "Sasa Polyester",
        "asset_class": "STOCK",
        "currency": "TRY",
        "current_price": 45.20,
        "daily_change_pct": -1.8,
        "weekly_change_pct": -5.2,
        "yearly_change_pct": -15.4,
        "sim_volatility": 0.0250,
    },
    {
        "id": 5,
        "symbol": "ASELS",
        "name": "Aselsan",
        "asset_class": "STOCK",
        "currency": "TRY",
        "current_price": 62.10,
        "daily_change_pct": 0.4,
        "weekly_change_pct": 1.2,
        "yearly_change_pct": 85.0,
        "sim_volatility": 0.0200,
    },
    {
        "id": 7,
        "symbol": "GRAM_ALTIN",
        "name": "Gram Altin",
        "asset_class": "GOLD",
        "currency": "TRY",
        "current_price": 2550.00,
        "daily_change_pct": 0.8,
        "weekly_change_pct": 3.5,
        "yearly_change_pct": 82.4,
        "sim_volatility": 0.0080,
    },
    {
        "id": 9,
        "symbol": "USD/TRY",
        "name": "Amerikan Dolari",
        "asset_class": "FOREX",
        "currency": "TRY",
        "current_price": 33.55,
        "daily_change_pct": 0.1,
        "weekly_change_pct": 0.8,
        "yearly_change_pct": 25.4,
        "sim_volatility": 0.0050,
    },
    {
        "id": 10,
        "symbol": "EUR/TRY",
        "name": "Euro",
        "asset_class": "FOREX",
        "currency": "TRY",
        "current_price": 36.80,
        "daily_change_pct": 0.3,
        "weekly_change_pct": 1.2,
        "yearly_change_pct": 28.7,
        "sim_volatility": 0.0050,
    },
    {
        "id": 12,
        "symbol": "BTC",
        "name": "Bitcoin",
        "asset_class": "CRYPTO",
        "currency": "USD",
        "current_price": 65400.00,
        "daily_change_pct": 4.5,
        "weekly_change_pct": -2.3,
        "yearly_change_pct": 125.6,
        "sim_volatility": 0.0400,
    },
    {
        "id": 13,
        "symbol": "ETH",
        "name": "Ethereum",
        "asset_class": "CRYPTO",
        "currency": "USD",
        "current_price": 3450.00,
        "daily_change_pct": 2.1,
        "weekly_change_pct": -1.5,
        "yearly_change_pct": 85.2,
        "sim_volatility": 0.0450,
    },
]

#: Calisma zamaninda GUNCELLENEN kopya (fiyat gorevi buraya yazar).
_ASSETS: list[dict] = [dict(a) for a in _SEED_ASSETS]

#: `market_api_usage` tablosunun bellek ici karsiligi: ISO tarih -> istek
#: sayisi. `market_api_usage` gibi kalici DEGILDIR, surec yeniden baslayinca
#: sifirlanir; amaci DB'siz calisirken gunluk tavanin yok olmasini onlemektir.
_API_USAGE: dict[str, int] = {}


def reset_data() -> None:
    """Varlik fiyatlarini ve api sayacini tohum degerlerine dondurur.

    Fiyat gorevi bellek ici veriyi YERINDE gunceller, yani durum surec omru
    boyunca birikir; birbirinden bagimsiz olmasi gereken testler bunu acikca
    cagirmalidir. `conftest.py` artik otomatik cagirmiyor (testler gercek
    PostgreSQL'e tasindi). Uretimde cagrilmaz.
    """
    _ASSETS.clear()
    _ASSETS.extend(dict(a) for a in _SEED_ASSETS)
    _API_USAGE.clear()


_PORTFOLIOS: list[dict] = [
    {"id": 1, "user_id": 1, "name": "Agresif BIST & Kripto", "is_default": True},
    {"id": 2, "user_id": 2, "name": "Guvenli Liman (Emeklilik)", "is_default": True},
]

_PORTFOLIO_ASSETS: list[dict] = [
    {"portfolio_id": 1, "asset_id": 1, "quantity": 1000, "average_buy_price": 290.00},
    {"portfolio_id": 1, "asset_id": 4, "quantity": 5000, "average_buy_price": 52.00},
    {"portfolio_id": 1, "asset_id": 12, "quantity": 0.5, "average_buy_price": 60000.00},
    {"portfolio_id": 2, "asset_id": 7, "quantity": 200, "average_buy_price": 2300.00},
]

_TRANSACTIONS: list[dict] = [
    {
        "id": 1,
        "portfolio_id": 1,
        "asset_id": 1,
        "transaction_type": "BUY",
        "quantity": 1000,
        "unit_price": 290.00,
        "days_ago": 75,
    },
    {
        "id": 2,
        "portfolio_id": 1,
        "asset_id": 4,
        "transaction_type": "BUY",
        "quantity": 5000,
        "unit_price": 52.00,
        "days_ago": 60,
    },
    {
        "id": 3,
        "portfolio_id": 1,
        "asset_id": 12,
        "transaction_type": "BUY",
        "quantity": 0.5,
        "unit_price": 60000.00,
        "days_ago": 40,
    },
    {
        "id": 4,
        "portfolio_id": 2,
        "asset_id": 7,
        "transaction_type": "BUY",
        "quantity": 200,
        "unit_price": 2300.00,
        "days_ago": 80,
    },
]

#: rag.documents + rag.chunks karsiligi. Embedding YOKTUR: model secilmedigi
#: icin bellek ici arama da kelime eslesmesiyle calisir (SQL tarafinda BM25).
_RAG_CHUNKS: list[dict] = [
    {
        "chunk_id": 1,
        "doc_id": "news-thyao-2026-08-10",
        "baslik": "THY 2. ceyrek net karini %18 artirdi",
        "sirket": "Turk Hava Yollari",
        "symbol": "THYAO",
        "tarih": "2026-08-10",
        "tip": "bilanco",
        "content": (
            "THY, 2026 yili 2. ceyrek finansal sonuclarinda net karini bir onceki yilin "
            "ayni donemine gore %18 artirdi. Sirket, yolcu doluluk oraninin %84 "
            "seviyesine ulastigini acikladi."
        ),
    },
    {
        "chunk_id": 2,
        "doc_id": "kap-thyao-2026-08-10",
        "baslik": "THYAO KAP aciklamasi: yakit maliyetleri geriledi",
        "sirket": "Turk Hava Yollari",
        "symbol": "THYAO",
        "tarih": "2026-08-10",
        "tip": "duyuru",
        "content": (
            "THYAO, KAP'a yaptigi aciklamada yakit maliyetlerindeki dususun karlilik "
            "uzerinde olumlu etkisi oldugunu belirtti."
        ),
    },
    {
        "chunk_id": 3,
        "doc_id": "news-sasa-2026-07-30",
        "baslik": "SASA'da hammadde maliyeti baskisi suruyor",
        "sirket": "Sasa Polyester",
        "symbol": "SASA",
        "tarih": "2026-07-30",
        "tip": "haber",
        "content": (
            "Sasa Polyester'de hammadde maliyetlerindeki artis marjlari baski altinda "
            "tutmaya devam ediyor. Analistler kisa vadede toparlanma beklemiyor."
        ),
    },
    {
        "chunk_id": 4,
        "doc_id": "analiz-kripto-2026-08-01",
        "baslik": "Kripto piyasasinda oynaklik yuksek seyrediyor",
        "sirket": None,
        "symbol": None,
        "tarih": "2026-08-01",
        "tip": "analist_raporu",
        "content": (
            "Bitcoin ve Ethereum'da gunluk oynaklik uzun donem ortalamasinin uzerinde "
            "seyrediyor. Yuksek agirlikli kripto pozisyonlari portfoy riskini artiriyor."
        ),
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bugun() -> str:
    """Api sayacinin gun anahtari - SQL'deki `CURRENT_DATE` karsiligi."""
    return _now().date().isoformat()


def _asset(asset_id: int) -> dict:
    return next(a for a in _ASSETS if a["id"] == asset_id)


def _fx_rate(currency: str) -> float:
    """SQL'deki `v_fx_rates` view'inin karsiligi."""
    if currency == "TRY":
        return 1.0
    symbol = f"{currency}/TRY"
    for asset in _ASSETS:
        if asset["symbol"] == symbol:
            return float(asset["current_price"])
    return 1.0


def _holdings_valued(user_id: int, portfolio_id: int | None) -> list[dict]:
    """`v_holdings_valued` karsiligi - TUM hesaplarin tek kaynagi."""
    portfolios = [
        p
        for p in _PORTFOLIOS
        if p["user_id"] == user_id and (portfolio_id is None or p["id"] == portfolio_id)
    ]
    if portfolio_id is None:
        portfolios = [p for p in portfolios if p["is_default"]] or portfolios

    ids = {p["id"] for p in portfolios}
    rows: list[dict] = []

    for pa in _PORTFOLIO_ASSETS:
        if pa["portfolio_id"] not in ids:
            continue
        asset = _asset(pa["asset_id"])
        fx = _fx_rate(asset["currency"])
        quantity = float(pa["quantity"])
        avg = float(pa["average_buy_price"])
        price = float(asset["current_price"])

        rows.append(
            {
                "portfolio_id": pa["portfolio_id"],
                "asset_id": asset["id"],
                "symbol": asset["symbol"],
                "asset_name": asset["name"],
                "asset_class": asset["asset_class"],
                "currency": asset["currency"],
                "quantity": quantity,
                "average_buy_price": avg,
                "current_price": price,
                "daily_change_pct": asset["daily_change_pct"],
                "market_value_try": quantity * price * fx,
                "cost_basis_try": quantity * avg * fx,
                "pnl_try": quantity * (price - avg) * fx,
                "pnl_pct": ((price - avg) / avg * 100) if avg > 0 else None,
            }
        )
    return rows


class InMemoryUserRepository:
    async def get_by_email(self, email: str) -> dict | None:
        for user in _USERS:
            if user["email"].lower() == email.lower():
                return dict(user)
        return None

    async def get_by_id(self, user_id: int) -> dict | None:
        for user in _USERS:
            if user["id"] == user_id:
                return {k: v for k, v in user.items() if k != "password_hash"}
        return None


class InMemoryPortfolioRepository:
    async def get_default_portfolio_id(self, user_id: int) -> int | None:
        for portfolio in _PORTFOLIOS:
            if portfolio["user_id"] == user_id and portfolio["is_default"]:
                return portfolio["id"]
        return None

    async def get_summary(self, user_id: int, portfolio_id: int | None = None) -> dict | None:
        rows = _holdings_valued(user_id, portfolio_id)
        if not rows:
            return None

        total_value = sum(r["market_value_try"] for r in rows)
        total_cost = sum(r["cost_basis_try"] for r in rows)
        total_pnl = sum(r["pnl_try"] for r in rows)

        return {
            "portfolio_id": rows[0]["portfolio_id"],
            "holding_count": len(rows),
            "total_value_try": total_value,
            "total_cost_try": total_cost,
            "total_pnl_try": total_pnl,
            "total_pnl_pct": (total_pnl / total_cost * 100) if total_cost > 0 else None,
        }

    async def get_holdings(self, user_id: int, portfolio_id: int | None = None) -> list[dict]:
        return sorted(
            _holdings_valued(user_id, portfolio_id),
            key=lambda r: r["market_value_try"],
            reverse=True,
        )

    async def get_allocation(self, user_id: int, portfolio_id: int | None = None) -> list[dict]:
        rows = _holdings_valued(user_id, portfolio_id)
        total = sum(r["market_value_try"] for r in rows)
        if not total:
            return []

        by_class: dict[str, float] = {}
        for row in rows:
            by_class[row["asset_class"]] = by_class.get(row["asset_class"], 0.0) + (
                row["market_value_try"]
            )

        return sorted(
            (
                {
                    "asset_class": asset_class,
                    "class_value": value,
                    "class_pct": round(value / total * 100, 2),
                }
                for asset_class, value in by_class.items()
            ),
            key=lambda r: r["class_value"],
            reverse=True,
        )

    async def get_transactions(
        self, user_id: int, portfolio_id: int | None = None, limit: int = 20
    ) -> list[dict]:
        target = portfolio_id or await self.get_default_portfolio_id(user_id)
        rows = [t for t in _TRANSACTIONS if t["portfolio_id"] == target]
        rows.sort(key=lambda t: t["days_ago"])

        return [
            {
                "id": t["id"],
                "symbol": _asset(t["asset_id"])["symbol"],
                "asset_name": _asset(t["asset_id"])["name"],
                "transaction_type": t["transaction_type"],
                "quantity": float(t["quantity"]),
                "unit_price": float(t["unit_price"]),
                "transaction_date": (_now() - timedelta(days=t["days_ago"])).isoformat(),
            }
            for t in rows[:limit]
        ]


class InMemoryMarketRepository:
    async def list_assets(self, category: str | None = None) -> list[dict]:
        rows = [dict(a) for a in _ASSETS]
        if category:
            rows = [a for a in rows if a["asset_class"] == category.upper()]
        return rows

    async def get_quote(self, symbol: str) -> dict | None:
        for asset in _ASSETS:
            if asset["symbol"].upper() == symbol.upper():
                return {
                    "symbol": asset["symbol"],
                    "name": asset["name"],
                    "currency": asset["currency"],
                    "price": float(asset["current_price"]),
                    "daily_change_pct": asset["daily_change_pct"],
                    "weekly_change_pct": asset["weekly_change_pct"],
                    "asset_class": asset["asset_class"],
                    "ts": _now().isoformat(),
                }
        return None

    async def get_history(self, symbol: str, days: int = 30) -> list[dict]:
        """Deterministik sentetik seri.

        SQL tarafindaki `price_history` backfill'i ile AYNI formulu kullanir
        (yillik trend + sinuzoidal dalga); rastgelelik yoktur, boylece ayni
        grafik her calistirmada ayni cikar.
        """
        asset = next((a for a in _ASSETS if a["symbol"].upper() == symbol.upper()), None)
        if asset is None:
            return []

        price = float(asset["current_price"])
        yearly = float(asset["yearly_change_pct"]) / 100.0
        volatility = float(asset["sim_volatility"])
        now = _now()

        series: list[dict] = []
        for days_ago in range(days, -1, -1):
            drift = 1 - yearly * (days_ago / 365.0)
            wave = volatility * 2.5 * math.sin(days_ago / 6.0)
            value = max(price * (drift + wave), price * 0.05)
            series.append(
                {
                    "ts": (now - timedelta(days=days_ago)).isoformat(),
                    "price": round(value, 4),
                }
            )
        return series

    async def get_prices_for_simulation(self) -> list[dict]:
        return [
            {
                "asset_id": a["id"],
                "symbol": a["symbol"],
                "current_price": float(a["current_price"]),
                "sim_volatility": float(a["sim_volatility"]),
            }
            for a in _ASSETS
        ]

    async def apply_price_updates(
        self, updates: list[dict], write_history: bool, source: str = "simulated"
    ) -> int:
        for update in updates:
            asset = next((a for a in _ASSETS if a["id"] == update["asset_id"]), None)
            if asset is None:
                continue
            previous = float(asset["current_price"])
            new_price = float(update["price"])
            asset["current_price"] = new_price
            if previous:
                asset["daily_change_pct"] = round((new_price - previous) / previous * 100, 4)
        return len(updates)

    async def get_api_usage_today(self) -> int:
        """Bugun dis piyasa API'sine yapilan ISTEK sayisi.

        BELLEK ICI MODDA DA GERCEKTEN SAYILIR. Daha once burasi sabit `0`
        donuyordu; DB'ye ulasilamadiginda repository katmani bu yedege duser
        ama `MARKET_DATA_PROVIDER=api` ise Yahoo cagrilari DEVAM eder - yani
        tam da kotanin en cok gerektigi anda tavan tamamen ortadan kalkiyordu.

        Sayac kalici degildir: surec yeniden baslayinca sifirlanir. DB'li
        moddaki `market_api_usage` tablosunun yerini TUTMAZ, yalnizca yedek
        moddaki sinirsizligi kapatir.
        """
        return _API_USAGE.get(_bugun(), 0)

    async def record_api_usage(self, calls: int = 1) -> None:
        if calls <= 0:
            return
        bugun = _bugun()
        _API_USAGE[bugun] = _API_USAGE.get(bugun, 0) + calls


class InMemoryRagRepository:
    async def search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
    ) -> list[dict]:
        """Kelime ortusmesine dayali basit arama (BM25'in bellek ici karsiligi)."""
        terms = {t for t in _normalize(query).split() if len(t) > 2}
        rows: list[dict] = []

        for chunk in _RAG_CHUNKS:
            # Sirket filtresi hem sembol hem unvan ile eslesir (SQL tarafiyla
            # ayni davranis): ajan "THYAO" gonderir, dokumanda unvan yazili
            # olabilir.
            if sirket and sirket.upper() not in {
                (chunk.get("sirket") or "").upper(),
                (chunk.get("symbol") or "").upper(),
            }:
                continue
            if tip and chunk["tip"] != tip:
                continue

            haystack = _normalize(f"{chunk['baslik']} {chunk['content']} {chunk['sirket'] or ''}")
            hits = sum(1 for term in terms if term in haystack)
            if not hits:
                continue
            rows.append({**chunk, "score": round(hits / max(len(terms), 1), 3)})

        rows.sort(key=lambda r: r["score"], reverse=True)
        return rows[:top_k]


class InMemoryChatRepository:
    """Sohbet kayitlari - surec omru boyunca bellekte tutulur.

    Uygulama yeniden baslatildiginda kaybolur; kalicilik icin DB gerekir.
    """

    def __init__(self) -> None:
        self._sessions: list[dict] = []
        self._messages: list[dict] = []
        self._next_session_id = 1
        self._next_message_id = 1

    async def list_sessions(self, user_id: int, limit: int = 50) -> list[dict]:
        rows = [dict(s) for s in self._sessions if s["user_id"] == user_id]
        rows.sort(key=lambda s: s["updated_at"], reverse=True)
        return rows[:limit]

    async def create_session(self, user_id: int, title: str) -> dict:
        now = _now().isoformat()
        session = {
            "id": self._next_session_id,
            "user_id": user_id,
            "title": title[:100],
            "created_at": now,
            "updated_at": now,
        }
        self._next_session_id += 1
        self._sessions.append(session)
        return dict(session)

    async def get_session(self, session_id: int, user_id: int) -> dict | None:
        for session in self._sessions:
            if session["id"] == session_id and session["user_id"] == user_id:
                return dict(session)
        return None

    async def list_messages(self, session_id: int, limit: int = 200) -> list[dict]:
        rows = [dict(m) for m in self._messages if m["session_id"] == session_id]
        return rows[:limit]

    async def add_message(
        self,
        session_id: int,
        sender_role: str,
        content: str,
        meta: dict | None = None,
        request_id: str | None = None,
    ) -> dict:
        message = {
            "id": self._next_message_id,
            "session_id": session_id,
            "sender_role": sender_role,
            "message_content": content,
            "meta": meta or {},
            "request_id": request_id,
            "created_at": _now().isoformat(),
        }
        self._next_message_id += 1
        self._messages.append(message)

        for session in self._sessions:
            if session["id"] == session_id:
                session["updated_at"] = message["created_at"]
        return dict(message)


class InMemoryAuditRepository:
    """Denetim kayitlarini yalnizca loga yazar (DB yokken).

    Kayit alanlari TEK bir `audit` anahtari altinda toplanir: `logging` modulu
    `args`, `name`, `message` gibi kendi alan adlarinin `extra` ile ezilmesine
    izin vermez ve `KeyError` firlatir - tool argumanlari arasinda `args`
    bulundugu icin bu gercek bir tuzaktir.
    """

    async def log_tool_call(self, record: dict) -> None:
        logger.info("tool_call", extra={"audit": _flatten(record)})

    async def log_security_event(self, record: dict) -> None:
        logger.warning("security_event", extra={"audit": _flatten(record)})


_TR_TRANSLATION = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")


def _normalize(text: str) -> str:
    return text.translate(_TR_TRANSLATION).lower()


def _flatten(record: dict) -> dict:
    """Denetim kaydini JSON'a uygun degerlere cevirir."""
    return {
        k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
        for k, v in record.items()
    }
