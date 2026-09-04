# ruff: noqa: E501 -- Sabit TR/EN oyun metinleri okunabilirlik icin bolunmez.
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
from datetime import date, datetime, timedelta, timezone

from app.core.errors import BusinessRuleError, NotFoundError

logger = logging.getLogger(__name__)

# --- users ------------------------------------------------------------------
# password_hash degerleri SQL seed'inden birebir alinmistir; hepsinin sifresi
# "demo1234" (bcrypt, cost 10). Gercek bir sir degildir - dummy data.
_SEED_USERS: list[dict] = [
    {
        "id": 1,
        "first_name": "Mehmet",
        "last_name": "Yilmaz",
        "email": "mehmet@example.com",
        "password_hash": "$2b$10$IR711tECQxZE.JMPUjgWs.y9LzkCYTDDqbejiRAB7YkEYAvSdDIXW",
        "risk_tolerance": "HIGH",
        "monthly_income": 150000.0,
        "onboarding_completed": True,
        "marketing_consent": True,
        "likit_para": 200000.0,
        "phone_number": "+905321112233",
        "birth_date": "1985-04-12",
        "tckn_last4": "4821",
        "role": "customer",
    },
    {
        "id": 2,
        "first_name": "Ayse",
        "last_name": "Kaya",
        "email": "ayse@example.com",
        "password_hash": "$2b$10$Yb8T7yJiAWQQD71v45o/EOpGCQVCWj9sAbJmjl5R6HKa39lyKW36S",
        "risk_tolerance": "LOW",
        "monthly_income": 75000.0,
        "onboarding_completed": True,
        "marketing_consent": True,
        "likit_para": 150000.0,
        "phone_number": "+905339998877",
        "birth_date": "1992-11-03",
        "tckn_last4": "1750",
        "role": "customer",
    },
    {
        "id": 3,
        "first_name": "Deniz",
        "last_name": "Danisman",
        "email": "danisman@example.com",
        "password_hash": "$2b$10$IR711tECQxZE.JMPUjgWs.y9LzkCYTDDqbejiRAB7YkEYAvSdDIXW",
        "risk_tolerance": None,
        "monthly_income": 0.0,
        "marketing_consent": False,
        "likit_para": 0.0,
        "phone_number": None,
        "birth_date": None,
        "tckn_last4": None,
        "role": "advisor",
    },
    # Portfoyu YOK (`_PORTFOLIOS`'ta satiri yok) ve islemi YOK: yani
    # `total_value_try=0`, `days_since_activity=None`. Lead motorunun hedef
    # kitlesi tam olarak budur - bu kayit olmadan DB'siz modda hicbir lead
    # uretilemez ve ozellik denenemezdi.
    {
        "id": 4,
        "first_name": "Sema",
        "last_name": "Atil",
        "email": "sema@example.com",
        "password_hash": "$2b$10$IR711tECQxZE.JMPUjgWs.y9LzkCYTDDqbejiRAB7YkEYAvSdDIXW",
        "risk_tolerance": "MEDIUM",
        "monthly_income": 45000.0,
        "marketing_consent": True,
        "likit_para": 300000.0,
        "phone_number": "+905324445566",
        "birth_date": "1978-07-21",
        "tckn_last4": "9034",
        "role": "customer",
    },
]
#: ⚠️ `_USERS` TOHUMDAN TURETILIR ve `reset_data()` onu tohuma dondurur.
#: Kayit ucu bu listeye YAZAR (`create`); tohumun kendisi yazilsaydi bir
#: testin olusturdugu kullanici tum oturum boyunca kalir ve ayni e-posta
#: ile kayit deneyen bir sonraki test 409 alirdi.
_USERS: list[dict] = [dict(row) for row in _SEED_USERS]

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
    _PORTFOLIO_VALUE_SNAPSHOTS.clear()
    _PORTFOLIO_ASSETS.clear()
    _PORTFOLIO_ASSETS.extend(dict(row) for row in _SEED_PORTFOLIO_ASSETS)
    _TRANSACTIONS.clear()
    _TRANSACTIONS.extend(dict(row) for row in _SEED_TRANSACTIONS)
    _ORDERS.clear()
    _ORDER_FILLS.clear()
    _NOTIFICATION_OUTBOX.clear()
    _SIGNALS.clear()
    _RECOMMENDATIONS.clear()
    _REC_AUDIT.clear()
    _USERS.clear()
    _USERS.extend(dict(row) for row in _SEED_USERS)
    _USER_LIMITS.clear()
    _BASKET_STATES.clear()
    _KILL_SWITCH.update({"active": False, "reason": None, "activated_by": None})


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
_PORTFOLIO_VALUE_SNAPSHOTS: list[dict] = []
_ORDERS: list[dict] = []
#: Bellek ici bildirim outbox'i - SQL'deki `notification_outbox` karsiligi.
_NOTIFICATION_OUTBOX: list[dict] = []

#: Otonom oneri motorunun bellek ici durumu (SQL karsiliklari:
#: signals, recommendations, recommendation_audit, user_trading_limits,
#: autonomous_kill_switch).
_SIGNALS: list[dict] = []
_RECOMMENDATIONS: list[dict] = []
_REC_AUDIT: list[dict] = []
_USER_LIMITS: dict[int, dict] = {}
_BASKET_STATES: dict[tuple[int, str], dict] = {}
_KILL_SWITCH: dict = {"active": False, "reason": None, "activated_by": None}


def _enqueue_outbox(order: dict, event_type: str, extra: dict | None = None) -> None:
    """Emir olayini bellek ici outbox'a yazar.

    SQL tarafinda bu yazim gerceklesmeyle AYNI transaction icindedir; bellek
    ici surumde transaction kavrami yok, bu yuzden cagri noktalari SQL ile
    ayni yerlerde tutulur ki iki uygulama ayni olaylari uretsin.
    """
    user = next((u for u in _USERS if u["id"] == order.get("user_id")), None)
    _NOTIFICATION_OUTBOX.append(
        {
            "id": len(_NOTIFICATION_OUTBOX) + 1,
            "user_id": order.get("user_id"),
            "order_id": order.get("id"),
            "event_type": event_type,
            "channel": "EMAIL",
            "recipient": (user or {}).get("email", ""),
            "payload": {
                "symbol": order.get("symbol"),
                "asset_name": order.get("asset_name"),
                "side": order.get("side"),
                "order_type": order.get("order_type"),
                "quantity": order.get("quantity"),
                "rejection_reason": order.get("rejection_reason"),
                **(extra or {}),
            },
            "status": "PENDING",
            "attempts": 0,
            "last_error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "processed_at": None,
        }
    )


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
        "kaynak_url": "https://www.kap.org.tr/tr/Bildirim/thyao-2026-2c",
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
        "kaynak_url": "https://www.kap.org.tr/tr/Bildirim/thyao-yakit-maliyeti",
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
        # Bilincli olarak `None`: kaynak_url'i BOS olan dokumanlar gercekte de
        # vardir (eski ingestion kayitlari). Arayuzun tiklanamaz karti dogru
        # cizdigi bu satir sayesinde gelistirme modunda da gorunur.
        "kaynak_url": None,
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
        "kaynak_url": "https://www.bloomberght.com/kripto/oynaklik-raporu-2026-08",
        "content": (
            "Bitcoin ve Ethereum'da gunluk oynaklik uzun donem ortalamasinin uzerinde "
            "seyrediyor. Yuksek agirlikli kripto pozisyonlari portfoy riskini artiriyor."
        ),
    },
]

#: Lead motorunun bellek ici durumu - surec omru boyunca birikir (DB'siz
#: mod icin, kalicilik gerekmez). SQL tarafindaki lead_scans/
#: lead_queue_entries/lead_contacts karsiligi.
_LEAD_SCANS: list[dict] = []
_LEAD_QUEUE_ENTRIES: list[dict] = []
_LEAD_CONTACTS: list[dict] = []
#: Danismanin elle isaretledigi gorusme sonuclari - EKLEME-ONLY, SQL
#: tarafindaki `lead_call_outcomes` ile ayni davranis: en son satir gecerli.
_LEAD_CALL_OUTCOMES: list[dict] = []
_next_scan_id = 1
_next_contact_id = 1


