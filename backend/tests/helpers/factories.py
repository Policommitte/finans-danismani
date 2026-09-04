"""Domain sozlugu ureticileri.

Testler yalnizca ILGILENDIKLERI alani verir; geri kalani makul bir
varsayilanla dolar. Boylece "risk skoru yogunlasmayi nasil cezalandiriyor"
sorusunu soran bir test `currency` ya da `avg_cost` yazmak zorunda kalmaz -
ve o alanlar degistiginde 40 test birden bozulmaz.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def holding(
    symbol: str = "THYAO",
    *,
    asset_class: str = "STOCK",
    market_value_try: float = 100_000.0,
    quantity: float = 100.0,
    **ekstra,
) -> dict:
    """`PortfolioRepository.get_holdings` satiri."""
    # `market_value_try` BILEREK `None` verilebilir - repo satirlarinda
    # gorulen bir durum ve risk servisinin onu tolere ettigi test ediliyor.
    birim = (market_value_try or 0.0) / quantity if quantity else 0.0
    satir = {
        "asset_id": abs(hash(symbol)) % 10_000,
        "symbol": symbol,
        "asset_name": symbol,
        "asset_class": asset_class,
        "quantity": quantity,
        "avg_cost": birim,
        "current_price": birim,
        "market_value_try": market_value_try,
        "currency": "TRY",
        "pnl_pct": 0.0,
        "daily_change_pct": 0.0,
    }
    satir.update(ekstra)
    return satir


def allocation(asset_class: str = "STOCK", class_pct: float = 100.0, **ekstra) -> dict:
    """`PortfolioRepository.get_allocation` satiri."""
    satir = {
        "asset_class": asset_class,
        "class_pct": class_pct,
        "class_value": class_pct * 1_000,
    }
    satir.update(ekstra)
    return satir


def asset(
    symbol: str = "THYAO",
    *,
    asset_class: str = "STOCK",
    current_price: float = 300.0,
    daily_change_pct: float | None = 0.0,
    weekly_change_pct: float | None = 0.0,
    yearly_change_pct: float | None = 0.0,
    yas_dakika: float = 0.0,
    **ekstra,
) -> dict:
    """`assets` tablosu satiri - sinyal motoru ve piyasa servisi girdisi.

    `yas_dakika` fiyatin ne kadar once guncellendigini soyler; sinyal
    motorunun bayatlik kontrolu (`max_staleness_minutes`) bunu okur.
    """
    satir = {
        "asset_id": abs(hash(symbol)) % 10_000,
        "symbol": symbol,
        "asset_name": symbol,
        "asset_class": asset_class,
        "category": asset_class,
        "currency": "TRY",
        "current_price": current_price,
        "daily_change_pct": daily_change_pct,
        "weekly_change_pct": weekly_change_pct,
        "yearly_change_pct": yearly_change_pct,
        "price_updated_at": datetime.now(timezone.utc) - timedelta(minutes=yas_dakika),
    }
    satir.update(ekstra)
    return satir


def price_point(price: float, *, gun_once: int = 0) -> dict:
    """`MarketRepository.get_history` satiri."""
    return {
        "price": price,
        "ts": datetime.now(timezone.utc) - timedelta(days=gun_once),
    }


def candle(
    *,
    ts: int | datetime = 0,
    open_: float = 100.0,
    high: float = 110.0,
    low: float = 90.0,
    close: float = 105.0,
    volume: float = 1_000.0,
) -> dict:
    """`MarketRepository.get_candles` satiri (OHLCV)."""
    return {
        "ts": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def lead_signal(
    *,
    marketing_consent: bool = True,
    email: str = "musteri@example.com",
    monthly_income: float = 90_000.0,
    likit_para: float = 250_000.0,
    total_value_try: float = 0.0,
    days_since_activity: int | None = 200,
    **ekstra,
) -> dict:
    """`v_lead_user_signals` satiri - lead kurallarinin girdisi.

    Varsayilanlar UYGUN bir lead uretir; testler tek alani bozarak o
    kuralin tetiklendigini gosterir.
    """
    satir = {
        "user_id": 1,
        "full_name": "Test Musteri",
        "marketing_consent": marketing_consent,
        "email": email,
        "monthly_income": monthly_income,
        "likit_para": likit_para,
        "total_value_try": total_value_try,
        "days_since_activity": days_since_activity,
        "holding_count": 0,
    }
    satir.update(ekstra)
    return satir
