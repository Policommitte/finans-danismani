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
from datetime import datetime, timedelta, timezone

from app.core.errors import BusinessRuleError, NotFoundError

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
    },
    {
        "id": 19,
        "symbol": "BIST100",
        "name": "BIST 100 Endeksi",
        "asset_class": "INDEX",
        "currency": "TRY",
        "current_price": 14337.0,
        "daily_change_pct": -0.84,
        "weekly_change_pct": 1.2,
        "yearly_change_pct": 28.0,
    },
]

#: Calisma zamaninda GUNCELLENEN kopya (fiyat gorevi buraya yazar).
_ASSETS: list[dict] = [dict(a) for a in _SEED_ASSETS]
for _seed_asset in _ASSETS:
    _seed_change = float(_seed_asset.get("daily_change_pct") or 0) / 100
    _seed_asset["prev_close"] = float(_seed_asset["current_price"]) / (1 + _seed_change)

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
    for asset in _ASSETS:
        change = float(asset.get("daily_change_pct") or 0) / 100
        asset["prev_close"] = float(asset["current_price"]) / (1 + change)
    _API_USAGE.clear()
    _CASH_ACCOUNTS.clear()
    _CASH_ACCOUNTS.extend(dict(row) for row in _SEED_CASH_ACCOUNTS)
    _PORTFOLIO_ASSETS.clear()
    _PORTFOLIO_ASSETS.extend(dict(row) for row in _SEED_PORTFOLIO_ASSETS)
    _TRANSACTIONS.clear()
    _TRANSACTIONS.extend(dict(row) for row in _SEED_TRANSACTIONS)
    _ORDERS.clear()
    _ORDER_FILLS.clear()


_PORTFOLIOS: list[dict] = [
    {"id": 1, "user_id": 1, "name": "Agresif BIST & Kripto", "is_default": True},
    {"id": 2, "user_id": 2, "name": "Guvenli Liman (Emeklilik)", "is_default": True},
]

_SEED_PORTFOLIO_ASSETS: list[dict] = [
    {"portfolio_id": 1, "asset_id": 1, "quantity": 1000, "average_buy_price": 290.00},
    {"portfolio_id": 1, "asset_id": 4, "quantity": 5000, "average_buy_price": 52.00},
    {"portfolio_id": 1, "asset_id": 12, "quantity": 0.5, "average_buy_price": 60000.00},
    {"portfolio_id": 2, "asset_id": 7, "quantity": 200, "average_buy_price": 2300.00},
]
_PORTFOLIO_ASSETS: list[dict] = [dict(row) for row in _SEED_PORTFOLIO_ASSETS]