def _lead_signals() -> list[dict]:
    """`v_lead_user_signals` karsiligi - SQL tarafiyla AYNI mantik,
    yalnizca `lead_rules.py`'nin gercekten okudugu alanlarla sinirli."""
    rows: list[dict] = []
    son_gorusmeler = _son_gorusmeler()
    for user in _USERS:
        if user.get("role", "customer") != "customer":
            continue
        holdings = _holdings_valued(user["id"], None)
        total_value = sum(h["market_value_try"] for h in holdings)
        portfolio_ids = [p["id"] for p in _PORTFOLIOS if p["user_id"] == user["id"]]
        gun_farklari = [t["days_ago"] for t in _TRANSACTIONS if t["portfolio_id"] in portfolio_ids]
        rows.append(
            {
                "user_id": user["id"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "monthly_income": user["monthly_income"],
                "marketing_consent": user.get("marketing_consent", True),
                "likit_para": user.get("likit_para", 0.0),
                "total_value_try": total_value,
                "holding_count": len(holdings),
                "days_since_activity": min(gun_farklari) if gun_farklari else None,
                "advisor_outcome": (son_gorusmeler.get(user["id"]) or {}).get("outcome"),
            }
        )
    return rows


def _son_gorusmeler() -> dict[int, dict]:
    """Kullanici basina EN SON gorusme sonucu - SQL'deki `SON_GORUSME`
    CTE'sinin karsiligi. `ACIK` ("sonucu temizle") sozluge HIC girmez,
    boylece cagiran taraf "isaretlenmemis" ile "temizlenmis" arasinda
    ayrim yapmak zorunda kalmaz."""
    son: dict[int, dict] = {}
    for kayit in _LEAD_CALL_OUTCOMES:
        mevcut = son.get(kayit["user_id"])
        if mevcut is None or kayit["created_at"] >= mevcut["created_at"]:
            son[kayit["user_id"]] = kayit
    return {user_id: kayit for user_id, kayit in son.items() if kayit["outcome"] != "ACIK"}


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


#: `password_hash`/`tckn_hash` HICBIR zaman disari donmez (get_by_email
#: haric - o auth katmani icin password_hash'i taşımak ZORUNDA, ama
#: tckn_hash orada da gerekmiyor).
_GIZLI_ALANLAR = ("password_hash", "tckn_hash")


class InMemoryUserRepository:
    async def get_by_email(self, email: str) -> dict | None:
        for user in _USERS:
            if user["email"].lower() == email.lower():
                return {k: v for k, v in user.items() if k != "tckn_hash"}
        return None

    async def get_by_id(self, user_id: int) -> dict | None:
        for user in _USERS:
            if user["id"] == user_id:
                return {k: v for k, v in user.items() if k not in _GIZLI_ALANLAR}
        return None

    async def create(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        account_number: str | None = None,
    ) -> dict:
        new_id = max((user["id"] for user in _USERS), default=0) + 1
        user = {
            "id": new_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password_hash": password_hash,
            "risk_tolerance": None,
            "monthly_income": 0.0,
            "onboarding_completed": False,
            "has_seen_tour": False,
            "tckn_hash": None,
            "tckn_last4": None,
            "birth_date": None,
            "phone_number": None,
            "account_number": account_number,
        }
        _USERS.append(user)
        return {k: v for k, v in user.items() if k not in _GIZLI_ALANLAR}

    async def complete_onboarding(self, user_id: int, risk_tolerance: str) -> dict | None:
        for user in _USERS:
            if user["id"] == user_id:
                user["risk_tolerance"] = risk_tolerance
                user["onboarding_completed"] = True
                return {k: v for k, v in user.items() if k not in _GIZLI_ALANLAR}
        return None

    async def mark_tour_seen(self, user_id: int) -> dict | None:
        for user in _USERS:
            if user["id"] == user_id:
                user["has_seen_tour"] = True
                return {k: v for k, v in user.items() if k not in _GIZLI_ALANLAR}
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
        self,
        user_id: int,
        portfolio_id: int | None = None,
        hours: int = 24,
        valid_from: datetime | None = None,
        gunluk: bool = False,
    ) -> list[dict]:
        # Bellek ici yedekte dogrulanmis fiyat zaman serisi tutulmaz.
        return []

    async def get_period_pnl(
        self, user_id: int, portfolio_id: int | None = None, start_ts: datetime | None = None
    ) -> list[dict]:
        # Fiyat gecmisi olmadan donem basi deger hesaplanamaz; bos donmek
        # ekranda "donem kar/zarari yok" demektir, uydurma rakam degil.
        return []

    async def write_value_snapshots(self) -> int:
        timestamp = _now().astimezone(timezone.utc)
        written = 0
        for portfolio in _PORTFOLIOS:
            holdings = sum(
                float(row["market_value_try"])
                for row in _holdings_valued(portfolio["user_id"], portfolio["id"])
            )
            cash = sum(
                float(account["available_balance"]) + float(account["reserved_balance"])
                for account in _CASH_ACCOUNTS
                if account["portfolio_id"] == portfolio["id"] and account["currency"] == "TRY"
            )
            snapshot = {
                "portfolio_id": portfolio["id"],
                "ts": timestamp,
                "holdings_value_try": holdings,
                "cash_value_try": cash,
                "total_value_try": holdings + cash,
            }
            _PORTFOLIO_VALUE_SNAPSHOTS.append(snapshot)
            written += 1
        return written

    async def get_value_snapshots(
        self, user_id: int, portfolio_id: int | None = None, hours: int = 24
    ) -> list[dict]:
        target = portfolio_id or await self.get_default_portfolio_id(user_id)
        valid_portfolio = next(
            (p for p in _PORTFOLIOS if p["id"] == target and p["user_id"] == user_id), None
        )
        if valid_portfolio is None:
            return []
        cutoff = _now().astimezone(timezone.utc) - timedelta(hours=hours)
        return [
            dict(row)
            for row in sorted(_PORTFOLIO_VALUE_SNAPSHOTS, key=lambda item: item["ts"])
            if row["portfolio_id"] == target and row["ts"] >= cutoff
        ]

    async def prune_value_snapshots(self, keep_days: int = 30) -> int:
        cutoff = _now().astimezone(timezone.utc) - timedelta(days=keep_days)
        old_count = len(_PORTFOLIO_VALUE_SNAPSHOTS)
        _PORTFOLIO_VALUE_SNAPSHOTS[:] = [
            row for row in _PORTFOLIO_VALUE_SNAPSHOTS if row["ts"] >= cutoff
        ]
        return old_count - len(_PORTFOLIO_VALUE_SNAPSHOTS)


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

    async def get_candles(self, symbol: str, interval: str = "5m", days: int = 5) -> list[dict]:
        return []

    async def upsert_candles(self, candles: list[dict], source: str = "yahoo") -> int:
        return 0

    async def prune_candles(self, interval: str, keep_days: int) -> int:
        return 0

    async def get_history_range(self, symbol: str, start: str, end: str) -> list[dict]:
        """Tarih araligini ayni sentetik seriden keser.

        Ayri bir formul YAZILMAZ: `get_history` ile ayni egriyi uretip
        araliga suzuyoruz, boylece iki metot birbirinden sapamaz.
        """
        try:
            bas = date.fromisoformat(start)
            son = date.fromisoformat(end)
        except ValueError:
            return []
        if son < bas:
            return []

        # Bugunden `bas` gunune kadar geri gidecek kadar uzun bir seri uret.
        gun_sayisi = (_now().date() - bas).days
        if gun_sayisi < 0:
            return []

        seri = await self.get_history(symbol, days=min(gun_sayisi + 1, 3650))
        return [s for s in seri if bas <= date.fromisoformat(s["ts"][:10]) <= son]

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
        account = next((a for a in _CASH_ACCOUNTS if a["portfolio_id"] == portfolio["id"]), None)
        if not account:
            return None
        return {**account, "portfolio_name": portfolio["name"]}

    async def get_order_context(self, user_id: int, symbol: str) -> dict | None:
        portfolio = _default_portfolio(user_id)
        asset = next((a for a in _ASSETS if a["symbol"].upper() == symbol.upper()), None)
        if not portfolio or not asset:
            return None
        account = next((a for a in _CASH_ACCOUNTS if a["portfolio_id"] == portfolio["id"]), None)
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
            "native_price": float(asset["current_price"]),
            "fx_rate": _fx_rate(asset["currency"]),
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
            reference = (
                float(limit_price) / float(context["fx_rate"])
                if order_type == "LIMIT"
                else float(context["native_price"])
            )
            if side != "BUY" or stop_loss_price <= 0 or stop_loss_price >= reference:
                raise BusinessRuleError(
                    "Stop-loss fiyati alim referans fiyatindan dusuk olmalidir."
                )

        account = next(a for a in _CASH_ACCOUNTS if a["portfolio_id"] == context["portfolio_id"])
        reserve_price = (
            float(limit_price) if order_type == "LIMIT" else float(context["current_price"])
        )
        gross = reserve_price * quantity
        reserve = (
            round(
                gross * (1 if order_type == "LIMIT" else 1.02) + gross * commission_rate,
                2,
            )
            if side == "BUY"
            else 0.0
        )
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
            "stop_loss_currency": (context["currency"] if stop_loss_price is not None else None),
            "parent_order_id": None,
            "validity": validity,
            "expires_at": (
                expires_at.isoformat() if hasattr(expires_at, "isoformat") else expires_at
            ),
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
            int(u["asset_id"]): float(u["price"]) for u in updates if float(u.get("price") or 0) > 0
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
                    _enqueue_outbox(order, "ORDER_EXPIRED")
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
                comparison_price = native_price if order.get("stop_loss_currency") else price
                if comparison_price > float(order["stop_loss_price"]):
                    continue
                current_holding = next(
                    (
                        h
                        for h in _PORTFOLIO_ASSETS
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
                    (
                        max(float(current_holding["quantity"]) - manual_pending, 0)
                        if current_holding
                        else 0
                    ),
                )
                if effective <= 0:
                    continue
                order["quantity"] = effective
            gross = round(price * float(order["quantity"]), 2)
            commission = round(gross * commission_rate, 2)
            account = next(a for a in _CASH_ACCOUNTS if a["portfolio_id"] == order["portfolio_id"])
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
                    _enqueue_outbox(order, "ORDER_REJECTED")
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
                    _enqueue_outbox(order, "ORDER_REJECTED")
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
            _enqueue_outbox(
                order,
                "ORDER_FILLED",
                {
                    "price": price,
                    "commission": commission,
                    "total": round(
                        gross + commission if order["side"] == "BUY" else gross - commission, 2
                    ),
                },
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
                        "stop_loss_currency": order.get("stop_loss_currency"),
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
    def _normalize_stop_orders(portfolio_id: int, asset_id: int, sold_quantity: float) -> None:
        holding = next(
            (
                row
                for row in _PORTFOLIO_ASSETS
                if row["portfolio_id"] == portfolio_id and row["asset_id"] == asset_id
            ),
            None,
        )
        available = float(holding["quantity"]) if holding else 0.0
        manual_reduction = sold_quantity
        stops = sorted(
            (
                row
                for row in _ORDERS
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


class InMemoryNotificationRepository:
    """`notification_outbox` yedegi (DB yokken).

    SQL surumunden tek farki eszamanlilik: burada `SKIP LOCKED` yoktur cunku
    tek surec ve tek liste vardir.
    """

    async def claim_pending(self, limit: int, max_attempts: int = 5) -> list[dict]:
        secilen = [
            row
            for row in _NOTIFICATION_OUTBOX
            if row["status"] == "PENDING" and row["attempts"] < max_attempts
        ][:limit]
        for row in secilen:
            row["attempts"] += 1
        return [dict(row) for row in secilen]

    async def mark(self, outbox_id: int, status: str, error: str | None = None) -> None:
        row = next((r for r in _NOTIFICATION_OUTBOX if r["id"] == outbox_id), None)
        if row is None:
            return
        row["status"] = status
        row["last_error"] = error
        row["processed_at"] = datetime.now(timezone.utc).isoformat()

    async def list_for_user(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = [dict(r) for r in _NOTIFICATION_OUTBOX if r["user_id"] == user_id]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return rows[:limit]


def _to_datetime(value) -> datetime | None:
    """ISO metni ya da datetime -> tz farkindali datetime."""
    if value is None:
        return None
    an = value
    if isinstance(an, str):
        try:
            an = datetime.fromisoformat(an)
        except ValueError:
            return None
    return an if an.tzinfo else an.replace(tzinfo=timezone.utc)


class InMemoryRecommendationRepository:
    """Otonom oneri motorunun bellek ici yedegi.

    SQL surumuyle AYNI davranisi tasir; tek fark eszamanlilik kilitleridir
    (tek surec, tek liste). Testlerin cogu bu uygulamaya kosar.
    """

    VARSAYILAN_LIMITLER = {
        "per_order_limit_try": 5000.0,
        "daily_limit_try": 15000.0,
        "allowed_asset_classes": [],
        "autonomous_enabled": True,
        "max_daily_recommendations": 4,
    }

    async def kill_switch_active(self) -> bool:
        return bool(_KILL_SWITCH["active"])

    async def set_kill_switch(self, active: bool, reason: str | None, actor: str) -> dict:
        _KILL_SWITCH.update({"active": active, "reason": reason, "activated_by": actor})
        return dict(_KILL_SWITCH)

    async def get_limits(self, user_id: int) -> dict:
        return dict(_USER_LIMITS.get(user_id) or self.VARSAYILAN_LIMITLER)

    async def upsert_limits(self, user_id: int, fields: dict) -> dict:
        mevcut = await self.get_limits(user_id)
        mevcut.update({k: v for k, v in fields.items() if v is not None})
        _USER_LIMITS[user_id] = mevcut
        return dict(mevcut)

    async def assets_for_scan(self) -> list[dict]:
        return [
            {
                "asset_id": a["id"],
                "symbol": a["symbol"],
                "name": a["name"],
                "asset_class": a["asset_class"],
                "currency": a["currency"],
                "sector": a.get("sector") or a["asset_class"],
                "region": a.get("region")
                or (
                    "TR"
                    if a["asset_class"] == "STOCK"
                    else "US" if a["asset_class"] in {"USA_STOCK", "ETF"} else "GLOBAL"
                ),
                "current_price": float(a["current_price"]) * _fx_rate(a["currency"]),
                "daily_change_pct": a.get("daily_change_pct"),
                "weekly_change_pct": a.get("weekly_change_pct"),
                "yearly_change_pct": a.get("yearly_change_pct"),
                "volatility_20d_pct": abs(float(a.get("daily_change_pct") or 0))
                + abs(float(a.get("weekly_change_pct") or 0)) * 0.35,
                "volatility_observation_count": 20,
                "daily_returns_252d": dict(
                    a.get("daily_returns_252d") or a.get("daily_returns_60d") or {}
                ),
                "price_updated_at": a.get("price_updated_at"),
            }
            for a in _ASSETS
        ]

    async def save_signals(self, signals: list[dict]) -> list[dict]:
        yayinlanan = []
        for sig in signals:
            kayit = {**sig, "id": len(_SIGNALS) + 1}
            _SIGNALS.append(kayit)
            if sig.get("published"):
                yayinlanan.append(dict(kayit))
        return yayinlanan

    async def autonomous_users(self) -> list[dict]:
        sonuc = []
        for user in _USERS:
            portfolio = _default_portfolio(user["id"])
            if not portfolio:
                continue
            hesap = next((c for c in _CASH_ACCOUNTS if c["portfolio_id"] == portfolio["id"]), None)
            if not hesap:
                continue
            limitler = await self.get_limits(user["id"])
            if not limitler["autonomous_enabled"]:
                continue
            deger = sum(
                float(h["quantity"])
                * float(_asset(h["asset_id"])["current_price"])
                * _fx_rate(_asset(h["asset_id"])["currency"])
                for h in _PORTFOLIO_ASSETS
                if h["portfolio_id"] == portfolio["id"]
            )
            sonuc.append(
                {
                    "user_id": user["id"],
                    "risk_tolerance": user.get("risk_tolerance"),
                    "portfolio_id": portfolio["id"],
                    "available_balance": hesap["available_balance"],
                    "portfolio_value_try": deger,
                    **limitler,
                }
            )
        return sonuc

    async def user_context(self, user_id: int) -> dict | None:
        user = next((u for u in _USERS if int(u["id"]) == user_id), None)
        portfolio = _default_portfolio(user_id)
        if user is None or portfolio is None:
            return None
        hesap = next((c for c in _CASH_ACCOUNTS if c["portfolio_id"] == portfolio["id"]), None)
        if hesap is None:
            return None
        limitler = await self.get_limits(user_id)
        deger = sum(
            float(h["quantity"])
            * float(_asset(h["asset_id"])["current_price"])
            * _fx_rate(_asset(h["asset_id"])["currency"])
            for h in _PORTFOLIO_ASSETS
            if h["portfolio_id"] == portfolio["id"]
        )
        return {
            "user_id": user_id,
            "risk_tolerance": user.get("risk_tolerance"),
            "portfolio_id": portfolio["id"],
            "available_balance": hesap["available_balance"],
            "portfolio_value_try": deger,
            "allowed_asset_classes": limitler["allowed_asset_classes"],
        }

    async def holdings_map(self, portfolio_id: int) -> dict[int, float]:
        return {
            int(h["asset_id"]): float(h["quantity"])
            for h in _PORTFOLIO_ASSETS
            if h["portfolio_id"] == portfolio_id and float(h["quantity"]) > 0
        }

    async def get_basket_state(self, user_id: int, goal: str) -> dict | None:
        state = _BASKET_STATES.get((user_id, goal))
        return dict(state) if state else None

    async def upsert_basket_state(self, user_id: int, goal: str, state: dict) -> dict:
        row = {"user_id": user_id, "goal": goal, **state}
        _BASKET_STATES[(user_id, goal)] = row
        return dict(row)

    async def daily_stats(self, user_id: int) -> dict:
        bugun = datetime.now(timezone.utc).date().isoformat()
        kendi = [
            r
            for r in _RECOMMENDATIONS
            if r["user_id"] == user_id and str(r["created_at"])[:10] == bugun
        ]
        return {
            "count": len(kendi),
            "amount": sum(float(r["estimated_amount"]) for r in kendi),
        }

    async def open_recommendation_asset_ids(self, user_id: int) -> list[int]:
        return [
            r["asset_id"]
            for r in _RECOMMENDATIONS
            if r["user_id"] == user_id and r["status"] in {"PUBLISHED", "VIEWED", "APPROVED"}
        ]

    async def create_recommendation(self, row: dict) -> dict:
        asset = _asset(row["asset_id"])
        kayit = {
            **row,
            "id": len(_RECOMMENDATIONS) + 1,
            "status": "PUBLISHED",
            "rejection_reason": None,
            "order_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "viewed_at": None,
            "decided_at": None,
            "asset_symbol": asset["symbol"],
            "asset_name": asset["name"],
            "asset_class": asset["asset_class"],
        }
        _RECOMMENDATIONS.append(kayit)
        # SQL tarafinda bu yazim oneriyle AYNI transaction icindedir;
        # cagri noktasi ayni tutulur ki iki uygulama ayni olaylari uretsin.
        user = next((u for u in _USERS if u["id"] == kayit["user_id"]), None)
        _NOTIFICATION_OUTBOX.append(
            {
                "id": len(_NOTIFICATION_OUTBOX) + 1,
                "user_id": kayit["user_id"],
                "order_id": None,
                "event_type": "RECOMMENDATION_CREATED",
                "channel": "EMAIL",
                "recipient": (user or {}).get("email", ""),
                "payload": {
                    "symbol": asset["symbol"],
                    "asset_name": asset["name"],
                    "side": kayit["side"],
                    "quantity": kayit["quantity"],
                    "reference_price": kayit["reference_price"],
                    "estimated_amount": kayit["estimated_amount"],
                    "confidence": kayit["confidence"],
                    "rationale": kayit["rationale"],
                },
                "status": "PENDING",
                "attempts": 0,
                "last_error": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "processed_at": None,
            }
        )
        return dict(kayit)

    async def list_recommendations(
        self, user_id: int, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        rows = [
            dict(r)
            for r in _RECOMMENDATIONS
            if r["user_id"] == user_id and (status is None or r["status"] == status)
        ]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return rows[:limit]

    async def counts_by_status(self, user_id: int) -> dict:
        sayac: dict[str, int] = {}
        for r in _RECOMMENDATIONS:
            if r["user_id"] == user_id:
                sayac[r["status"]] = sayac.get(r["status"], 0) + 1
        return sayac

    async def get_recommendation(self, user_id: int, recommendation_id: int) -> dict | None:
        row = next(
            (
                r
                for r in _RECOMMENDATIONS
                if r["id"] == recommendation_id and r["user_id"] == user_id
            ),
            None,
        )
        return dict(row) if row else None

    def _find(self, user_id: int, rid: int) -> dict | None:
        return next(
            (r for r in _RECOMMENDATIONS if r["id"] == rid and r["user_id"] == user_id), None
        )

    async def mark_viewed(self, user_id: int, recommendation_id: int) -> dict | None:
        row = self._find(user_id, recommendation_id)
        if row and row["status"] == "PUBLISHED":
            row["status"] = "VIEWED"
            row["viewed_at"] = datetime.now(timezone.utc).isoformat()
        return dict(row) if row else None

    async def reject(self, user_id: int, recommendation_id: int, reason: str) -> dict:
        row = self._find(user_id, recommendation_id)
        if not row or row["status"] not in {"PUBLISHED", "VIEWED"}:
            raise BusinessRuleError("Bu oneri artik reddedilemez.")
        row.update(
            status="REJECTED",
            rejection_reason=reason,
            decided_at=datetime.now(timezone.utc).isoformat(),
        )
        return dict(row)

    async def attach_order(self, user_id: int, recommendation_id: int, order_id: int) -> dict:
        row = self._find(user_id, recommendation_id)
        if not row or row.get("order_id") is not None:
            raise BusinessRuleError("Bu oneri zaten bir emre donusmus.")
        if row["status"] not in {"PUBLISHED", "VIEWED", "APPROVED"}:
            raise BusinessRuleError("Bu oneri artik onaylanamaz.")
        row.update(
            status="CONVERTED",
            order_id=order_id,
            decided_at=datetime.now(timezone.utc).isoformat(),
        )
        return dict(row)

    async def expire_due(self, now=None) -> int:
        # ISO METIN karsilastirmasi YAPILMAZ: "+00:00" ve "Z" gibi farkli
        # ofset yazimlari ayni ani temsil etse de metin olarak farkli siralanir.
        an = now or datetime.now(timezone.utc)
        sayi = 0
        for r in _RECOMMENDATIONS:
            if r["status"] not in {"PUBLISHED", "VIEWED"}:
                continue
            son = _to_datetime(r["expires_at"])
            if son is not None and son <= an:
                r["status"] = "EXPIRED"
                sayi += 1
        return sayi

    async def halt_open(self, reason: str) -> int:
        sayi = 0
        for r in _RECOMMENDATIONS:
            if r["status"] in {"PUBLISHED", "VIEWED"}:
                r["status"] = "HALTED"
                sayi += 1
        return sayi

    async def log_audit(self, record: dict) -> None:
        _REC_AUDIT.append(
            {
                **record,
                "id": len(_REC_AUDIT) + 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )


class InMemoryRagRepository:
    async def search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
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
            # ISO "YYYY-AA-GG" formatinda leksikografik karsilastirma SQL
            # tarafindaki `d.tarih >= :date_from` ile ayni sonucu verir.
            if date_from and chunk["tarih"] < date_from:
                continue
            if date_to and chunk["tarih"] > date_to:
                continue

            haystack = _normalize(f"{chunk['baslik']} {chunk['content']} {chunk['sirket'] or ''}")
            hits = sum(1 for term in terms if term in haystack)
            if not hits:
                continue
            rows.append({**chunk, "score": round(hits / max(len(terms), 1), 3)})

        rows.sort(key=lambda r: r["score"], reverse=True)
        return rows[:top_k]

    async def list_news(self, limit: int = 20, kategori: str | None = None) -> list[dict]:
        # _RAG_CHUNKS chunk-bazli oldugu icin doc_id'ye gore tekillestiriyoruz
        # (bulten sayfasi makale ister, chunk degil).
        seen: set[str] = set()
        rows: list[dict] = []
        for chunk in _RAG_CHUNKS:
            doc_id = chunk["doc_id"]
            if doc_id in seen:
                continue
            if kategori and chunk.get("kategori") != kategori:
                continue
            seen.add(doc_id)
            rows.append(
                {
                    "id": chunk["chunk_id"],
                    "baslik": chunk["baslik"],
                    "sirket": chunk["sirket"],
                    "symbol": chunk["symbol"],
                    "tarih": chunk["tarih"],
                    "tip": chunk["tip"],
                    "kategori": chunk.get("kategori"),
                    "kaynak_url": None,
                    "raw_text": chunk["content"],
                    "image_url": chunk.get("image_url"),
                }
            )
        rows.sort(key=lambda r: r["tarih"] or "", reverse=True)
        return rows[:limit]

    async def set_news_image(self, document_id: int, image_url: str) -> None:
        for chunk in _RAG_CHUNKS:
            if chunk["chunk_id"] == document_id:
                chunk["image_url"] = image_url

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """Bellek ici veride embedding YOKTUR; `search()`'e trivial delegate."""
        return await self.search(
            query, top_k=top_k, sirket=sirket, tip=tip, date_from=date_from, date_to=date_to
        )


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

    async def message_owner_id(self, message_id: int) -> int | None:
        for message in self._messages:
            if message["id"] == message_id:
                for session in self._sessions:
                    if session["id"] == message["session_id"]:
                        return int(session["user_id"])
        return None


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


class InMemoryLeadRepository:
    """Lead motoru - DB yokken devreye giren yedek.

    `claim_email_contact`'teki "bugun zaten var mi" kontrolu, SQL
    tarafindaki kismi unique index'in (`lead_contacts_gunluk_uidx`)
    bellek ici karsiligidir.
    """

    async def list_lead_signals(self) -> list[dict]:
        return _lead_signals()

    async def last_contacted_map(self, cooldown_days: int) -> dict[int, datetime]:
        sinir = _now() - timedelta(days=cooldown_days)
        sonuc: dict[int, datetime] = {}
        for contact in _LEAD_CONTACTS:
            if (
                contact["channel"] != "EMAIL"
                or contact["status"] != "SENT"
                or contact["created_at"] < sinir
            ):
                continue
            mevcut = sonuc.get(contact["user_id"])
            if mevcut is None or contact["created_at"] > mevcut:
                sonuc[contact["user_id"]] = contact["created_at"]
        return sonuc

    async def start_scan(self, trigger: str) -> int:
        global _next_scan_id
        scan_id = _next_scan_id
        _next_scan_id += 1
        _LEAD_SCANS.append(
            {
                "id": scan_id,
                "started_at": _now(),
                "finished_at": None,
                "trigger": trigger,
                "scanned_count": 0,
                "bsd_count": 0,
                "autonomous_count": 0,
                "excluded_count": 0,
                "emailed_count": 0,
                "error": None,
            }
        )
        return scan_id

    async def finish_scan(
        self, scan_id: int, counts: dict[str, int], error: str | None = None
    ) -> None:
        for scan in _LEAD_SCANS:
            if scan["id"] == scan_id:
                scan["finished_at"] = _now()
                scan.update(
                    {
                        "scanned_count": counts.get("scanned_count", 0),
                        "bsd_count": counts.get("bsd_count", 0),
                        "autonomous_count": counts.get("autonomous_count", 0),
                        "excluded_count": counts.get("excluded_count", 0),
                        "emailed_count": counts.get("emailed_count", 0),
                        "error": error,
                    }
                )
                return

    async def latest_scan(self) -> dict | None:
        bitmis = [s for s in _LEAD_SCANS if s["finished_at"] is not None]
        if not bitmis:
            return None
        return dict(max(bitmis, key=lambda s: s["started_at"]))

    async def minutes_since_last_scan(self) -> float | None:
        son = await self.latest_scan()
        if son is None:
            return None
        return (_now() - son["finished_at"]).total_seconds() / 60

    async def record_decision(self, scan_id: int, entry: dict) -> None:
        _LEAD_QUEUE_ENTRIES.append({"scan_id": scan_id, "created_at": _now(), **entry})

    async def claim_email_contact(
        self, user_id: int, scan_id: int, to_email: str, subject: str
    ) -> int | None:
        global _next_contact_id
        bugun = _now().date()
        for contact in _LEAD_CONTACTS:
            if (
                contact["user_id"] == user_id
                and contact["channel"] == "EMAIL"
                and contact["status"] == "SENT"
                and contact["created_at"].date() == bugun
            ):
                return None
        contact_id = _next_contact_id
        _next_contact_id += 1
        _LEAD_CONTACTS.append(
            {
                "id": contact_id,
                "user_id": user_id,
                "scan_id": scan_id,
                "channel": "EMAIL",
                "status": "SENT",
                "to_email": to_email,
                "subject": subject,
                "error": None,
                "created_at": _now(),
            }
        )
        return contact_id

    async def mark_contact_failed(self, contact_id: int, error: str) -> None:
        for contact in _LEAD_CONTACTS:
            if contact["id"] == contact_id:
                contact["status"] = "FAILED"
                contact["error"] = error
                return

    async def mark_contact_skipped(self, contact_id: int) -> None:
        for contact in _LEAD_CONTACTS:
            if contact["id"] == contact_id:
                contact["status"] = "SKIPPED"
                return

    async def list_queue(self, decision: str, limit: int = 100) -> list[dict]:
        # SQL tarafiyla ayni: yarim kalmis (hatali) tarama ekrani
        # BOSALTMAMALI, son SAGLAM tarama gorunmeye devam eder.
        saglam = [s for s in _LEAD_SCANS if s["finished_at"] is not None and s["error"] is None]
        if not saglam:
            return []
        son = max(saglam, key=lambda s: s["started_at"])
        rows = [
            e
            for e in _LEAD_QUEUE_ENTRIES
            if e["scan_id"] == son["id"] and e["decision"] == decision
        ]
        rows.sort(key=lambda e: e.get("score", 0), reverse=True)

        son_gorusmeler = _son_gorusmeler()
        sonuc = []
        for row in rows[:limit]:
            user = next((u for u in _USERS if u["id"] == row["user_id"]), None)
            if user is None:
                continue
            gorusme = son_gorusmeler.get(row["user_id"]) or {}
            sonuc.append(
                {
                    **row,
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "email": user["email"],
                    "phone_number": user.get("phone_number"),
                    "birth_date": user.get("birth_date"),
                    "tckn_last4": user.get("tckn_last4"),
                    "registered_at": user.get("created_at"),
                    "call_outcome": gorusme.get("outcome"),
                    "call_outcome_at": gorusme.get("created_at"),
                }
            )
        return sonuc

    async def list_emailed(self, days: int, limit: int = 100) -> list[dict]:
        sinir = _now() - timedelta(days=days)
        # Kullanici basina EN SON mail kaydi (SQL'deki DISTINCT ON karsiligi).
        son_temaslar: dict[int, dict] = {}
        for contact in _LEAD_CONTACTS:
            if (
                contact["channel"] != "EMAIL"
                or contact["status"] != "SENT"
                or contact["created_at"] < sinir
            ):
                continue
            mevcut = son_temaslar.get(contact["user_id"])
            if mevcut is None or contact["created_at"] > mevcut["created_at"]:
                son_temaslar[contact["user_id"]] = contact

        son_gorusmeler = _son_gorusmeler()
        sonuc = []
        for contact in sorted(son_temaslar.values(), key=lambda c: c["created_at"], reverse=True)[
            :limit
        ]:
            user = next((u for u in _USERS if u["id"] == contact["user_id"]), None)
            if user is None:
                continue
            gorusme = son_gorusmeler.get(contact["user_id"]) or {}
            karar = next(
                (
                    e
                    for e in _LEAD_QUEUE_ENTRIES
                    if e["scan_id"] == contact.get("scan_id") and e["user_id"] == contact["user_id"]
                ),
                {},
            )
            sonuc.append(
                {
                    "user_id": user["id"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "email": user["email"],
                    "phone_number": user.get("phone_number"),
                    "birth_date": user.get("birth_date"),
                    "tckn_last4": user.get("tckn_last4"),
                    "registered_at": user.get("created_at"),
                    "decision": "AUTONOMOUS",
                    "exclusion_reason": None,
                    "score": karar.get("score", 0),
                    "score_components": karar.get("score_components", {}),
                    "reasons": karar.get("reasons", []),
                    "total_value_try": karar.get("total_value_try", 0),
                    "monthly_income": karar.get("monthly_income", 0),
                    "likit_para": karar.get("likit_para", 0),
                    "days_since_activity": karar.get("days_since_activity"),
                    "created_at": contact["created_at"],
                    "call_outcome": gorusme.get("outcome"),
                    "call_outcome_at": gorusme.get("created_at"),
                }
            )
        return sonuc

    async def record_call_outcome(
        self, user_id: int, advisor_id: int | None, outcome: str, note: str | None
    ) -> None:
        _LEAD_CALL_OUTCOMES.append(
            {
                "user_id": user_id,
                "advisor_id": advisor_id,
                "outcome": outcome,
                "note": note,
                "created_at": _now(),
            }
        )

    async def latest_call_outcomes(self) -> dict[int, dict]:
        return {
            user_id: {"outcome": kayit["outcome"], "created_at": kayit["created_at"]}
            for user_id, kayit in _son_gorusmeler().items()
        }


#: `db/migrations/018_economic_events.sql` + `019_economic_events_saat.sql`
#: ile AYNI 7 satir - DB'siz modda da Turkiye'ye ozel ekonomik olaylar
#: gorunsun diye (bkz. dosyanin ust yorumu). Saatler resmi/yerlesik
#: aciklama saatleridir: TCMB PPK karari 14:00'te, TUIK enflasyon verisi
#: 10:00'da aciklanir (Turkiye saati).
_ECONOMIC_EVENTS: list[dict] = [
    {
        "event_date": date(2026, 9, 10),
        "event_time": "14:00",
        "country": "TR",
        "event_name": "TCMB PPK Faiz Kararı",
        "importance": "high",
        "source": "TCMB",
        "expected": None,
        "actual": None,
        "previous": None,
    },
    {
        "event_date": date(2026, 10, 22),
        "event_time": "14:00",
        "country": "TR",
        "event_name": "TCMB PPK Faiz Kararı",
        "importance": "high",
        "source": "TCMB",
        "expected": None,
        "actual": None,
        "previous": None,
    },
    {
        "event_date": date(2026, 12, 10),
        "event_time": "14:00",
        "country": "TR",
        "event_name": "TCMB PPK Faiz Kararı",
        "importance": "high",
        "source": "TCMB",
        "expected": None,
        "actual": None,
        "previous": None,
    },
    {
        "event_date": date(2026, 9, 3),
        "event_time": "10:00",
        "country": "TR",
        "event_name": "TÜİK Enflasyon (TÜFE) Açıklaması",
        "importance": "medium",
        "source": "TÜİK",
        "expected": None,
        "actual": None,
        "previous": None,
    },
    {
        "event_date": date(2026, 10, 3),
        "event_time": "10:00",
        "country": "TR",
        "event_name": "TÜİK Enflasyon (TÜFE) Açıklaması",
        "importance": "medium",
        "source": "TÜİK",
        "expected": None,
        "actual": None,
        "previous": None,
    },
    {
        "event_date": date(2026, 11, 3),
        "event_time": "10:00",
        "country": "TR",
        "event_name": "TÜİK Enflasyon (TÜFE) Açıklaması",
        "importance": "medium",
        "source": "TÜİK",
        "expected": None,
        "actual": None,
        "previous": None,
    },
    {
        "event_date": date(2026, 12, 3),
        "event_time": "10:00",
        "country": "TR",
        "event_name": "TÜİK Enflasyon (TÜFE) Açıklaması",
        "importance": "medium",
        "source": "TÜİK",
        "expected": None,
        "actual": None,
        "previous": None,
    },
]


class InMemoryEconomicCalendarRepository:
    async def list_events(self, start: date, end: date) -> list[dict]:
        return sorted(
            (dict(e) for e in _ECONOMIC_EVENTS if start <= e["event_date"] <= end),
            key=lambda e: e["event_date"],
        )


_TR_TRANSLATION = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")


def _normalize(text: str) -> str:
    return text.translate(_TR_TRANSLATION).lower()


def _flatten(record: dict) -> dict:
    """Denetim kaydini JSON'a uygun degerlere cevirir."""
    return {
        k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
        for k, v in record.items()
    }


# --- sans yatirimda (oyun) ---------------------------------------------------
# `db/v5_schema_and_data.sql` 7B bolumundeki tohum veriyle BIREBIR AYNI
# metinler (frontend/src/models/oyun.ts CHEAT_SHEET / QUESTIONS ile de ayni).
# Rakip simulasyonu (isim/skor/yuzde) icin veri YOK - bkz. base.py::ContestRepository.

_TOPICS: list[dict] = [
    {
        "id": 1,
        "title_tr": "Bileşik faiz",
        "title_en": "Compound interest",
        "body_tr": (
            "Kazanılan faiz anaparaya eklenir ve yeniden faiz getirir. Erken başlamak "
            "süreyi en değerli girdi hâline getirir."
        ),
        "body_en": (
            "Interest earned is added to the principal and starts earning interest "
            "itself. Starting early makes time your most valuable asset."
        ),
    },
    {
        "id": 2,
        "title_tr": "Enflasyon ve alım gücü",
        "title_en": "Inflation and purchasing power",
        "body_tr": (
            "Fiyatlar sürekli yükselir, aynı para zamanla daha az şey alır. Getiri "
            "enflasyonun altında kalırsa reel olarak kayıp vardır."
        ),
        "body_en": (
            "Prices keep rising, so the same money buys less over time. If your return "
            "falls below inflation, you lose value in real terms."
        ),
    },
    {
        "id": 3,
        "title_tr": "Çeşitlendirme",
        "title_en": "Diversification",
        "body_tr": (
            "Birikimi farklı varlıklara dağıtmak tek bir varlığın kötü gitmesinin "
            "etkisini azaltır. Aynı sektördeki varlıklar aynı şoklara birlikte maruz "
            "kalır."
        ),
        "body_en": (
            "Spreading your savings across different assets reduces the impact of any "
            "single asset performing poorly. Assets in the same sector are exposed to "
            "the same shocks together."
        ),
    },
    {
        "id": 4,
        "title_tr": "Risk ve getiri",
        "title_en": "Risk and return",
        "body_tr": (
            "Yüksek getiri kural olarak yüksek belirsizlikle gelir. Risksiz ve yüksek "
            "getiri bir arada vaat ediliyorsa risk muhtemelen gizlenmiştir."
        ),
        "body_en": (
            "Higher returns generally come with higher uncertainty. If risk-free and "
            "high returns are promised together, the risk is probably being hidden."
        ),
    },
    {
        "id": 5,
        "title_tr": "Acil durum fonu",
        "title_en": "Emergency fund",
        "body_tr": (
            "Beklenmedik giderlerde borçlanmadan dayanmayı sağlayan rezervdir. İhtiyaç "
            "anında hızla ve değer kaybetmeden nakde çevrilebilmelidir."
        ),
        "body_en": (
            "A reserve that lets you cover unexpected expenses without borrowing. It "
            "should be quickly convertible to cash without losing value when needed."
        ),
    },
    {
        "id": 6,
        "title_tr": "Borç ve kredi yönetimi",
        "title_en": "Debt and credit management",
        "body_tr": (
            "Asgari ödeme borcu bitirmez, kalan tutara faiz işlemeye devam eder. Ödeme "
            "geçmişi kredi notunu en çok etkileyen unsurdur."
        ),
        "body_en": (
            "Paying the minimum doesn't clear the debt — interest keeps accruing on the "
            "remaining balance. Payment history is the factor that most affects your "
            "credit score."
        ),
    },
]

_QUESTIONS: list[dict] = [
    {
        "id": 1,
        "topic_id": 1,
        "text_tr": (
            "Aynı faiz oranı ve aynı anapara ile 10 yıl yatırım yapan iki kişiden biri "
            "basit, diğeri bileşik faiz kullanıyor. Aradaki farkın temel nedeni nedir?"
        ),
        "text_en": (
            "Two people invest for 10 years with the same interest rate and the same "
            "principal — one uses simple interest, the other compound interest. What "
            "mainly causes the difference between them?"
        ),
        "options": [
            {
                "tr": "Bileşik faizde oran her yıl otomatik olarak yükseltilir",
                "en": "With compound interest, the rate automatically increases every year",
            },
            {
                "tr": "Bileşik faizde kazanılan faiz de faiz getirmeye başlar",
                "en": "With compound interest, the interest earned starts earning interest too",
            },
            {
                "tr": "Basit faizde vergi kesintisi daha yüksektir",
                "en": "With simple interest, the tax deduction is higher",
            },
            {
                "tr": "Basit faizde anapara her yıl azaltılır",
                "en": "With simple interest, the principal is reduced every year",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Bileşik faizde oran değişmez; değişen şey faiz işleyen tutardır. Kazanç "
            "anaparaya eklendikçe taban büyür ve süre uzadıkça fark hızla açılır."
        ),
        "education_note_en": (
            "With compound interest, the rate doesn't change — what changes is the "
            "amount that earns interest. As gains are added to the principal, the base "
            "grows, and the gap widens quickly over time."
        ),
        "difficulty": "orta",
        "timer_seconds": 10,
    },
    {
        "id": 2,
        "topic_id": 2,
        "text_tr": (
            "Yıllık getirisi %30 olan bir yatırım, enflasyonun %45 olduğu bir yılda ne "
            "anlama gelir?"
        ),
        "text_en": (
            "What does a 30% annual return mean for an investment in a year when "
            "inflation is 45%?"
        ),
        "options": [
            {"tr": "Reel olarak kazanç sağlanmıştır", "en": "A real gain was achieved"},
            {"tr": "Reel olarak kayıp yaşanmıştır", "en": "A real loss was incurred"},
            {"tr": "Reel getiri tam olarak sıfırdır", "en": "The real return is exactly zero"},
            {
                "tr": "Enflasyon reel getiriyi etkilemez",
                "en": "Inflation does not affect real return",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Nominal getiri enflasyonun altında kaldığında paranın miktarı artsa bile "
            "alım gücü azalır. Gerçek performans, getiriden enflasyon düşülerek ölçülür."
        ),
        "education_note_en": (
            "When the nominal return stays below inflation, purchasing power falls even "
            "though the amount of money increases. Real performance is measured by "
            "subtracting inflation from the return."
        ),
        "difficulty": "orta",
        "timer_seconds": 10,
    },
    {
        "id": 3,
        "topic_id": 3,
        "text_tr": (
            "Bir yatırımcı tüm birikimini aynı sektördeki beş farklı şirkete dağıtıyor. "
            "Bu neden tam bir çeşitlendirme sayılmaz?"
        ),
        "text_en": (
            "An investor spreads all their savings across five different companies in "
            "the same sector. Why doesn't this count as full diversification?"
        ),
        "options": [
            {
                "tr": "Beş varlık çeşitlendirme için yetersiz sayıdadır",
                "en": "Five assets are not enough for diversification",
            },
            {
                "tr": "Aynı sektördeki varlıklar benzer risklerden birlikte etkilenir",
                "en": "Assets in the same sector are affected together by similar risks",
            },
            {
                "tr": "Çeşitlendirme yalnızca farklı ülkelerde yapılabilir",
                "en": "Diversification can only be done across different countries",
            },
            {
                "tr": "Hisse senetleri çeşitlendirmeye uygun değildir",
                "en": "Stocks are not suitable for diversification",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Çeşitlendirmenin işe yaraması için varlıkların birlikte hareket etmemesi "
            "gerekir. Aynı sektör aynı şoklara maruz kaldığı için sayı artsa da risk "
            "yeterince dağılmaz."
        ),
        "education_note_en": (
            "For diversification to work, assets shouldn't move together. Since the same "
            "sector is exposed to the same shocks, risk isn't spread enough even if the "
            "number of holdings increases."
        ),
        "difficulty": "zor",
        "timer_seconds": 10,
    },
    {
        "id": 4,
        "topic_id": 4,
        "text_tr": (
            '"Garantili, risksiz, aylık %20 getiri" vaat eden bir yatırım teklifi için '
            "aşağıdakilerden hangisi doğrudur?"
        ),
        "text_en": (
            "Which of the following is true for an investment offer promising "
            '"guaranteed, risk-free, 20% monthly return"?'
        ),
        "options": [
            {
                "tr": "Getirisi yüksek olduğu için öncelikli tercih edilmelidir",
                "en": "It should be preferred first because its return is high",
            },
            {
                "tr": "Risk ve getiri ilişkisine aykırıdır, riski gizlenmiş olabilir",
                "en": "It contradicts the risk-return relationship; the risk may be hidden",
            },
            {
                "tr": "Kısa vadede risksiz, uzun vadede risklidir",
                "en": "It's risk-free in the short term but risky in the long term",
            },
            {
                "tr": "Faiz oranı sabitse risk otomatik olarak ortadan kalkar",
                "en": "If the interest rate is fixed, the risk automatically disappears",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Yüksek getiri kural olarak yüksek belirsizlikle gelir. Risksiz ve yüksek "
            "getiri bir arada vaat ediliyorsa, risk ortadan kalkmamıştır; yalnızca "
            "gösterilmemektedir."
        ),
        "education_note_en": (
            "High returns generally come with high uncertainty. If risk-free and high "
            "returns are promised together, the risk hasn't disappeared — it's simply "
            "not being shown."
        ),
        "difficulty": "kolay",
        "timer_seconds": 10,
    },
    {
        "id": 5,
        "topic_id": 5,
        "text_tr": "Acil durum fonu için aşağıdaki saklama biçimlerinden hangisi en uygundur?",
        "text_en": "Which of the following storage methods is most suitable for an emergency fund?",
        "options": [
            {
                "tr": "Beş yıl vadeli, erken çıkışta ceza uygulanan bir üründe",
                "en": "A 5-year term product with an early-withdrawal penalty",
            },
            {
                "tr": "Kısa sürede nakde çevrilebilen likit bir araçta",
                "en": "A liquid instrument that can be converted to cash quickly",
            },
            {
                "tr": "Uzun vadede en çok kazandıran yüksek riskli varlıkta",
                "en": "A high-risk asset with the best long-term returns",
            },
            {
                "tr": "Satışı haftalar sürebilen fiziksel bir varlıkta",
                "en": "A physical asset that can take weeks to sell",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Acil durum fonunun amacı kazanç değil erişilebilirliktir. İhtiyaç anında "
            "beklemeden ve değer kaybetmeden çekilebilmesi gerekir."
        ),
        "education_note_en": (
            "The purpose of an emergency fund is accessibility, not return. It should be "
            "withdrawable instantly and without losing value when needed."
        ),
        "difficulty": "kolay",
        "timer_seconds": 10,
    },
    {
        "id": 6,
        "topic_id": 6,
        "text_tr": (
            "Kredi kartı ekstresinde yalnızca asgari tutarı ödeyen bir kullanıcı için "
            "aşağıdakilerden hangisi doğrudur?"
        ),
        "text_en": (
            "Which of the following is true for a user who only pays the minimum amount "
            "on their credit card statement?"
        ),
        "options": [
            {
                "tr": "Kalan borç faizsiz olarak bir sonraki aya devreder",
                "en": "The remaining debt carries over to next month interest-free",
            },
            {
                "tr": "Ödenmeyen tutara faiz işler ve borç büyümeye devam eder",
                "en": "Interest accrues on the unpaid amount and the debt keeps growing",
            },
            {
                "tr": "Kart limiti otomatik olarak yükseltilir",
                "en": "The card limit is automatically increased",
            },
            {
                "tr": "O ay yapılan tüm harcamalar iptal edilir",
                "en": "All purchases made that month are cancelled",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Asgari ödeme kartın kapanmasını önler ama borcu bitirmez. Kalan tutara akdi "
            "faiz işler; her ay tekrarlandığında borç bileşik biçimde büyür."
        ),
        "education_note_en": (
            "The minimum payment keeps the card from defaulting, but it doesn't clear "
            "the debt. Contractual interest accrues on the remaining amount; if repeated "
            "every month, the debt grows compound."
        ),
        "difficulty": "kolay",
        "timer_seconds": 10,
    },
    {
        "id": 7,
        "topic_id": None,
        "text_tr": "50/30/20 bütçe kuralında yüzde 20'lik dilim neyi ifade eder?",
        "text_en": "In the 50/30/20 budget rule, what does the 20% portion represent?",
        "options": [
            {"tr": "Zorunlu giderleri", "en": "Essential expenses"},
            {"tr": "Birikim ve borç kapatmayı", "en": "Savings and debt repayment"},
            {"tr": "Kişisel harcamaları", "en": "Personal spending"},
            {"tr": "Vergi ve sigorta ödemelerini", "en": "Tax and insurance payments"},
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Kuralda gelirin yarısı zorunlu ihtiyaçlara, yüzde 30'u isteklere, yüzde "
            "20'si birikime ve borç kapatmaya ayrılır. Birikimi önce ayırmak, kalanla "
            "yaşamayı kolaylaştırır."
        ),
        "education_note_en": (
            "Under the rule, half of income goes to essential needs, 30% to wants, and "
            "20% to savings and debt repayment. Setting savings aside first makes it "
            "easier to live on the rest."
        ),
        "difficulty": "kolay",
        "timer_seconds": 10,
    },
    {
        "id": 8,
        "topic_id": 6,
        "text_tr": (
            "Bir kişinin kredi notunu en olumsuz etkileyen davranış aşağıdakilerden " "hangisidir?"
        ),
        "text_en": (
            "Which of the following behaviors most negatively affects a person's credit " "score?"
        ),
        "options": [
            {"tr": "Kredi kartını hiç kullanmamak", "en": "Never using a credit card"},
            {"tr": "Ödemeleri düzenli olarak geciktirmek", "en": "Regularly making late payments"},
            {"tr": "Birden fazla bankada hesabı olmak", "en": "Having accounts at multiple banks"},
            {
                "tr": "Otomatik ödeme talimatı vermek",
                "en": "Setting up automatic payment instructions",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Kredi notunu belirleyen en ağırlıklı unsur ödeme geçmişidir. Gecikmeler "
            "kayda geçer ve sonraki kredi başvurularında hem onayı hem faiz oranını "
            "olumsuz etkiler."
        ),
        "education_note_en": (
            "Payment history is the most heavily weighted factor in a credit score. Late "
            "payments get recorded and negatively affect both approval and the interest "
            "rate on future credit applications."
        ),
        "difficulty": "orta",
        "timer_seconds": 10,
    },
    {
        "id": 9,
        "topic_id": None,
        "text_tr": (
            'Vadeli mevduatta "brüt faiz" ile "net faiz" arasındaki fark neyden ' "kaynaklanır?"
        ),
        "text_en": (
            'In a term deposit, what causes the difference between "gross interest" '
            'and "net interest"?'
        ),
        "options": [
            {
                "tr": "Bankanın uyguladığı hesap işletim ücretinden",
                "en": "The account maintenance fee charged by the bank",
            },
            {
                "tr": "Faiz gelirinden yapılan stopaj kesintisinden",
                "en": "The withholding tax deducted from interest income",
            },
            {"tr": "Enflasyon oranındaki değişimden", "en": "Changes in the inflation rate"},
            {
                "tr": "Vade sonunda uygulanan kur farkından",
                "en": "The exchange-rate difference applied at maturity",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Mevduat faizinden yasal stopaj kesilir. Ürünleri karşılaştırırken brüt oran "
            "değil, elinize geçecek net tutar dikkate alınmalıdır."
        ),
        "education_note_en": (
            "Statutory withholding tax is deducted from deposit interest. When comparing "
            "products, you should look at the net amount you'll actually receive, not "
            "the gross rate."
        ),
        "difficulty": "zor",
        "timer_seconds": 10,
    },
    {
        "id": 10,
        "topic_id": 4,
        "text_tr": (
            "Portföyünde ağırlıklı olarak hisse senedi bulunan bir yatırımcı, "
            "emekliliğine iki yıl kala ne yapmalıdır?"
        ),
        "text_en": (
            "What should an investor whose portfolio is mostly stocks do two years "
            "before retirement?"
        ),
        "options": [
            {
                "tr": "Riski artırıp getiriyi hızlandırmalıdır",
                "en": "Increase risk to accelerate returns",
            },
            {
                "tr": "Dalgalanmayı azaltmak için düşük riskli araçların payını artırmalıdır",
                "en": "Increase the share of low-risk instruments to reduce volatility",
            },
            {
                "tr": "Tüm birikimi tek bir hisseye toplamalıdır",
                "en": "Put all savings into a single stock",
            },
            {
                "tr": "Portföyü olduğu gibi bırakmalıdır, vade önemsizdir",
                "en": "Leave the portfolio as is; the time horizon doesn't matter",
            },
        ],
        "correct_index": 1,
        "education_note_tr": (
            "Yatırım ufku kısaldıkça kayıpları telafi etme süresi de azalır. Hedefe "
            "yaklaşırken portföyün risk düzeyini kademeli düşürmek yaygın bir "
            "yaklaşımdır."
        ),
        "education_note_en": (
            "As the investment horizon shortens, there's less time to recover from "
            "losses. Gradually lowering the portfolio's risk level as you approach your "
            "goal is a common approach."
        ),
        "difficulty": "orta",
        "timer_seconds": 10,
    },
]

#: Bugunku oturum - ilk 5 soru sirayla, tum konular baglanir. `contest_date`
#: her modul yuklendiginde YENIDEN hesaplanir (`_bugun()`), boylece dev
#: sunucusu gun asimini otomatik takip eder.
_CONTESTS: list[dict] = [
    {
        "id": 1,
        "contest_date": _bugun(),
        "starts_at": _now().replace(hour=20, minute=0, second=0, microsecond=0),
        "capacity_total": 1000,
        "prize_pool_points": 1_000_000,
        "question_count": 5,
        "created_at": _now(),
    }
]
_CONTEST_TOPICS: list[dict] = [
    {"id": i, "contest_id": 1, "topic_id": t["id"], "sort_order": i}
    for i, t in enumerate(_TOPICS, start=1)
]
_CONTEST_QUESTIONS: list[dict] = [
    {"id": i, "contest_id": 1, "question_id": qid, "sort_order": i}
    for i, qid in enumerate([1, 2, 3, 4, 5], start=1)
]
_next_contest_id = 2

_CONTEST_AGREEMENTS: list[dict] = []
_next_contest_agreement_id = 1

_PARTICIPATIONS: list[dict] = []
_next_participation_id = 1

_ANSWERS: list[dict] = []
_next_answer_id = 1

_PAYOUTS: list[dict] = []
_next_payout_id = 1

_DONATION_PURCHASES: list[dict] = []
_next_donation_purchase_id = 1

_USER_POWERUPS: list[dict] = []

_POWERUP_PURCHASES: list[dict] = []
_next_powerup_purchase_id = 1

#: Bir kullaniciya "gecmis gunler" hikayesi bir kez tohumlandi mi (bkz.
#: `_gecmis_gunleri_tohumla`). DEV/DEMO ONBELLEGI - gercek DB'de karsiligi YOK.
_TOHUMLANAN_KULLANICILAR: set[int] = set()

#: (kac gun once, kazandi mi, skor, elenilen soru, odul puani) - eskiden
#: yalnizca frontend'de GORUNTU icin var olan sahte "Puan gecmisi" dolgusu
#: (bkz. eski `frontend/src/models/oyun.ts::HISTORY`) artik BURADA, gercek
#: katilim+odul satirlari olarak yaziliyor ki kullanici bu puanlari GERCEKTEN
#: harcayabilsin (bkz. GOREV: magazadaki "gozuken" bakiye ile gercek bakiye
#: ayni sey olmali). Rakamlar frontend'deki halinden BIREBIR tasindi.
_GECMIS_GUNLER_SABLONU: list[tuple[int, bool, int, int | None, int]] = [
    (1, False, 260, 4, 0),
    (2, True, 905, None, 3150),
    (3, False, 340, 2, 0),
    (4, True, 810, None, 3480),
    (5, True, 720, None, 2260),
    (6, False, 180, 1, 0),
]


def _gecmis_gunleri_tohumla(user_id: int) -> None:
    """DEV/DEMO: kullanicinin cuzdaninda ilk eristiginde (henuz hic gercek
    katilimi yoksa) "gecmis gunler" hikayesini gercek `participation`/`payout`
    satirlari olarak ekler - boylece demo bos bir cuzdanla degil, dolu ve
    GERCEKTEN harcanabilir bir bakiyeyle basliyor. Yalnizca in-memory (dev)
    modda calisir; gercek veritabaninda bu tohumlama YOKTUR - gercek
    kullanicilar sifir bakiyeyle baslar."""
    global _next_participation_id, _next_payout_id

    if user_id in _TOHUMLANAN_KULLANICILAR:
        return
    _TOHUMLANAN_KULLANICILAR.add(user_id)
    if any(p["user_id"] == user_id for p in _PARTICIPATIONS):
        return  # zaten gercek gecmisi var - sahte gecmis ustune eklenmez

    for gun_once, won, score, eliminated_q, payout_points in _GECMIS_GUNLER_SABLONU:
        an = _now() - timedelta(days=gun_once)
        katilim = {
            "id": _next_participation_id,
            "contest_id": 1,
            "user_id": user_id,
            "contest_date": an.date().isoformat(),
            "registered_at": an,
            "eliminated_at_question": eliminated_q,
            "final_score": score,
            "won": won,
        }
        _PARTICIPATIONS.append(katilim)
        _next_participation_id += 1
        if payout_points:
            _PAYOUTS.append(
                {
                    "id": _next_payout_id,
                    "participation_id": katilim["id"],
                    "points_awarded": payout_points,
                    "created_at": an,
                }
            )
            _next_payout_id += 1


class InMemoryContestRepository:
    """Sans Yatirimda oyunu - DB yokken devreye giren yedek.

    Rakip simulasyonu (isim/skor/yuzde) icin veri TUTMAZ - bu katman
    yalnizca kullanicinin KENDI katilimini, cevaplarini ve cuzdanini
    tasir (bkz. base.py::ContestRepository).
    """

    async def get_active_contest(self) -> dict | None:
        bugun = _bugun()
        for contest in _CONTESTS:
            if contest["contest_date"] == bugun:
                return dict(contest)
        # DEV/DEMO: sunucu surec gece yarisini gecip RESTART OLMADAN calismaya
        # devam ederse, modul yuklenirken bir kere hesaplanan `contest_date`
        # bayatlar ve hicbir satir "bugun"e esit gelmez - "Bugun icin acik bir
        # yarisma yok" hatasi budur. Tek sabit ("bu akscamki") yarismayi
        # GUNCEL tarihe kaydirarak kendini onarir; boylece demo icin sunucuyu
        # her gun yeniden baslatmak gerekmez.
        if _CONTESTS:
            contest = _CONTESTS[0]
            contest["contest_date"] = bugun
            contest["starts_at"] = _now().replace(hour=20, minute=0, second=0, microsecond=0)
            return dict(contest)
        return None

    async def get_contest_topics(self, contest_id: int) -> list[dict]:
        by_id = {t["id"]: t for t in _TOPICS}
        links = sorted(
            (ct for ct in _CONTEST_TOPICS if ct["contest_id"] == contest_id),
            key=lambda ct: ct["sort_order"],
        )
        return [dict(by_id[link["topic_id"]]) for link in links if link["topic_id"] in by_id]

    async def get_contest_questions(self, contest_id: int) -> list[dict]:
        by_id = {q["id"]: q for q in _QUESTIONS}
        links = sorted(
            (cq for cq in _CONTEST_QUESTIONS if cq["contest_id"] == contest_id),
            key=lambda cq: cq["sort_order"],
        )
        result = []
        for link in links:
            question = by_id.get(link["question_id"])
            if question is None:
                continue
            row = dict(question)
            row["contest_question_id"] = link["id"]
            row["sort_order"] = link["sort_order"]
            result.append(row)
        return result

    async def has_agreement(self, user_id: int) -> bool:
        return any(a["user_id"] == user_id for a in _CONTEST_AGREEMENTS)

    async def create_agreement(self, user_id: int) -> None:
        global _next_contest_agreement_id
        if await self.has_agreement(user_id):
            return
        _CONTEST_AGREEMENTS.append(
            {"id": _next_contest_agreement_id, "user_id": user_id, "accepted_at": _now()}
        )
        _next_contest_agreement_id += 1

    async def count_participants(self, contest_id: int) -> int:
        return sum(1 for p in _PARTICIPATIONS if p["contest_id"] == contest_id)

    async def register_participation(self, contest_id: int, user_id: int) -> dict:
        global _next_participation_id
        bugun = _bugun()
        for p in _PARTICIPATIONS:
            if p["user_id"] == user_id and p["contest_date"] == bugun:
                raise BusinessRuleError("Bugun icin katilim hakkini zaten kullandin.")
        row = {
            "id": _next_participation_id,
            "contest_id": contest_id,
            "user_id": user_id,
            "contest_date": bugun,
            "registered_at": _now(),
            "eliminated_at_question": None,
            "final_score": 0,
            "won": False,
        }
        _PARTICIPATIONS.append(row)
        _next_participation_id += 1
        return dict(row)

    async def get_participation(self, participation_id: int) -> dict | None:
        for p in _PARTICIPATIONS:
            if p["id"] == participation_id:
                return dict(p)
        return None

    async def reset_todays_participation(self, user_id: int) -> None:
        bugun = _bugun()
        remove_ids = {
            p["id"]
            for p in _PARTICIPATIONS
            if p["user_id"] == user_id and p["contest_date"] == bugun
        }
        if not remove_ids:
            return
        _PARTICIPATIONS[:] = [p for p in _PARTICIPATIONS if p["id"] not in remove_ids]
        _ANSWERS[:] = [a for a in _ANSWERS if a["participation_id"] not in remove_ids]
        _PAYOUTS[:] = [pay for pay in _PAYOUTS if pay["participation_id"] not in remove_ids]

    async def reset_shop_purchases(self, user_id: int) -> None:
        _POWERUP_PURCHASES[:] = [r for r in _POWERUP_PURCHASES if r["user_id"] != user_id]
        _USER_POWERUPS[:] = [r for r in _USER_POWERUPS if r["user_id"] != user_id]
        _DONATION_PURCHASES[:] = [r for r in _DONATION_PURCHASES if r["user_id"] != user_id]

    async def submit_answer(
        self,
        participation_id: int,
        contest_question_id: int,
        selected_index: int | None,
        is_correct: bool,
        points_earned: int,
        elapsed_seconds: float,
    ) -> dict:
        global _next_answer_id
        row = {
            "id": _next_answer_id,
            "participation_id": participation_id,
            "contest_question_id": contest_question_id,
            "selected_index": selected_index,
            "is_correct": is_correct,
            "points_earned": points_earned,
            "elapsed_seconds": elapsed_seconds,
            "answered_at": _now(),
        }
        _ANSWERS.append(row)
        _next_answer_id += 1
        return dict(row)

    async def list_answers(self, participation_id: int) -> list[dict]:
        sort_order_by_cq = {cq["id"]: cq["sort_order"] for cq in _CONTEST_QUESTIONS}
        rows = [dict(a) for a in _ANSWERS if a["participation_id"] == participation_id]
        rows.sort(key=lambda a: sort_order_by_cq.get(a["contest_question_id"], 0))
        return rows

    async def finalize_participation(
        self,
        participation_id: int,
        won: bool,
        final_score: int,
        eliminated_at_question: int | None,
    ) -> dict:
        for p in _PARTICIPATIONS:
            if p["id"] == participation_id:
                p.update(
                    won=won, final_score=final_score, eliminated_at_question=eliminated_at_question
                )
                return dict(p)
        raise NotFoundError("Katilim bulunamadi.")

    async def create_payout(self, participation_id: int, payout_points: int) -> None:
        global _next_payout_id
        if any(p["participation_id"] == participation_id for p in _PAYOUTS):
            return
        _PAYOUTS.append(
            {
                "id": _next_payout_id,
                "participation_id": participation_id,
                "points_awarded": payout_points,
                "created_at": _now(),
            }
        )
        _next_payout_id += 1

    async def get_leaderboard(self, period: str) -> list[dict]:
        cutoff: datetime | None = None
        if period == "gunluk":
            cutoff = _now() - timedelta(days=1)
        elif period == "haftalik":
            cutoff = _now() - timedelta(days=7)
        rows = [p for p in _PARTICIPATIONS if cutoff is None or p["registered_at"] >= cutoff]
        rows = sorted(rows, key=lambda p: p["final_score"], reverse=True)
        by_user = {u["id"]: u for u in _USERS}
        result = []
        for rank, p in enumerate(rows, start=1):
            user = by_user.get(p["user_id"])
            if user is None:
                continue
            result.append(
                {
                    "rank": rank,
                    "label": f"{user['first_name']} {user['last_name']}",
                    "score": p["final_score"],
                }
            )
        return result

    async def list_participations(self, user_id: int, limit: int = 20) -> list[dict]:
        _gecmis_gunleri_tohumla(user_id)
        payout_by_participation = {p["participation_id"]: p["points_awarded"] for p in _PAYOUTS}
        rows = [p for p in _PARTICIPATIONS if p["user_id"] == user_id]
        rows.sort(key=lambda p: p["registered_at"], reverse=True)
        result = []
        for p in rows[:limit]:
            row = dict(p)
            row["points_awarded"] = payout_by_participation.get(p["id"], 0)
            result.append(row)
        return result

    async def get_points_balance(self, user_id: int) -> int:
        _gecmis_gunleri_tohumla(user_id)
        earned = sum(
            payout["points_awarded"]
            for payout in _PAYOUTS
            for p in _PARTICIPATIONS
            if p["id"] == payout["participation_id"] and p["user_id"] == user_id
        )
        spent = sum(row["price_points"] for row in _POWERUP_PURCHASES if row["user_id"] == user_id)
        spent += sum(
            row["price_points"] for row in _DONATION_PURCHASES if row["user_id"] == user_id
        )
        return earned - spent

    async def get_user_powerups(self, user_id: int) -> dict[str, int]:
        return {row["kind"]: row["quantity"] for row in _USER_POWERUPS if row["user_id"] == user_id}

    async def consume_powerup(self, user_id: int, kind: str) -> bool:
        for row in _USER_POWERUPS:
            if row["user_id"] == user_id and row["kind"] == kind and row["quantity"] > 0:
                row["quantity"] -= 1
                return True
        return False

    async def record_powerup_purchase(self, user_id: int, kind: str, price_points: int) -> None:
        global _next_powerup_purchase_id
        _POWERUP_PURCHASES.append(
            {
                "id": _next_powerup_purchase_id,
                "user_id": user_id,
                "kind": kind,
                "price_points": price_points,
                "purchased_at": _now(),
            }
        )
        _next_powerup_purchase_id += 1

        for row in _USER_POWERUPS:
            if row["user_id"] == user_id and row["kind"] == kind:
                row["quantity"] += 1
                return
        _USER_POWERUPS.append({"user_id": user_id, "kind": kind, "quantity": 1})

    async def list_powerup_purchases(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = [r for r in _POWERUP_PURCHASES if r["user_id"] == user_id]
        rows.sort(key=lambda r: r["purchased_at"], reverse=True)
        return [dict(r) for r in rows[:limit]]

    async def get_user_badges(self, user_id: int) -> list[str]:
        return [row["badge_label"] for row in _DONATION_PURCHASES if row["user_id"] == user_id]

    async def record_donation_purchase(
        self, user_id: int, donation_key: str, badge_label: str, price_points: int
    ) -> None:
        global _next_donation_purchase_id
        if any(
            row["user_id"] == user_id and row["donation_key"] == donation_key
            for row in _DONATION_PURCHASES
        ):
            return
        _DONATION_PURCHASES.append(
            {
                "id": _next_donation_purchase_id,
                "user_id": user_id,
                "donation_key": donation_key,
                "badge_label": badge_label,
                "price_points": price_points,
                "purchased_at": _now(),
            }
        )
        _next_donation_purchase_id += 1

    async def list_donation_purchases(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = [r for r in _DONATION_PURCHASES if r["user_id"] == user_id]
        rows.sort(key=lambda r: r["purchased_at"], reverse=True)
        return [dict(r) for r in rows[:limit]]
