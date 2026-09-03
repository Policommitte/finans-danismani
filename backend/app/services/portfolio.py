"""Portfoy ekrani domain servisi.

Katman kurali: `routes -> services -> repositories`. Endpoint'ler repository'yi
dogrudan cagirmaz; boylece veri kaynagi degistiginde (bellek ici -> Postgres)
ve alan adlari duzeltildiginde tek dokunulan yer burasidir.

Servis HESAP YAPMAZ: toplamlar ve yuzdeler DB view'larindan gelir (mimari v4
bolum 9.2). Burada yalnizca sozlesmeye (schemas/portfolio.py) uygun bicime
cevirme yapilir.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.core.errors import NotFoundError
from app.repositories.deps import get_portfolio_repository
from app.schemas.portfolio import (
    AllocationResponse,
    AllocationSlice,
    Holding,
    HoldingsResponse,
    PortfolioPerformancePoint,
    PortfolioPerformanceResponse,
    PortfolioSnapshotPerformanceResponse,
    PortfolioSummary,
    PortfolioValueSnapshotPoint,
    SymbolPeriodPnl,
    Transaction,
    TransactionsResponse,
)


async def ozet_getir(
    user_id: int,
    portfolio_id: int | None = None,
    *,
    include_period_changes: bool = False,
) -> PortfolioSummary:
    repository = get_portfolio_repository()
    summary, holdings = await asyncio.gather(
        repository.get_summary(user_id, portfolio_id),
        repository.get_holdings(user_id, portfolio_id),
    )
    if summary is None:
        raise NotFoundError("Portfoy ozeti bulunamadi.")

    daily_change_try = sum(float(row.get("daily_change_try") or 0) for row in holdings)
    previous_total = float(summary["total_value_try"]) - daily_change_try
    total_value_try = float(summary["total_value_try"])
    weekly_change: tuple[float | None, float | None] = (None, None)
    monthly_change: tuple[float | None, float | None] = (None, None)
    if include_period_changes:
        weekly_change, monthly_change = await donem_degisiklikleri_getir(
            user_id,
            total_value_try,
            portfolio_id,
        )

    return PortfolioSummary(
        portfolio_id=summary.get("portfolio_id"),
        holding_count=int(summary["holding_count"]),
        total_value_try=_f(summary["total_value_try"]),
        total_cost_try=_f(summary["total_cost_try"]),
        total_pnl_try=_f(summary["total_pnl_try"]),
        total_pnl_pct=_f_opt(summary.get("total_pnl_pct")),
        daily_change_try=_f(daily_change_try),
        daily_change_pct=(
            round(daily_change_try / previous_total * 100, 2) if previous_total > 0 else None
        ),
        weekly_change_try=weekly_change[0],
        weekly_change_pct=weekly_change[1],
        monthly_change_try=monthly_change[0],
        monthly_change_pct=monthly_change[1],
    )


async def donem_degisiklikleri_getir(
    user_id: int,
    current_total: float,
    portfolio_id: int | None = None,
) -> tuple[
    tuple[float | None, float | None],
    tuple[float | None, float | None],
]:
    """Haftalik ve aylik portfoy degisimlerini tek gecmis sorgusundan uretir."""
    rows = await get_portfolio_repository().get_performance_history(
        user_id,
        portfolio_id,
        hours=31 * 24,
    )
    return (
        _period_change(rows, current_total, days=7),
        _period_change(rows, current_total, days=30),
    )


async def varliklar_getir(user_id: int, portfolio_id: int | None = None) -> HoldingsResponse:
    rows = await get_portfolio_repository().get_holdings(user_id, portfolio_id)
    items = [_holding(row) for row in rows]

    return HoldingsResponse(
        items=items,
        total_value_try=round(sum(item.market_value_try for item in items), 2),
    )


async def dagilim_getir(user_id: int, portfolio_id: int | None = None) -> AllocationResponse:
    rows = await get_portfolio_repository().get_allocation(user_id, portfolio_id)
    return AllocationResponse(
        items=[
            AllocationSlice(
                asset_class=row["asset_class"],
                class_value_try=_f(row["class_value"]),
                class_pct=_f(row["class_pct"]),
            )
            for row in rows
        ]
    )


async def islemler_getir(
    user_id: int, portfolio_id: int | None = None, limit: int = 20
) -> TransactionsResponse:
    rows = await get_portfolio_repository().get_transactions(user_id, portfolio_id, limit=limit)
    return TransactionsResponse(
        items=[
            Transaction(
                id=int(row["id"]),
                symbol=row["symbol"],
                asset_name=row["asset_name"],
                transaction_type=row["transaction_type"],
                quantity=_f(row["quantity"]),
                unit_price=_f(row["unit_price"]),
                transaction_date=str(row["transaction_date"]),
            )
            for row in rows
        ],
        limit=limit,
    )


#: Donem secenekleri ve saat karsiliklari - TEK kaynak. Frontend'deki
#: dugmeler (1G/1H/1A/1Y) bu anahtarlari gonderir.
PERFORMANS_ARALIKLARI: dict[str, int] = {
    "1G": 24,
    "1H": 24 * 7,
    "1A": 24 * 30,
    "1Y": 24 * 365,
}

#: Gun ici korumalari YALNIZCA "bugun" gorunumunde uygulanir. Daha genis
#: tutulursa (orn. 1 hafta) %5 sicrama filtresi, son kapanis ile bugunku
#: canli fiyat arasindaki farkta tetiklenip haftanin tamamini atar ve 1H
#: ekrani 1G ile birebir ayni gorunur.
_GUN_ICI_SINIR_SAAT = 24

#: Bu esigin USTUNDE gunde TEK nokta doner, yani "bugun" disindaki her
#: aralik gunluk kovaya iner.
#:
#: 1 hafta da dahil: gun ici noktalar birakildiginda hafta ici gunlerin
#: kapanislari (gunde 1 nokta) ile BUGUNUN dakikalik noktalari (onlarca)
#: ayni eksene biniyor - grafik solda dumduz, sagda sikisik cikiyor ve
#: haftanin gercek seyri okunamiyordu.
_GUNLUK_KOVA_SINIR_SAAT = 24


async def performans_getir(
    user_id: int, portfolio_id: int | None = None, range_key: str = "1G"
) -> PortfolioPerformanceResponse:
    """Secilen donem icin portfoy degeri serisi + donem kar/zarari.

    IKI KORUMA yalnizca GUN ICI (<= 1 hafta) yolunda uygulanir:

    1. `portfolio_performance_valid_from`: gelistirme donemindeki bozuk
       `live_prices` kayitlarini eler. Uzun araliklarda uygulanamaz - esik
       12 gun oncesini isaret ediyor, aylik/yillik grafigi tamamen keserdi.
    2. "%5 sicrama" filtresi: ardisik iki nokta arasinda %5'ten buyuk fark
       varsa seriyi sifirlar (eski seed fiyatindan ilk gercek fiyata gecis).
       Gunluk veride BTC gibi varliklarda %5'lik gunluk hareket NORMALDIR;
       uzun aralikta uygulanirsa grafik durmadan kirpilirdi.

    Uzun araliklarda bu korumalara ihtiyac yok: veri `price_history`'den
    gelir ve o tablodaki her satir gercek piyasa verisidir (`source='api'`).
    """
    hours = PERFORMANS_ARALIKLARI.get(range_key, PERFORMANS_ARALIKLARI["1G"])
    gun_ici = hours <= _GUN_ICI_SINIR_SAAT
    gunluk_kova = hours > _GUNLUK_KOVA_SINIR_SAAT

    repository = get_portfolio_repository()
    rows = await repository.get_performance_history(
        user_id,
        portfolio_id,
        hours=hours,
        valid_from=settings.portfolio_performance_valid_from if gun_ici else None,
        gunluk=gunluk_kova,
    )

    temiz_satirlar: list[dict] = []
    for row in rows:
        value = float(row["total_value_try"] or 0)
        if gun_ici and temiz_satirlar:
            previous = float(temiz_satirlar[-1]["total_value_try"] or 0)
            if previous > 0 and abs(value / previous - 1) > 0.05:
                # Eski seed fiyatindan ilk gercek piyasa fiyatina gecis,
                # kullanici performansi degildir; yeni canli baz buradan baslar.
                temiz_satirlar = []
        temiz_satirlar.append(row)

    # Donem basi olarak GRAFIGIN ILK NOKTASI kullanilir, "now() - hours"
    # degil: penceredeki en eski fiyat kaydi genelde tam o an degildir ve
    # iki farkli baz kullanmak grafikteki degisim ile kar/zarar rakaminin
    # birbirini tutmamasina yol acardi.
    donem_basi = temiz_satirlar[0]["ts"] if temiz_satirlar else None
    pnl_satirlari = (
        await repository.get_period_pnl(user_id, portfolio_id, start_ts=donem_basi)
        if donem_basi is not None
        else []
    )

    symbol_pnl: list[SymbolPeriodPnl] = []
    toplam_kar_zarar = 0.0
    toplam_sermaye = 0.0
    for row in pnl_satirlari:
        kar_zarar, sermaye = _donem_kar_zarar(row)
        # Donem boyunca ne pozisyon ne islem varsa (cok once tamamen
        # satilmis varlik) satiri hic gostermeyiz - ekranda 0,00 TL'lik
        # anlamsiz satirlar birikirdi.
        if kar_zarar == 0 and sermaye == 0:
            continue
        toplam_kar_zarar += kar_zarar
        toplam_sermaye += sermaye
        symbol_pnl.append(
            SymbolPeriodPnl(
                symbol=row["symbol"],
                pnl_try=round(kar_zarar, 2),
                pnl_pct=round(kar_zarar / sermaye * 100, 2) if sermaye > 0 else None,
            )
        )

    benchmark_start = next(
        (
            row
            for row in temiz_satirlar
            if row.get("bist100_price") is not None and float(row["bist100_price"]) > 0
        ),
        None,
    )
    benchmark_baseline = (
        float(benchmark_start["bist100_price"]) if benchmark_start is not None else None
    )
    portfolio_baseline = (
        _f(benchmark_start["total_value_try"]) if benchmark_start is not None else 0
    )

    return PortfolioPerformanceResponse(
        points=[
            PortfolioPerformancePoint(
                ts=_iso_timestamp(row["ts"]),
                total_value_try=_f(row["total_value_try"]),
                bist100_value_try=(
                    round(portfolio_baseline * float(row["bist100_price"]) / benchmark_baseline, 2)
                    if benchmark_baseline
                    and row.get("bist100_price") is not None
                    and float(row["bist100_price"]) > 0
                    else None
                ),
            )
            for row in temiz_satirlar
        ],
        hours=hours,
        range_key=range_key,  # type: ignore[arg-type]
        change_try=round(toplam_kar_zarar, 2),
        change_pct=(
            round(toplam_kar_zarar / toplam_sermaye * 100, 2) if toplam_sermaye > 0 else None
        ),
        symbol_pnl=symbol_pnl,
    )


async def snapshot_performansi_getir(
    user_id: int, portfolio_id: int | None = None, hours: int = 24
) -> PortfolioSnapshotPerformanceResponse:
    """Hesaplanmis fiyat gecmisi yerine kaydedilmis gercek portfoy toplamlarini getirir."""
    rows = await get_portfolio_repository().get_value_snapshots(user_id, portfolio_id, hours=hours)
    return PortfolioSnapshotPerformanceResponse(
        points=[
            PortfolioValueSnapshotPoint(
                ts=_iso_timestamp(row["ts"]),
                holdings_value_try=_f(row["holdings_value_try"]),
                cash_value_try=_f(row["cash_value_try"]),
                total_value_try=_f(row["total_value_try"]),
            )
            for row in rows
        ],
        hours=hours,
    )


def _donem_kar_zarar(row: dict) -> tuple[float, float]:
    """Bir varligin donem kar/zarari ve donem basi sermayesi.

    Sermaye = donem basindaki deger + donem icinde ODENEN alim maliyeti;
    yuzde bunun uzerinden hesaplanir. Donem icinde hic para baglanmamissa
    (deger de 0'sa) yuzde anlamsizdir, o yuzden 0 doner ve cagiran taraf
    yuzdeyi None yapar.
    """
    baslangic = _f(row["baslangic_degeri"])
    alim = _f(row["alim_maliyeti"])
    kar_zarar = _f(row["bitis_degeri"]) - baslangic - alim + _f(row["satis_hasilati"])
    return kar_zarar, baslangic + alim


def _holding(row: dict) -> Holding:
    return Holding(
        symbol=row["symbol"],
        asset_name=row["asset_name"],
        asset_class=row["asset_class"],
        currency=row["currency"],
        quantity=_f(row["quantity"]),
        average_buy_price=_f(row["average_buy_price"]),
        current_price=_f(row["current_price"]),
        daily_change_pct=_f_opt(row.get("daily_change_pct")),
        daily_change_try=_f(row.get("daily_change_try")),
        daily_change_pct_try=_f_opt(row.get("daily_change_pct_try")),
        market_value_try=_f(row["market_value_try"]),
        cost_basis_try=_f(row["cost_basis_try"]),
        pnl_try=_f(row["pnl_try"]),
        pnl_pct=_f_opt(row.get("pnl_pct")),
    )


def _f(value) -> float:
    """psycopg NUMERIC kolonlari `Decimal` doner; JSON'a cevrilmeden float'a alinir."""
    return round(float(value or 0), 2)


def _iso_timestamp(value) -> str:
    """DB datetime degerini tarayicilarin guvenle okuyacagi ISO bicimine getirir."""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _f_opt(value) -> float | None:
    return None if value is None else round(float(value), 2)


def _period_change(
    rows: list[dict], current_total: float, *, days: int
) -> tuple[float | None, float | None]:
    """Guncel portfoyu donem basindaki son eksiksiz fiyat kaydiyla karsilastirir."""
    dated_rows: list[tuple[datetime, dict]] = []
    for row in rows:
        if not row.get("is_complete", True):
            continue
        timestamp = _as_datetime(row.get("ts"))
        reference_value = float(row.get("total_value_try") or 0)
        if timestamp is not None and reference_value > 0:
            dated_rows.append((timestamp, row))

    if not dated_rows:
        return None, None

    dated_rows.sort(key=lambda item: item[0])
    target = dated_rows[-1][0] - timedelta(days=days)
    reference = next(
        (row for timestamp, row in reversed(dated_rows) if timestamp <= target),
        None,
    )
    if reference is None:
        return None, None

    reference_total = float(reference["total_value_try"])
    change_try = current_total - reference_total
    return round(change_try, 2), round(change_try / reference_total * 100, 2)


def _as_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