_SEED_TRANSACTIONS: list[dict] = [
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
_TRANSACTIONS: list[dict] = [dict(row) for row in _SEED_TRANSACTIONS]

_SEED_CASH_ACCOUNTS: list[dict] = [
    {
        "id": 1,
        "portfolio_id": 1,
        "currency": "TRY",
        "available_balance": 100000.0,
        "reserved_balance": 0.0,
    },
    {
        "id": 2,
        "portfolio_id": 2,
        "currency": "TRY",
        "available_balance": 75000.0,
        "reserved_balance": 0.0,
    },
]
_CASH_ACCOUNTS: list[dict] = [dict(row) for row in _SEED_CASH_ACCOUNTS]
_ORDERS: list[dict] = []
_ORDER_FILLS: list[dict] = []

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


def _previous_fx_rate(currency: str) -> float:
    if currency == "TRY":
        return 1.0
    symbol = f"{currency}/TRY"
    for asset in _ASSETS:
        if asset["symbol"] == symbol:
            return float(asset.get("prev_close") or asset["current_price"])
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
        previous_value = (
            quantity
            * float(asset.get("prev_close") or price)
            * _previous_fx_rate(asset["currency"])
        )
        market_value = quantity * price * fx

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
                "market_value_try": market_value,
                "daily_change_try": market_value - previous_value,
                "daily_change_pct_try": (
                    (market_value - previous_value) / previous_value * 100
                    if previous_value > 0
                    else None
                ),
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

    async def get_performance_history(
        self, user_id: int, portfolio_id: int | None = None, hours: int = 24
    ) -> list[dict]:
        # Bellek ici yedekte dogrulanmis fiyat zaman serisi tutulmaz.
        return []


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
        # Bellek ici yedekte dogrulanmis fiyat zaman serisi tutulmaz.
        return []

    async def get_candles(
        self, symbol: str, interval: str = "5m", days: int = 5
    ) -> list[dict]:
        return []

    async def upsert_candles(self, candles: list[dict], source: str = "yahoo") -> int:
        return 0

    async def prune_candles(self, interval: str, keep_days: int) -> int:
        return 0

    async def get_assets_for_price_update(self) -> list[dict]:
        return [
            {
                "asset_id": a["id"],
                "symbol": a["symbol"],
                "current_price": float(a["current_price"]),
            }
            for a in _ASSETS
        ]

    async def apply_price_updates(self, updates: list[dict], write_live: bool, source: str) -> int:
        """Bellek ici kopyadaki fiyatlari gunceller.

        `write_live` yok sayilir: bu yedek katmanda `live_prices` karsiligi
        bir tablo YOKTUR, dolayisiyla gun ici kayit tutulmaz. Yedek plan
        "uygulama DB'siz de ayakta kalsin" icindir, veri biriktirmek icin
        degil - DB'ye tekrar ulasildiginda tarihce SQL tarafinda kaldigi
        yerden devam eder.
        """
        if updates and source != "api":
            raise ValueError("yalnizca dogrulanmis 'api' fiyatlari yazilabilir")
        for update in updates:
            asset = next((a for a in _ASSETS if a["id"] == update["asset_id"]), None)
            if asset is None:
                continue
            new_price = float(update["price"])
            supplied_previous = update.get("previous_close")
            if supplied_previous is not None and float(supplied_previous) > 0:
                asset["prev_close"] = float(supplied_previous)
            asset["current_price"] = new_price
            previous_close = float(asset.get("prev_close") or 0)
            if previous_close:
                asset["daily_change_pct"] = round(
                    (new_price - previous_close) / previous_close * 100, 4
                )
        return len(updates)

    async def pending_close_days(self) -> list[str]:
        """Her zaman bos: gun ici kayit tutulmadigi icin kapanacak gun yoktur."""
        return []

    async def close_out_day(self, day: str) -> int:
        """Yedek katmanda gun kapanisi YOKTUR; cagrilmasi zararsizdir.

        `pending_close_days` hep bos dondugu icin scheduler burayi normalde
        hic cagirmaz. Yine de sozlesmenin parcasi: SQL yerine bellek ici
        depoya duselim diye cagiran kodun degismesi gerekmez.
        """
        return 0

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


class InMemoryTradingRepository:
    async def get_account(self, user_id: int) -> dict | None:
        portfolio = _default_portfolio(user_id)
        if not portfolio:
            return None
        account = next(
            (a for a in _CASH_ACCOUNTS if a["portfolio_id"] == portfolio["id"]), None
        )
        if not account:
            return None
        return {**account, "portfolio_name": portfolio["name"]}

    async def get_order_context(self, user_id: int, symbol: str) -> dict | None:
        portfolio = _default_portfolio(user_id)
        asset = next((a for a in _ASSETS if a["symbol"].upper() == symbol.upper()), None)
        if not portfolio or not asset:
            return None
        account = next(
            (a for a in _CASH_ACCOUNTS if a["portfolio_id"] == portfolio["id"]), None
        )
        if not account:
            return None
        holding = next(
            (
                h
                for h in _PORTFOLIO_ASSETS
                if h["portfolio_id"] == portfolio["id"] and h["asset_id"] == asset["id"]
            ),
            None,
        )
        pending_sell = sum(
            float(o["quantity"]) - float(o["filled_quantity"])
            for o in _ORDERS
            if o["portfolio_id"] == portfolio["id"]
            and o["asset_id"] == asset["id"]
            and o["side"] == "SELL"
            and o["status"] == "PENDING"
            and o.get("order_type") != "STOP_MARKET"
        )
        return {
            "portfolio_id": portfolio["id"],
            "asset_id": asset["id"],
            "symbol": asset["symbol"],
            "asset_name": asset["name"],
            "asset_class": asset["asset_class"],
            "currency": asset["currency"],
            "current_price": float(asset["current_price"]) * _fx_rate(asset["currency"]),
            "price_updated_at": asset.get("price_updated_at"),
            "available_balance": account["available_balance"],
            "reserved_balance": account["reserved_balance"],
            "holding_quantity": float(holding["quantity"]) if holding else 0.0,
            "pending_sell_quantity": pending_sell,
        }

    async def create_market_order(
        self,
        user_id: int,
        symbol: str,
        side: str,
        quantity: float,
        idempotency_key: str,
        commission_rate: float,
        order_type: str = "MARKET",
        limit_price: float | None = None,
        validity: str = "GTC",
        expires_at: object | None = None,
        stop_loss_price: float | None = None,
    ) -> dict:
        existing = next(
            (
                o
                for o in _ORDERS
                if o["user_id"] == user_id and o["idempotency_key"] == idempotency_key
            ),
            None,
        )
        if existing:
            return dict(existing)
        context = await self.get_order_context(user_id, symbol)
        if not context:
            raise NotFoundError(f"'{symbol.upper()}' hissesi veya paper hesabi bulunamadi.")
        if context["asset_class"] == "INDEX":
            raise BusinessRuleError("Endeksler dogrudan alinip satilamaz.")
        if side not in {"BUY", "SELL"} or quantity <= 0:
            raise BusinessRuleError("Gecersiz emir bilgisi.")
        if order_type not in {"MARKET", "LIMIT"}:
            raise BusinessRuleError("Gecersiz emir tipi.")
        if order_type == "LIMIT" and (limit_price is None or limit_price <= 0):
            raise BusinessRuleError("Limit fiyati sifirdan buyuk olmalidir.")
        if validity not in {"DAY", "GTC"}:
            raise BusinessRuleError("Gecersiz emir gecerliligi.")
        if stop_loss_price is not None:
            reference = float(limit_price) if order_type == "LIMIT" else float(context["current_price"])
            if side != "BUY" or stop_loss_price <= 0 or stop_loss_price >= reference:
                raise BusinessRuleError("Stop-loss fiyati alim referans fiyatindan dusuk olmalidir.")

        account = next(a for a in _CASH_ACCOUNTS if a["portfolio_id"] == context["portfolio_id"])
        reserve_price = float(limit_price) if order_type == "LIMIT" else float(context["current_price"])
        gross = reserve_price * quantity
        reserve = round(
            gross * (1 if order_type == "LIMIT" else 1.02) + gross * commission_rate,
            2,
        ) if side == "BUY" else 0.0
        if side == "BUY":
            if account["available_balance"] < reserve:
                raise BusinessRuleError(
                    "Fiyat tamponu dahil bu alim emri icin sanal bakiye yetersiz."
                )
            account["available_balance"] -= reserve
            account["reserved_balance"] += reserve
        elif context["holding_quantity"] - context["pending_sell_quantity"] < quantity:
            raise BusinessRuleError(
                "Bekleyen emirler dusuldugunde satilabilir hisse adedi yetersiz."
            )

        now = datetime.now(timezone.utc).isoformat()
        order = {
            "id": len(_ORDERS) + 1,
            "user_id": user_id,
            "portfolio_id": context["portfolio_id"],
            "asset_id": context["asset_id"],
            "symbol": context["symbol"],
            "asset_name": context["asset_name"],
            "side": side,
            "order_type": order_type,
            "limit_price": limit_price,
            "stop_loss_price": stop_loss_price,
            "parent_order_id": None,
            "validity": validity,
            "expires_at": expires_at.isoformat() if hasattr(expires_at, "isoformat") else expires_at,
            "quantity": quantity,
            "quoted_price": context["current_price"],
            "status": "PENDING",
            "filled_quantity": 0.0,
            "average_fill_price": None,
            "commission": 0.0,
            "reserved_amount": reserve,
            "rejection_reason": None,
            "idempotency_key": idempotency_key,
            "created_at": now,
            "filled_at": None,
        }
        _ORDERS.append(order)
        return dict(order)

    async def list_orders(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = [dict(o) for o in _ORDERS if o["user_id"] == user_id]
        rows.sort(key=lambda o: (o["created_at"], o["id"]), reverse=True)
        return rows[:limit]

    async def cancel_order(self, user_id: int, order_id: int) -> dict:
        order = next(
            (row for row in _ORDERS if row["id"] == order_id and row["user_id"] == user_id),
            None,
        )
        if not order:
            raise NotFoundError("Emir bulunamadi.")
        if order["status"] != "PENDING":
            raise BusinessRuleError("Yalnizca bekleyen emirler iptal edilebilir.")
        account = next(a for a in _CASH_ACCOUNTS if a["portfolio_id"] == order["portfolio_id"])
        reserve = float(order.get("reserved_amount") or 0)
        account["available_balance"] += reserve
        account["reserved_balance"] -= reserve
        order.update(status="CANCELLED", reserved_amount=0.0)
        return dict(order)

    async def process_pending_orders(self, updates: list[dict], commission_rate: float) -> int:
        prices = {
            int(u["asset_id"]): float(u["price"])
            for u in updates
            if float(u.get("price") or 0) > 0
        }
        completed = 0
        pending_snapshot = sorted(
            list(_ORDERS),
            key=lambda row: (row.get("order_type") == "STOP_MARKET", row["created_at"], row["id"]),
        )
        for order in pending_snapshot:
            expires_at = order.get("expires_at")
            if order["status"] == "PENDING" and expires_at:
                expiry = datetime.fromisoformat(str(expires_at))
                if expiry <= datetime.now(timezone.utc):
                    account = next(
                        a for a in _CASH_ACCOUNTS if a["portfolio_id"] == order["portfolio_id"]
                    )
                    reserve = float(order.get("reserved_amount") or 0)
                    account["available_balance"] += reserve
                    account["reserved_balance"] -= reserve
                    order.update(status="CANCELLED", reserved_amount=0.0)
                    continue
            if order["status"] != "PENDING" or order["asset_id"] not in prices:
                continue
            asset = _asset(order["asset_id"])
            native_price = prices[order["asset_id"]]
            price = native_price * _fx_rate(asset["currency"])
            if order["order_type"] == "LIMIT":
                limit = float(order["limit_price"])
                if order["side"] == "BUY" and price > limit:
                    continue
                if order["side"] == "SELL" and price < limit:
                    continue
            elif order["order_type"] == "STOP_MARKET":
                if price > float(order["stop_loss_price"]):
                    continue
                current_holding = next(
                    (
                        h for h in _PORTFOLIO_ASSETS
                        if h["portfolio_id"] == order["portfolio_id"]
                        and h["asset_id"] == order["asset_id"]
                    ),
                    None,
                )
                manual_pending = sum(
                    float(other["quantity"]) - float(other["filled_quantity"])
                    for other in _ORDERS
                    if other["portfolio_id"] == order["portfolio_id"]
                    and other["asset_id"] == order["asset_id"]
                    and other["side"] == "SELL"
                    and other["status"] == "PENDING"
                    and other.get("order_type") != "STOP_MARKET"
                )
                effective = min(
                    float(order["quantity"]),
                    max(float(current_holding["quantity"]) - manual_pending, 0)
                    if current_holding else 0,
                )
                if effective <= 0:
                    continue
                order["quantity"] = effective
            gross = round(price * float(order["quantity"]), 2)
            commission = round(gross * commission_rate, 2)
            account = next(
                a for a in _CASH_ACCOUNTS if a["portfolio_id"] == order["portfolio_id"]
            )
            holding = next(
                (
                    h
                    for h in _PORTFOLIO_ASSETS
                    if h["portfolio_id"] == order["portfolio_id"]
                    and h["asset_id"] == order["asset_id"]
                ),
                None,
            )
            if order["side"] == "BUY":
                total = gross + commission
                reserve = float(order["reserved_amount"])
                if account["available_balance"] + reserve < total:
                    account["available_balance"] += reserve
                    account["reserved_balance"] -= reserve
                    order["status"] = "REJECTED"
                    order["rejection_reason"] = "Yeni fiyatta kullanilabilir bakiye yetersiz."
                    continue
                account["available_balance"] += reserve - total
                account["reserved_balance"] -= reserve
                if holding:
                    old_qty = float(holding["quantity"])
                    new_qty = old_qty + float(order["quantity"])
                    holding["average_buy_price"] = (
                        old_qty * float(holding["average_buy_price"])
                        + float(order["quantity"]) * native_price
                    ) / new_qty
                    holding["quantity"] = new_qty
                else:
                    _PORTFOLIO_ASSETS.append(
                        {
                            "portfolio_id": order["portfolio_id"],
                            "asset_id": order["asset_id"],
                            "quantity": order["quantity"],
                            "average_buy_price": native_price,
                        }
                    )
            else:
                if not holding or float(holding["quantity"]) < float(order["quantity"]):
                    order["status"] = "REJECTED"
                    order["rejection_reason"] = "Gerceklesme aninda satilabilir adet yetersiz."
                    continue
                holding["quantity"] = float(holding["quantity"]) - float(order["quantity"])
                if holding["quantity"] == 0:
                    _PORTFOLIO_ASSETS.remove(holding)
                account["available_balance"] += gross - commission

            _TRANSACTIONS.append(
                {
                    "id": max((row["id"] for row in _TRANSACTIONS), default=0) + 1,
                    "portfolio_id": order["portfolio_id"],
                    "asset_id": order["asset_id"],
                    "transaction_type": order["side"],
                    "quantity": order["quantity"],
                    "unit_price": native_price,
                    "days_ago": 0,
                }
            )

            now = datetime.now(timezone.utc).isoformat()
            order.update(
                status="FILLED",
                filled_quantity=order["quantity"],
                average_fill_price=price,
                commission=commission,
                filled_at=now,
            )
            if order["side"] == "BUY" and order.get("stop_loss_price") is not None:
                _ORDERS.append(
                    {
                        "id": max((row["id"] for row in _ORDERS), default=0) + 1,
                        "user_id": order["user_id"],
                        "portfolio_id": order["portfolio_id"],
                        "asset_id": order["asset_id"],
                        "symbol": order["symbol"],
                        "asset_name": order["asset_name"],
                        "side": "SELL",
                        "order_type": "STOP_MARKET",
                        "limit_price": None,
                        "stop_loss_price": order["stop_loss_price"],
                        "parent_order_id": order["id"],
                        "validity": "GTC",
                        "expires_at": None,
                        "quantity": order["quantity"],
                        "quoted_price": price,
                        "status": "PENDING",
                        "filled_quantity": 0.0,
                        "average_fill_price": None,
                        "commission": 0.0,
                        "reserved_amount": 0.0,
                        "rejection_reason": None,
                        "idempotency_key": f"attached-stop-{order['id']}",
                        "created_at": now,
                        "filled_at": None,
                    }
                )
            if order["side"] == "SELL" and order["order_type"] != "STOP_MARKET":
                self._normalize_stop_orders(
                    order["portfolio_id"], order["asset_id"], float(order["quantity"])
                )
            _ORDER_FILLS.append(
                {
                    "order_id": order["id"],
                    "quantity": order["quantity"],
                    "price": price,
                    "commission": commission,
                    "executed_at": now,
                }
            )
            completed += 1
        return completed

    @staticmethod
    def _normalize_stop_orders(
        portfolio_id: int, asset_id: int, sold_quantity: float
    ) -> None:
        holding = next(
            (
                row for row in _PORTFOLIO_ASSETS
                if row["portfolio_id"] == portfolio_id and row["asset_id"] == asset_id
            ),
            None,
        )
        available = float(holding["quantity"]) if holding else 0.0
        manual_reduction = sold_quantity
        stops = sorted(
            (
                row for row in _ORDERS
                if row["portfolio_id"] == portfolio_id
                and row["asset_id"] == asset_id
                and row.get("order_type") == "STOP_MARKET"
                and row["status"] == "PENDING"
            ),
            key=lambda row: (row["created_at"], row["id"]),
        )
        for stop in stops:
            original = float(stop["quantity"])
            reduction = min(original, manual_reduction)
            manual_reduction -= reduction
            protected = min(original - reduction, available)
            if protected <= 0:
                stop["status"] = "CANCELLED"
            else:
                stop["quantity"] = protected
            available -= protected


def _default_portfolio(user_id: int) -> dict | None:
    rows = [p for p in _PORTFOLIOS if p["user_id"] == user_id]
    return next((p for p in rows if p["is_default"]), rows[0] if rows else None)


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
