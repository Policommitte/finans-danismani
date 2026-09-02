"""PostgreSQL implementasyonlari (`db/v5_schema_and_data.sql` semasi).

`base.py` icindeki protokolleri uygular; servis ve endpoint kodu bu dosyayi
TANIMAZ - secim `deps.py` icinde yapilir.

Neden ORM degil de duz SQL:
    Hesabin tek kaynagi VIEW'lardir (`v_holdings_valued`, `v_portfolio_summary`,
    `v_portfolio_allocation`) ve hibrit arama bir SQL fonksiyonudur
    (`rag.hybrid_search`). ORM modelleri bu hesaplari Python'a tasima cazibesi
    yaratir; ayni toplami iki yerde hesaplamak ise dashboard ile ajanin farkli
    rakam gostermesi demektir (mimari v4 bolum 9.2).

Her metot KENDI oturumunu acar: MCP tool'lari ve arka plan fiyat gorevi HTTP
istegi disindan da cagrilir, dolayisiyla oturum bir request'e baglanamaz.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.core.errors import BusinessRuleError, NotFoundError
from app.ingestion.embeddings import Embedder

logger = logging.getLogger(__name__)


class _SqlRepository:
    """Ortak oturum yonetimi."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    #: NOT: SQL metinlerinde `:param::TYPE` yazimi KULLANILMAZ - SQLAlchemy
    #: `text()` bind parametrelerini ayristirirken PostgreSQL'in `::` cast
    #: operatoruyle karisir ve "syntax error at or near :" hatasi verir.
    #: Bunun yerine `CAST(:param AS TYPE)` yazilir.

    async def _rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(text(sql), params or {})
            return [dict(row) for row in result.mappings().all()]

    async def _row(self, sql: str, params: dict[str, Any] | None = None) -> dict | None:
        rows = await self._rows(sql, params)
        return rows[0] if rows else None


class SqlUserRepository(_SqlRepository):
    async def get_by_email(self, email: str) -> dict | None:
        return await self._row(
            """
            SELECT id, first_name, last_name, email, password_hash,
                   risk_tolerance, monthly_income, onboarding_completed, has_seen_tour,
                   role, tckn_last4, birth_date, phone_number
            FROM users WHERE lower(email) = lower(:email)
            """,
            {"email": email},
        )

    async def get_by_id(self, user_id: int) -> dict | None:
        return await self._row(
            """
            SELECT id, first_name, last_name, email, risk_tolerance, monthly_income,
                   onboarding_completed, has_seen_tour, role, tckn_last4, birth_date,
                   phone_number
            FROM users WHERE id = :user_id
            """,
            {"user_id": user_id},
        )

    async def create(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        account_number: str | None = None,
    ) -> dict:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO users
                        (first_name, last_name, email, password_hash, onboarding_completed,
                         has_seen_tour, account_number)
                    VALUES (:first_name, :last_name, :email, :password_hash, false,
                            false, :account_number)
                    RETURNING id, first_name, last_name, email, risk_tolerance, monthly_income,
                              onboarding_completed, has_seen_tour, tckn_last4, birth_date,
                              phone_number
                    """
                ),
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "password_hash": password_hash,
                    "account_number": account_number,
                },
            )
            row = result.mappings().one()
            await session.commit()
            return dict(row)

    async def complete_onboarding(self, user_id: int, risk_tolerance: str) -> dict | None:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    UPDATE users
                    SET risk_tolerance = :risk_tolerance, onboarding_completed = true
                    WHERE id = :user_id
                    RETURNING id, first_name, last_name, email, risk_tolerance, monthly_income,
                              onboarding_completed, has_seen_tour, tckn_last4, birth_date,
                              phone_number
                    """
                ),
                {"user_id": user_id, "risk_tolerance": risk_tolerance},
            )
            row = result.mappings().first()
            await session.commit()
            return dict(row) if row else None

    async def mark_tour_seen(self, user_id: int) -> dict | None:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    UPDATE users
                    SET has_seen_tour = true
                    WHERE id = :user_id
                    RETURNING id, first_name, last_name, email, risk_tolerance, monthly_income,
                              onboarding_completed, has_seen_tour, tckn_last4, birth_date,
                              phone_number
                    """
                ),
                {"user_id": user_id},
            )
            row = result.mappings().first()
            await session.commit()
            return dict(row) if row else None


class SqlPortfolioRepository(_SqlRepository):
    """Portfoy verisi - hesap YAPMAZ, view'lari okur.

    `portfolio_id` verilmezse kullanicinin varsayilan portfoyu kullanilir.
    Her sorgu `user_id` filtresi tasir: baska kullanicinin portfoy id'si
    gonderilse bile satir donmez (yetkilendirme derinlemesine savunma).
    """

    async def get_default_portfolio_id(self, user_id: int) -> int | None:
        row = await self._row(
            """
            SELECT id FROM portfolios
            WHERE user_id = :user_id
            ORDER BY is_default DESC, id
            LIMIT 1
            """,
            {"user_id": user_id},
        )
        return row["id"] if row else None

    async def get_summary(self, user_id: int, portfolio_id: int | None = None) -> dict | None:
        return await self._row(
            """
            SELECT s.portfolio_id, s.holding_count,
                   s.total_value_try, s.total_cost_try,
                   s.total_pnl_try, s.total_pnl_pct
            FROM v_portfolio_summary s
            JOIN portfolios p ON p.id = s.portfolio_id
            WHERE s.user_id = :user_id
              AND (CAST(:portfolio_id AS INT) IS NULL OR s.portfolio_id = :portfolio_id)
            ORDER BY p.is_default DESC, s.portfolio_id
            LIMIT 1
            """,
            {"user_id": user_id, "portfolio_id": portfolio_id},
        )

    async def get_holdings(self, user_id: int, portfolio_id: int | None = None) -> list[dict]:
        return await self._rows(
            """
            SELECT h.portfolio_id, h.asset_id, h.symbol, h.asset_name,
                   h.asset_class, h.currency, h.quantity, h.average_buy_price,
                   h.current_price, h.daily_change_pct, h.market_value_try,
                   h.cost_basis_try, h.pnl_try, h.pnl_pct,
                   h.market_value_try - (
                       h.quantity * COALESCE(a.prev_close, a.current_price)
                       * CASE WHEN h.currency = 'TRY' THEN 1
                              ELSE COALESCE(fx.prev_close, fx.current_price, 1) END
                   ) AS daily_change_try,
                   CASE WHEN (
                       h.quantity * COALESCE(a.prev_close, a.current_price)
                       * CASE WHEN h.currency = 'TRY' THEN 1
                              ELSE COALESCE(fx.prev_close, fx.current_price, 1) END
                   ) > 0 THEN 100 * (h.market_value_try / (
                       h.quantity * COALESCE(a.prev_close, a.current_price)
                       * CASE WHEN h.currency = 'TRY' THEN 1
                              ELSE COALESCE(fx.prev_close, fx.current_price, 1) END
                   ) - 1) END AS daily_change_pct_try
            FROM v_holdings_valued h
            JOIN assets a ON a.id = h.asset_id
            LEFT JOIN assets fx ON fx.symbol = h.currency || '/TRY'
            WHERE h.user_id = :user_id
              AND h.portfolio_id = COALESCE(
                    CAST(:portfolio_id AS INT),
                    (
                        SELECT id FROM portfolios
                        WHERE user_id = :user_id
                        ORDER BY is_default DESC, id
                        LIMIT 1
                    )
                  )
            ORDER BY h.market_value_try DESC
            """,
            {"user_id": user_id, "portfolio_id": portfolio_id},
        )

    async def get_allocation(self, user_id: int, portfolio_id: int | None = None) -> list[dict]:
        return await self._rows(
            """
            SELECT a.asset_class, a.class_value, a.class_pct
            FROM v_portfolio_allocation a
            JOIN portfolios p ON p.id = a.portfolio_id
            WHERE a.user_id = :user_id
              AND a.portfolio_id = COALESCE(
                    CAST(:portfolio_id AS INT),
                    (
                        SELECT id FROM portfolios
                        WHERE user_id = :user_id
                        ORDER BY is_default DESC, id
                        LIMIT 1
                    )
                  )
            ORDER BY a.class_value DESC
            """,
            {"user_id": user_id, "portfolio_id": portfolio_id},
        )

    async def get_transactions(
        self, user_id: int, portfolio_id: int | None = None, limit: int = 20
    ) -> list[dict]:
        return await self._rows(
            """
            SELECT t.id, a.symbol, a.name AS asset_name, t.transaction_type,
                   t.quantity, t.unit_price, t.transaction_date
            FROM transactions t
            JOIN portfolios p ON p.id = t.portfolio_id
            JOIN assets     a ON a.id = t.asset_id
            WHERE p.user_id = :user_id
              AND t.portfolio_id = COALESCE(
                    CAST(:portfolio_id AS INT),
                    (
                        SELECT id FROM portfolios
                        WHERE user_id = :user_id
                        ORDER BY is_default DESC, id
                        LIMIT 1
                    )
                  )
            ORDER BY t.transaction_date DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "portfolio_id": portfolio_id, "limit": limit},
        )

    async def get_performance_history(
        self, user_id: int, portfolio_id: int | None = None, hours: int = 24
    ) -> list[dict]:
        return await self._rows(
            """
            WITH selected_portfolio AS (
                SELECT id
                FROM portfolios
                WHERE user_id = :user_id
                  AND id = COALESCE(
                        CAST(:portfolio_id AS INT),
                        (
                            SELECT id FROM portfolios
                            WHERE user_id = :user_id
                            ORDER BY is_default DESC, id
                            LIMIT 1
                        )
                      )
            ), positions AS (
                SELECT pa.asset_id, pa.quantity, a.current_price, fx.try_rate
                FROM portfolio_assets pa
                JOIN selected_portfolio sp ON sp.id = pa.portfolio_id
                JOIN assets a ON a.id = pa.asset_id
                JOIN v_fx_rates fx ON fx.currency = a.currency
            ), all_prices AS (
                SELECT ph.asset_id, ph.ts, ph.price
                FROM price_history ph
                WHERE ph.ts >= now() - make_interval(hours => :hours)
                  AND ph.ts >= :valid_from
                  AND ph.source <> 'simulated'
                UNION ALL
                SELECT lp.asset_id, lp.created_at AS ts, lp.price
                FROM live_prices lp
                WHERE lp.created_at >= now() - make_interval(hours => :hours)
                  AND lp.created_at >= :valid_from
                  AND lp.source <> 'simulated'
            ), timeline AS (
                SELECT DISTINCT ap.ts
                FROM all_prices ap
                JOIN positions p ON p.asset_id = ap.asset_id
            )
            SELECT t.ts,
                   SUM(
                       p.quantity
                       * COALESCE(h.price, p.current_price)
                       * p.try_rate
                   ) AS total_value_try,
                   BOOL_AND(h.price IS NOT NULL) AS is_complete,
                   MAX(b.price) AS bist100_price
            FROM timeline t
            CROSS JOIN positions p
            LEFT JOIN LATERAL (
                SELECT ap.price
                FROM all_prices ap
                WHERE ap.asset_id = p.asset_id
                  AND ap.ts <= t.ts
                ORDER BY ap.ts DESC
                LIMIT 1
            ) h ON TRUE
            LEFT JOIN LATERAL (
                SELECT ap.price
                FROM all_prices ap
                JOIN assets benchmark ON benchmark.id = ap.asset_id
                WHERE upper(benchmark.symbol) = 'BIST100'
                  AND ap.ts <= t.ts
                ORDER BY ap.ts DESC
                LIMIT 1
            ) b ON TRUE
            GROUP BY t.ts
            ORDER BY t.ts
            """,
            {
                "user_id": user_id,
                "portfolio_id": portfolio_id,
                "hours": hours,
                "valid_from": settings.portfolio_performance_valid_from,
            },
        )

    async def write_value_snapshots(self) -> int:
        """Her basarili fiyat turunda portfoylerin anlik toplamlarini yazar.

        Zaman kovasi kullanilmaz: iki basarili fiyat turu birbirinin uzerine
        yazmaz. Nakit, rezerve bakiye dahil edilerek snapshot anindaki
        toplamdan hesaplanir.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    WITH holdings AS (
                        SELECT p.id AS portfolio_id,
                               COALESCE(SUM(h.market_value_try), 0) AS holdings_value_try
                        FROM portfolios p
                        LEFT JOIN v_holdings_valued h ON h.portfolio_id = p.id
                        GROUP BY p.id
                    ), cash AS (
                        SELECT p.id AS portfolio_id,
                               COALESCE(SUM(
                                   (ca.available_balance + ca.reserved_balance)
                                   * CASE WHEN ca.currency = 'TRY' THEN 1
                                          ELSE COALESCE(fx.try_rate, 0) END
                               ), 0) AS cash_value_try
                        FROM portfolios p
                        LEFT JOIN cash_accounts ca ON ca.portfolio_id = p.id
                        LEFT JOIN v_fx_rates fx ON fx.currency = ca.currency
                        GROUP BY p.id
                    ), written AS (
                        INSERT INTO portfolio_value_snapshots (
                            portfolio_id, ts, holdings_value_try,
                            cash_value_try, total_value_try, source
                        )
                        SELECT h.portfolio_id,
                               now(),
                               h.holdings_value_try,
                               c.cash_value_try,
                               h.holdings_value_try + c.cash_value_try,
                               'scheduler'
                        FROM holdings h
                        JOIN cash c ON c.portfolio_id = h.portfolio_id
                        ON CONFLICT (portfolio_id, ts) DO NOTHING
                        RETURNING 1
                    )
                    SELECT COUNT(*) AS written_count FROM written
                    """
                )
            )
            count = int(result.scalar_one())
            await session.commit()
            return count

    async def get_value_snapshots(
        self, user_id: int, portfolio_id: int | None = None, hours: int = 24
    ) -> list[dict]:
        return await self._rows(
            """
            SELECT s.ts, s.holdings_value_try, s.cash_value_try, s.total_value_try
            FROM portfolio_value_snapshots s
            JOIN portfolios p ON p.id = s.portfolio_id
            WHERE p.user_id = :user_id
              AND s.portfolio_id = COALESCE(
                    CAST(:portfolio_id AS INT),
                    (
                        SELECT id FROM portfolios
                        WHERE user_id = :user_id
                        ORDER BY is_default DESC, id
                        LIMIT 1
                    )
                  )
              AND s.ts >= now() - make_interval(hours => :hours)
            ORDER BY s.ts
            """,
            {"user_id": user_id, "portfolio_id": portfolio_id, "hours": hours},
        )

    async def prune_value_snapshots(self, keep_days: int = 30) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    DELETE FROM portfolio_value_snapshots
                    WHERE ts < now() - make_interval(days => :keep_days)
                    """
                ),
                {"keep_days": keep_days},
            )
            deleted = int(result.rowcount or 0)
            await session.commit()
            return deleted


class SqlMarketRepository(_SqlRepository):
    async def list_assets(self, category: str | None = None) -> list[dict]:
        return await self._rows(
            """
            SELECT a.id, a.symbol, a.name, ac.code AS asset_class, a.currency,
                   a.current_price, a.daily_change_pct, a.weekly_change_pct,
                   a.yearly_change_pct, a.price_updated_at
            FROM assets a
            JOIN asset_categories ac ON ac.id = a.category_id
            WHERE (CAST(:category AS TEXT) IS NULL OR ac.code = :category)
            ORDER BY ac.code, a.symbol
            """,
            {"category": category.upper() if category else None},
        )

    async def get_quote(self, symbol: str) -> dict | None:
        return await self._row(
            """
            SELECT a.symbol, a.name, ac.code AS asset_class, a.currency,
                   a.current_price AS price, a.daily_change_pct, a.weekly_change_pct,
                   COALESCE(a.price_updated_at, now()) AS ts
            FROM assets a
            JOIN asset_categories ac ON ac.id = a.category_id
            WHERE upper(a.symbol) = upper(:symbol)
            """,
            {"symbol": symbol},
        )

    async def get_history(self, symbol: str, days: int = 30) -> list[dict]:
        return await self._rows(
            """
            WITH raw_points AS (
                SELECT ph.ts, ph.price, 1 AS priority
                FROM price_history ph
                JOIN assets a ON a.id = ph.asset_id
                WHERE upper(a.symbol) = upper(:symbol)
                  AND ph.ts >= now() - make_interval(days => :days)
                UNION ALL
                SELECT lp.created_at AS ts, lp.price, 2 AS priority
                FROM live_prices lp
                JOIN assets a ON a.id = lp.asset_id
                WHERE upper(a.symbol) = upper(:symbol)
                  AND lp.created_at >= now() - make_interval(days => :days)
                UNION ALL
                SELECT COALESCE(a.price_updated_at, now()) AS ts,
                       a.current_price AS price, 3 AS priority
                FROM assets a
                WHERE upper(a.symbol) = upper(:symbol)
                  AND COALESCE(a.price_updated_at, now()) >= now() - make_interval(days => :days)
            ), deduplicated AS (
                SELECT DISTINCT ON (ts) ts, price
                FROM raw_points
                ORDER BY ts, priority DESC
            )
            SELECT ts, price FROM deduplicated ORDER BY ts
            """,
            {"symbol": symbol, "days": days},
        )

    async def get_history_range(self, symbol: str, start: str, end: str) -> list[dict]:
        """Iki tarih arasi gunluk kapanis serisi (her iki uc DAHIL).

        `end` gunun kendisini de kapsasin diye `< end + 1 gun` yaziliyor:
        `ph.ts` bir zaman damgasidir, `<= :end` yazilsaydi bitis gununun gun
        ici saatleri disarida kalirdi.
        """
        return await self._rows(
            """
            SELECT ph.ts, ph.price
            FROM price_history ph
            JOIN assets a ON a.id = ph.asset_id
            WHERE upper(a.symbol) = upper(:symbol)
              AND ph.ts >= CAST(:start AS DATE)
              AND ph.ts < CAST(:end AS DATE) + INTERVAL '1 day'
            ORDER BY ph.ts
            """,
            {"symbol": symbol, "start": start, "end": end},
        )

    async def get_candles(self, symbol: str, interval: str = "5m", days: int = 5) -> list[dict]:
        return await self._rows(
            """
            SELECT mc.ts, mc.open, mc.high, mc.low, mc.close, mc.volume
            FROM market_candles mc
            JOIN assets a ON a.id = mc.asset_id
            WHERE upper(a.symbol) = upper(:symbol)
              AND mc.interval = :interval
              AND mc.ts >= now() - make_interval(days => :days)
            ORDER BY mc.ts
            """,
            {"symbol": symbol, "interval": interval, "days": days},
        )

    async def upsert_candles(self, candles: list[dict], source: str = "yahoo") -> int:
        if not candles:
            return 0
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO market_candles (
                        asset_id, interval, ts, open, high, low, close, volume, source
                    )
                    SELECT a.id, x.interval, x.ts, x.open, x.high, x.low,
                           x.close, x.volume, :source
                    FROM jsonb_to_recordset(CAST(:payload AS JSONB)) AS x(
                        symbol TEXT, interval TEXT, ts TIMESTAMPTZ,
                        open NUMERIC, high NUMERIC, low NUMERIC,
                        close NUMERIC, volume NUMERIC
                    )
                    JOIN assets a ON upper(a.symbol) = upper(x.symbol)
                    WHERE x.open > 0 AND x.high > 0 AND x.low > 0 AND x.close > 0
                    ON CONFLICT (asset_id, interval, ts) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        source = EXCLUDED.source,
                        updated_at = now()
                    """
                ),
                {"payload": _json(candles), "source": source},
            )
            await session.commit()
            return result.rowcount or 0

    async def prune_candles(self, interval: str, keep_days: int) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    DELETE FROM market_candles
                    WHERE interval = :interval
                      AND ts < now() - make_interval(days => :keep_days)
                    """
                ),
                {"interval": interval, "keep_days": keep_days},
            )
            await session.commit()
            return result.rowcount or 0

    async def get_assets_for_price_update(self) -> list[dict]:
        return await self._rows(
            """
            SELECT id AS asset_id, symbol, current_price
            FROM assets ORDER BY id
            """
        )

    async def apply_price_updates(self, updates: list[dict], write_live: bool, source: str) -> int:
        """Fiyatlari gunceller; istenirse `live_prices`'a gun ici satir yazar.

        GECMIS TABLOSUNA (`price_history`) BURADAN YAZILMAZ. 5 dakikalik
        tick'ler dogrudan oraya aksaydi tablo gunde ~4.608 satirla siserdi;
        grafikler icin gereken cozunurluk ise gunluk kapanistir. Bu yuzden
        tick'ler `live_prices`'a birikir ve gun bitiminde yalnizca gunun son
        fiyati `price_history`'ye tasinir (bkz. `close_out_day`).

        `prev_close` her tick'te ilerletilmez; saglayicinin onceki kapanisi
        varsa o deger, yoksa mevcut gun baslangic degeri korunur. Boylece
        `daily_change_pct` son tick'e gore degil gun baslangicina gore kalir.
        Gun kapanirken `close_out_day` bu degeri kesin kapanisla tazeler.

        `daily_change_pct` ve `weekly_change_pct` YENIDEN HESAPLANIR - aksi
        halde seed degerinde donar ve dashboard hep ayni yuzdeyi gosterir
        (mimari v4 bolum 8.2).

        `source` cagiran tarafindan verilir ve gercek kaynagi belirtir. Etiket
        `live_prices` uzerinden gun sonunda `price_history`'ye tasinir.
        """
        if not updates:
            return 0
        if source != "api":
            raise ValueError("yalnizca dogrulanmis 'api' fiyatlari yazilabilir")

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    WITH incoming AS (
                        SELECT (value->>'asset_id')::INT  AS asset_id,
                               (value->>'price')::NUMERIC AS price,
                               (value->>'previous_close')::NUMERIC AS previous_close
                        FROM jsonb_array_elements(CAST(:payload AS JSONB))
                    ), priced AS (
                        SELECT a.id AS asset_id,
                               v.price,
                               CASE
                                   WHEN v.previous_close > 0
                                   THEN v.previous_close
                                   WHEN (a.price_updated_at AT TIME ZONE :market_timezone)::date
                                      < (now() AT TIME ZONE :market_timezone)::date
                                     OR a.prev_close IS NULL
                                     OR a.prev_close <= 0
                                     OR ABS((a.current_price - a.prev_close) / a.prev_close) > 0.20
                                   THEN a.current_price
                                   ELSE a.prev_close
                               END AS day_open
                        FROM assets a
                        JOIN incoming v ON v.asset_id = a.id
                    )
                    UPDATE assets AS a
                    SET prev_close       = p.day_open,
                        current_price    = p.price,
                        daily_change_pct = CASE WHEN p.day_open > 0
                            THEN ROUND(((p.price - p.day_open) / p.day_open * 100)::NUMERIC, 4)
                            ELSE a.daily_change_pct END,
                        price_updated_at = now()
                    FROM priced p
                    WHERE a.id = p.asset_id
                    """
                ),
                {"payload": _json(updates), "market_timezone": settings.market_day_timezone},
            )

            if write_live:
                # Varligi olmayan asset_id'ye yazmayi FK engellerdi ve tum
                # tick'i dusururdu; JOIN ile bastan eliyoruz.
                await session.execute(
                    text(
                        """
                        INSERT INTO live_prices (asset_id, price, source, created_at)
                        SELECT a.id, v.price, :source, date_trunc('second', now())
                        FROM (SELECT
                                (value->>'asset_id')::INT  AS asset_id,
                                (value->>'price')::NUMERIC AS price
                              FROM jsonb_array_elements(CAST(:payload AS JSONB))) AS v
                        JOIN assets a ON a.id = v.asset_id
                        WHERE v.price > 0
                        """
                    ),
                    {"payload": _json(updates), "source": source},
                )

            await session.execute(
                text(
                    """
                    UPDATE assets a
                    SET weekly_change_pct = ROUND(
                            ((a.current_price - h.price) / NULLIF(h.price, 0) * 100)::NUMERIC, 4)
                    FROM (
                        SELECT DISTINCT ON (asset_id) asset_id, price
                        FROM price_history
                        WHERE ts <= now() - INTERVAL '7 days'
                        ORDER BY asset_id, ts DESC
                    ) h
                    WHERE h.asset_id = a.id
                    """
                )
            )
            await session.commit()

        return len(updates)

    # -- Gun devri ---------------------------------------------------------
    #
    # Gun siniri `settings.market_day_timezone` (Europe/Istanbul) ile
    # belirlenir; veritabani sunucusu UTC calisir. Saat dilimi SQL'e bind
    # parametresi olarak gecer, metne gomulmez.

    async def pending_close_days(self) -> list[str]:
        """Kapanisi bekleyen gunler (bugunden onceki her gun), eskiden yeniye.

        Ayri bir "kapatildi mi" tablosu YOKTUR: `live_prices`'ta gecmis bir
        gune ait satir kalmasi, o gunun henuz kapatilmadigi anlamina gelir.
        Boylece uygulama hafta sonu kapali kalsa bile acilista bekleyen tum
        gunler kendiliginden gorunur ve kapanislar geriye donuk tamamlanir.
        """
        satirlar = await self._rows(
            """
            SELECT DISTINCT
                   CAST(created_at AT TIME ZONE CAST(:tz AS TEXT) AS DATE) AS gun
            FROM live_prices
            WHERE created_at < (
                      date_trunc('day', now() AT TIME ZONE CAST(:tz AS TEXT))
                  ) AT TIME ZONE CAST(:tz AS TEXT)
            ORDER BY gun
            """,
            {"tz": settings.market_day_timezone},
        )
        return [str(satir["gun"]) for satir in satirlar]

    async def close_out_day(self, day: str) -> int:
        """Gunu kapatir: kapanisi yazar, `prev_close`'u tazeler, gunu siler.

        Uc adim TEK transaction icindedir - arada bir hata olursa hicbiri
        gerceklesmez ve gun bir sonraki tick'te yeniden denenir. SIRA
        onemlidir: once `price_history`'ye yazilir, silme en sonda yapilir.
        """
        parametreler = {"gun": day, "tz": settings.market_day_timezone}

        async with self._session_factory() as session:
            # 1) Gunun SON canli fiyati -> price_history (gun kapanisi).
            #
            #    Kapanisin zaman damgasi gunun Turkiye saatiyle 00:00'idir:
            #    yfinance'in gunluk barlari da gunu bu sekilde damgalar,
            #    boylece backfill satirlariyla ayni izgaraya oturur ve
            #    ON CONFLICT tahmini backfill degerini olculen kapanisla
            #    degistirir.
            #
            #    SIMULE SATIRLAR KAPANIS OLAMAZ. Scheduler artik simule tick
            #    yazmiyor (bkz. `scheduler.YAZILABILIR_KAYNAKLAR`), ama eski
            #    calistirmalardan kalmis satirlar olabilir; onlar da gecmise
            #    GECMEZ - yalnizca silinir. Boylece sahte veri hicbir yoldan
            #    `price_history`'ye giremez.
            sonuc = await session.execute(
                text(
                    """
                    WITH sinir AS (
                        SELECT CAST(CAST(:gun AS DATE) AS TIMESTAMP)
                                   AT TIME ZONE CAST(:tz AS TEXT) AS bas,
                               CAST(CAST(:gun AS DATE) + 1 AS TIMESTAMP)
                                   AT TIME ZONE CAST(:tz AS TEXT) AS son
                    ),
                    kapanis AS (
                        SELECT DISTINCT ON (lp.asset_id)
                               lp.asset_id, lp.price, lp.source
                        FROM live_prices lp, sinir s
                        WHERE lp.created_at >= s.bas
                          AND lp.created_at <  s.son
                          AND lp.asset_id IS NOT NULL
                          AND lp.price > 0
                          AND lp.source <> 'simulated'
                        ORDER BY lp.asset_id, lp.created_at DESC, lp.id DESC
                    )
                    INSERT INTO price_history (asset_id, ts, price, source)
                    SELECT k.asset_id, s.bas, k.price, k.source
                    FROM kapanis k, sinir s
                    ON CONFLICT (asset_id, ts) DO UPDATE
                        SET price  = EXCLUDED.price,
                            source = EXCLUDED.source
                    """
                ),
                parametreler,
            )
            yazilan = sonuc.rowcount or 0

            # 2) prev_close = gunun kapanisi.
            #    `daily_change_pct`'in "dune gore" olmasinin tek dayanagi bu;
            #    tick'ler artik prev_close'a dokunmuyor.
            await session.execute(
                text(
                    """
                    WITH sinir AS (
                        SELECT CAST(CAST(:gun AS DATE) AS TIMESTAMP)
                                   AT TIME ZONE CAST(:tz AS TEXT) AS bas
                    )
                    UPDATE assets a
                    SET prev_close = ph.price
                    FROM price_history ph, sinir s
                    WHERE ph.asset_id = a.id
                      AND ph.ts = s.bas
                    """
                ),
                parametreler,
            )

            # 3) Yalnizca KAPANAN gunun satirlarini sil.
            #    TRUNCATE degil: o an akan yeni gunun tick'leri korunur.
            #    asset_id'si NULL olan artik satirlar da bu araliktaysa
            #    temizlenir, yoksa gun sonsuza kadar "kapanmadi" gorunurdu.
            await session.execute(
                text(
                    """
                    WITH sinir AS (
                        SELECT CAST(CAST(:gun AS DATE) AS TIMESTAMP)
                                   AT TIME ZONE CAST(:tz AS TEXT) AS bas,
                               CAST(CAST(:gun AS DATE) + 1 AS TIMESTAMP)
                                   AT TIME ZONE CAST(:tz AS TEXT) AS son
                    )
                    DELETE FROM live_prices lp
                    USING sinir s
                    WHERE lp.created_at >= s.bas
                      AND lp.created_at <  s.son
                    """
                ),
                parametreler,
            )

            await session.commit()

        return yazilan

    async def get_api_usage_today(self) -> int:
        """Bugun dis piyasa API'sine yapilan cagri sayisi."""
        async with self._session_factory() as session:
            sonuc = await session.execute(
                text("SELECT call_count FROM market_api_usage WHERE usage_date = CURRENT_DATE")
            )
            satir = sonuc.first()
            return int(satir[0]) if satir else 0

    async def record_api_usage(self, calls: int = 1) -> None:
        """Gunluk cagri sayacini artirir.

        UPSERT: gunun ilk cagrisinda satir yaratilir, sonrakiler UZERINE
        EKLENIR (sifirlanmaz).
        """
        if calls <= 0:
            return

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO market_api_usage (usage_date, call_count, last_call_at)
                    VALUES (CURRENT_DATE, :calls, now())
                    ON CONFLICT (usage_date) DO UPDATE
                        SET call_count   = market_api_usage.call_count + EXCLUDED.call_count,
                            last_call_at = now()
                    """
                ),
                {"calls": calls},
            )
            await session.commit()


class SqlTradingRepository(_SqlRepository):
    """Paper emirleri ve sanal nakit bakiyesini atomik olarak yonetir."""

    async def get_account(self, user_id: int) -> dict | None:
        return await self._row(
            """
            SELECT ca.portfolio_id, p.name AS portfolio_name, ca.currency,
                   ca.available_balance, ca.reserved_balance
            FROM portfolios p
            JOIN cash_accounts ca ON ca.portfolio_id = p.id AND ca.currency = 'TRY'
            WHERE p.user_id = :user_id
            ORDER BY p.is_default DESC, p.id
            LIMIT 1
            """,
            {"user_id": user_id},
        )

    async def get_order_context(self, user_id: int, symbol: str) -> dict | None:
        return await self._row(
            """
            SELECT p.id AS portfolio_id, a.id AS asset_id, a.symbol,
                   a.name AS asset_name, ac.code AS asset_class, a.currency,
                   a.current_price AS native_price, fx.try_rate AS fx_rate,
                   a.current_price * fx.try_rate AS current_price,
                   a.price_updated_at,
                   ca.available_balance, ca.reserved_balance,
                   COALESCE(pa.quantity, 0) AS holding_quantity,
                   COALESCE((
                       SELECT SUM(o.quantity - o.filled_quantity)
                       FROM orders o
                       WHERE o.portfolio_id = p.id AND o.asset_id = a.id
                         AND o.side = 'SELL' AND o.status = 'PENDING'
                         AND o.order_type <> 'STOP_MARKET'
                   ), 0) AS pending_sell_quantity
            FROM portfolios p
            JOIN cash_accounts ca ON ca.portfolio_id = p.id AND ca.currency = 'TRY'
            JOIN assets a ON upper(a.symbol) = upper(:symbol)
            JOIN asset_categories ac ON ac.id = a.category_id
            JOIN v_fx_rates fx ON fx.currency = a.currency
            LEFT JOIN portfolio_assets pa
              ON pa.portfolio_id = p.id AND pa.asset_id = a.id
            WHERE p.user_id = :user_id
            ORDER BY p.is_default DESC, p.id
            LIMIT 1
            """,
            {"user_id": user_id, "symbol": symbol},
        )

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
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise BusinessRuleError("Emir adedi sifirdan buyuk olmalidir.")

        async with self._session_factory() as session:
            async with session.begin():
                existing = await session.execute(
                    text(
                        """
                        SELECT o.*, a.symbol, a.name AS asset_name
                        FROM orders o JOIN assets a ON a.id = o.asset_id
                        WHERE o.user_id = :user_id AND o.idempotency_key = :key
                        """
                    ),
                    {"user_id": user_id, "key": idempotency_key},
                )
                old = existing.mappings().first()
                if old:
                    return dict(old)

                result = await session.execute(
                    text(
                        """
                        SELECT p.id AS portfolio_id, a.id AS asset_id, a.symbol,
                               a.name AS asset_name, ac.code AS asset_class, a.currency,
                               a.current_price AS native_price, fx.try_rate AS fx_rate,
                               a.current_price * fx.try_rate AS current_price,
                               ca.available_balance,
                               COALESCE(pa.quantity, 0) AS holding_quantity
                        FROM portfolios p
                        JOIN cash_accounts ca
                          ON ca.portfolio_id = p.id AND ca.currency = 'TRY'
                        JOIN assets a ON upper(a.symbol) = upper(:symbol)
                        JOIN asset_categories ac ON ac.id = a.category_id
                        JOIN v_fx_rates fx ON fx.currency = a.currency
                        LEFT JOIN portfolio_assets pa
                          ON pa.portfolio_id = p.id AND pa.asset_id = a.id
                        WHERE p.user_id = :user_id
                        ORDER BY p.is_default DESC, p.id
                        LIMIT 1
                        FOR UPDATE OF p, ca
                        """
                    ),
                    {"user_id": user_id, "symbol": symbol},
                )
                context = result.mappings().first()
                if not context:
                    raise NotFoundError(f"'{symbol.upper()}' hissesi veya paper hesabi bulunamadi.")
                if context["asset_class"] == "INDEX":
                    raise BusinessRuleError("Endeksler dogrudan alinip satilamaz.")
                if side not in {"BUY", "SELL"}:
                    raise BusinessRuleError("Islem yonu BUY veya SELL olmalidir.")
                if order_type not in {"MARKET", "LIMIT"}:
                    raise BusinessRuleError("Emir tipi MARKET veya LIMIT olmalidir.")
                if order_type == "LIMIT" and (limit_price is None or limit_price <= 0):
                    raise BusinessRuleError("Limit fiyati sifirdan buyuk olmalidir.")
                if validity not in {"DAY", "GTC"}:
                    raise BusinessRuleError("Gecerlilik DAY veya GTC olmalidir.")
                if stop_loss_price is not None:
                    reference = (
                        Decimal(str(limit_price)) / Decimal(str(context["fx_rate"]))
                        if order_type == "LIMIT"
                        else Decimal(str(context["native_price"]))
                    )
                    if (
                        side != "BUY"
                        or Decimal(str(stop_loss_price)) <= 0
                        or Decimal(str(stop_loss_price)) >= reference
                    ):
                        raise BusinessRuleError(
                            "Stop-loss fiyati alim referans fiyatindan dusuk olmalidir."
                        )

                price = Decimal(str(context["current_price"]))
                reserve_price = Decimal(str(limit_price)) if order_type == "LIMIT" else price
                commission = _money(reserve_price * qty * Decimal(str(commission_rate)))
                # Piyasa emrinde sonraki tick icin %2 tampon; limit emrinde
                # kullanicinin belirledigi azami fiyat + komisyon bloke edilir.
                reserve = _money(
                    reserve_price
                    * qty
                    * (Decimal("1") if order_type == "LIMIT" else Decimal("1.02"))
                    + commission
                )

                if side == "BUY":
                    if Decimal(str(context["available_balance"])) < reserve:
                        raise BusinessRuleError(
                            "Fiyat tamponu dahil bu alim emri icin sanal bakiye yetersiz."
                        )
                    await session.execute(
                        text(
                            """
                            UPDATE cash_accounts
                            SET available_balance = available_balance - :reserve,
                                reserved_balance = reserved_balance + :reserve,
                                updated_at = now()
                            WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                            """
                        ),
                        {"reserve": reserve, "portfolio_id": context["portfolio_id"]},
                    )
                else:
                    pending = await session.scalar(
                        text(
                            """
                            SELECT COALESCE(SUM(quantity - filled_quantity), 0)
                            FROM orders
                            WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                              AND side = 'SELL' AND status = 'PENDING'
                              AND order_type <> 'STOP_MARKET'
                            """
                        ),
                        {
                            "portfolio_id": context["portfolio_id"],
                            "asset_id": context["asset_id"],
                        },
                    )
                    if Decimal(str(context["holding_quantity"])) - Decimal(str(pending)) < qty:
                        raise BusinessRuleError(
                            "Bekleyen emirler dusuldugunde satilabilir hisse adedi yetersiz."
                        )
                    reserve = Decimal("0")

                inserted = await session.execute(
                    text(
                        """
                        INSERT INTO orders (
                            user_id, portfolio_id, asset_id, side, order_type,
                            quantity, quoted_price, limit_price, stop_loss_price,
                            stop_loss_currency,
                            validity, expires_at,
                            status, reserved_amount, idempotency_key
                        ) VALUES (
                            :user_id, :portfolio_id, :asset_id, :side, :order_type,
                            :quantity, :quoted_price, :limit_price, :stop_loss_price,
                            :stop_loss_currency,
                            :validity, :expires_at,
                            'PENDING', :reserved_amount, :idempotency_key
                        )
                        RETURNING *
                        """
                    ),
                    {
                        "user_id": user_id,
                        "portfolio_id": context["portfolio_id"],
                        "asset_id": context["asset_id"],
                        "side": side,
                        "quantity": qty,
                        "quoted_price": price,
                        "order_type": order_type,
                        "limit_price": limit_price,
                        "stop_loss_price": stop_loss_price,
                        "stop_loss_currency": (
                            context["currency"] if stop_loss_price is not None else None
                        ),
                        "validity": validity,
                        "expires_at": expires_at,
                        "reserved_amount": reserve,
                        "idempotency_key": idempotency_key,
                    },
                )
                row = dict(inserted.mappings().one())
                row.update(symbol=context["symbol"], asset_name=context["asset_name"])
                return row

    async def list_orders(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self._rows(
            """
            SELECT o.*, a.symbol, a.name AS asset_name
            FROM orders o
            JOIN assets a ON a.id = o.asset_id
            WHERE o.user_id = :user_id
            ORDER BY o.created_at DESC, o.id DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )

    async def cancel_order(self, user_id: int, order_id: int) -> dict:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        SELECT o.*, a.symbol, a.name AS asset_name
                        FROM orders o
                        JOIN assets a ON a.id = o.asset_id
                        WHERE o.id = :order_id AND o.user_id = :user_id
                        FOR UPDATE OF o
                        """
                    ),
                    {"order_id": order_id, "user_id": user_id},
                )
                order = result.mappings().first()
                if not order:
                    raise NotFoundError("Emir bulunamadi.")
                if order["status"] != "PENDING":
                    raise BusinessRuleError("Yalnizca bekleyen emirler iptal edilebilir.")

                reserved = Decimal(str(order["reserved_amount"] or 0))
                if reserved > 0:
                    await session.execute(
                        text(
                            """
                            UPDATE cash_accounts
                            SET available_balance = available_balance + :reserved,
                                reserved_balance = reserved_balance - :reserved,
                                updated_at = now()
                            WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                            """
                        ),
                        {"reserved": reserved, "portfolio_id": order["portfolio_id"]},
                    )
                await session.execute(
                    text(
                        """
                        UPDATE orders
                        SET status = 'CANCELLED', reserved_amount = 0, updated_at = now()
                        WHERE id = :order_id
                        """
                    ),
                    {"order_id": order_id},
                )
                updated = dict(order)
                updated.update(status="CANCELLED", reserved_amount=Decimal("0"))
                return updated

    async def process_pending_orders(self, updates: list[dict], commission_rate: float) -> int:
        prices = {
            int(item["asset_id"]): Decimal(str(item["price"]))
            for item in updates
            if item.get("asset_id") is not None and float(item.get("price") or 0) > 0
        }
        completed = 0
        async with self._session_factory() as session:
            async with session.begin():
                expired_result = await session.execute(
                    text(
                        """
                        SELECT id, portfolio_id, reserved_amount
                        FROM orders
                        WHERE status = 'PENDING' AND expires_at IS NOT NULL AND expires_at <= now()
                        FOR UPDATE SKIP LOCKED
                        """
                    )
                )
                for expired in expired_result.mappings().all():
                    reserved = Decimal(str(expired["reserved_amount"] or 0))
                    if reserved > 0:
                        await session.execute(
                            text(
                                """
                                UPDATE cash_accounts
                                SET available_balance = available_balance + :reserved,
                                    reserved_balance = reserved_balance - :reserved,
                                    updated_at = now()
                                WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                                """
                            ),
                            {"reserved": reserved, "portfolio_id": expired["portfolio_id"]},
                        )
                    await session.execute(
                        text(
                            """
                            UPDATE orders
                            SET status = 'CANCELLED', reserved_amount = 0, updated_at = now()
                            WHERE id = :order_id
                            """
                        ),
                        {"order_id": expired["id"]},
                    )
                    await self._queue_notification(session, expired["id"], "ORDER_EXPIRED")

                result = await session.execute(
                    text(
                        """
                        SELECT o.*, a.currency AS asset_currency, fx.try_rate AS fx_rate
                        FROM orders o
                        JOIN assets a ON a.id = o.asset_id
                        JOIN v_fx_rates fx ON fx.currency = a.currency
                        WHERE o.status = 'PENDING'
                          AND o.asset_id IN (
                              SELECT CAST(value AS INT)
                              FROM jsonb_array_elements_text(CAST(:asset_ids AS JSONB))
                          )
                        ORDER BY CASE WHEN o.order_type = 'STOP_MARKET' THEN 1 ELSE 0 END,
                                 o.created_at, o.id
                        FOR UPDATE SKIP LOCKED
                        """
                    ),
                    {"asset_ids": json.dumps(list(prices))},
                )
                orders = [dict(row) for row in result.mappings().all()]

                for order in orders:
                    native_price = prices[order["asset_id"]]
                    price = native_price * Decimal(str(order["fx_rate"]))
                    if order["order_type"] == "LIMIT":
                        limit = Decimal(str(order["limit_price"]))
                        condition_met = price <= limit if order["side"] == "BUY" else price >= limit
                        if not condition_met:
                            continue
                    elif order["order_type"] == "STOP_MARKET":
                        stop_price = Decimal(str(order["stop_loss_price"]))
                        comparison_price = (
                            native_price if order.get("stop_loss_currency") else price
                        )
                        if comparison_price > stop_price:
                            continue
                    qty = Decimal(str(order["quantity"]))
                    if order["order_type"] == "STOP_MARKET":
                        protected_available = await session.scalar(
                            text(
                                """
                                SELECT GREATEST(
                                    COALESCE(pa.quantity, 0) - COALESCE((
                                        SELECT SUM(o.quantity - o.filled_quantity)
                                        FROM orders o
                                        WHERE o.portfolio_id = :portfolio_id
                                          AND o.asset_id = :asset_id
                                          AND o.side = 'SELL' AND o.status = 'PENDING'
                                          AND o.order_type <> 'STOP_MARKET'
                                    ), 0), 0
                                )
                                FROM (SELECT 1) seed
                                LEFT JOIN portfolio_assets pa
                                  ON pa.portfolio_id = :portfolio_id AND pa.asset_id = :asset_id
                                """
                            ),
                            {
                                "portfolio_id": order["portfolio_id"],
                                "asset_id": order["asset_id"],
                            },
                        )
                        qty = min(qty, Decimal(str(protected_available or 0)))
                        if qty <= 0:
                            continue
                        if qty != Decimal(str(order["quantity"])):
                            await session.execute(
                                text(
                                    "UPDATE orders SET quantity = :quantity, "
                                    "updated_at = now() WHERE id = :order_id"
                                ),
                                {"quantity": qty, "order_id": order["id"]},
                            )
                    gross = _money(price * qty)
                    commission = _money(gross * Decimal(str(commission_rate)))

                    account_result = await session.execute(
                        text(
                            """
                            SELECT * FROM cash_accounts
                            WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                            FOR UPDATE
                            """
                        ),
                        {"portfolio_id": order["portfolio_id"]},
                    )
                    account = account_result.mappings().first()
                    if not account:
                        await self._reject_order(session, order, "Paper trading hesabi bulunamadi.")
                        continue

                    if order["side"] == "BUY":
                        total = gross + commission
                        reserved = Decimal(str(order["reserved_amount"] or 0))
                        available = Decimal(str(account["available_balance"]))
                        if available + reserved < total:
                            await self._reject_order(
                                session, order, "Yeni fiyatta kullanilabilir bakiye yetersiz."
                            )
                            continue
                        await session.execute(
                            text(
                                """
                                UPDATE cash_accounts
                                SET available_balance = available_balance + :reserved - :total,
                                    reserved_balance = reserved_balance - :reserved,
                                    updated_at = now()
                                WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                                """
                            ),
                            {
                                "reserved": reserved,
                                "total": total,
                                "portfolio_id": order["portfolio_id"],
                            },
                        )
                        await session.execute(
                            text(
                                """
                                INSERT INTO portfolio_assets (
                                    portfolio_id, asset_id, quantity, average_buy_price
                                ) VALUES (:portfolio_id, :asset_id, :quantity, :price)
                                ON CONFLICT (portfolio_id, asset_id) DO UPDATE SET
                                    average_buy_price = CASE
                                        WHEN portfolio_assets.quantity + EXCLUDED.quantity > 0
                                        THEN (
                                            portfolio_assets.quantity
                                            * portfolio_assets.average_buy_price
                                            + EXCLUDED.quantity * EXCLUDED.average_buy_price
                                        ) / (portfolio_assets.quantity + EXCLUDED.quantity)
                                        ELSE 0
                                    END,
                                    quantity = portfolio_assets.quantity + EXCLUDED.quantity
                                """
                            ),
                            {
                                "portfolio_id": order["portfolio_id"],
                                "asset_id": order["asset_id"],
                                "quantity": qty,
                                "price": native_price,
                            },
                        )
                        ledger_amount = -total
                        ledger_type = "BUY_FILL"
                    else:
                        holding_result = await session.execute(
                            text(
                                """
                                SELECT * FROM portfolio_assets
                                WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                                FOR UPDATE
                                """
                            ),
                            {
                                "portfolio_id": order["portfolio_id"],
                                "asset_id": order["asset_id"],
                            },
                        )
                        holding = holding_result.mappings().first()
                        if not holding or Decimal(str(holding["quantity"])) < qty:
                            await self._reject_order(
                                session, order, "Gerceklesme aninda satilabilir adet yetersiz."
                            )
                            continue
                        net = gross - commission
                        await session.execute(
                            text(
                                """
                                UPDATE portfolio_assets
                                SET quantity = quantity - :quantity
                                WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                                """
                            ),
                            {
                                "quantity": qty,
                                "portfolio_id": order["portfolio_id"],
                                "asset_id": order["asset_id"],
                            },
                        )
                        await session.execute(
                            text(
                                """
                                UPDATE cash_accounts
                                SET available_balance = available_balance + :net,
                                    updated_at = now()
                                WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                                """
                            ),
                            {"net": net, "portfolio_id": order["portfolio_id"]},
                        )
                        await session.execute(
                            text(
                                """
                                DELETE FROM portfolio_assets
                                WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                                  AND quantity = 0
                                """
                            ),
                            {
                                "portfolio_id": order["portfolio_id"],
                                "asset_id": order["asset_id"],
                            },
                        )
                        ledger_amount = net
                        ledger_type = "SELL_PROCEEDS"

                    await session.execute(
                        text(
                            """
                            INSERT INTO transactions (
                                portfolio_id, asset_id, transaction_type,
                                quantity, unit_price, transaction_date
                            ) VALUES (
                                :portfolio_id, :asset_id, :side,
                                :quantity, :unit_price, now()
                            )
                            """
                        ),
                        {
                            "portfolio_id": order["portfolio_id"],
                            "asset_id": order["asset_id"],
                            "side": order["side"],
                            "quantity": qty,
                            "unit_price": native_price,
                        },
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO order_fills (order_id, quantity, price, commission)
                            VALUES (:order_id, :quantity, :price, :commission)
                            """
                        ),
                        {
                            "order_id": order["id"],
                            "quantity": qty,
                            "price": price,
                            "commission": commission,
                        },
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO cash_ledger (
                                account_id, order_id, entry_type, amount, balance_after
                            )
                            SELECT id, :order_id, :entry_type, :amount, available_balance
                            FROM cash_accounts
                            WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                            """
                        ),
                        {
                            "order_id": order["id"],
                            "entry_type": ledger_type,
                            "amount": ledger_amount,
                            "portfolio_id": order["portfolio_id"],
                        },
                    )
                    await session.execute(
                        text(
                            """
                            UPDATE orders
                            SET status = 'FILLED', filled_quantity = quantity,
                                average_fill_price = :price, commission = :commission,
                                filled_at = now(), updated_at = now()
                            WHERE id = :order_id
                            """
                        ),
                        {
                            "price": price,
                            "commission": commission,
                            "order_id": order["id"],
                        },
                    )
                    await self._queue_notification(
                        session,
                        order["id"],
                        "ORDER_FILLED",
                        {
                            "price": float(price),
                            "commission": float(commission),
                            "total": float(abs(ledger_amount)),
                            "quantity": float(qty),
                        },
                    )
                    if order["side"] == "BUY" and order.get("stop_loss_price") is not None:
                        await session.execute(
                            text(
                                """
                                INSERT INTO orders (
                                    user_id, portfolio_id, asset_id, side, order_type,
                                    quantity, quoted_price, stop_loss_price,
                                    stop_loss_currency, parent_order_id,
                                    validity, status, reserved_amount, idempotency_key
                                ) VALUES (
                                    :user_id, :portfolio_id, :asset_id, 'SELL', 'STOP_MARKET',
                                    :quantity, :quoted_price, :stop_loss_price,
                                    :stop_loss_currency, :parent_order_id,
                                    'GTC', 'PENDING', 0, :idempotency_key
                                )
                                ON CONFLICT (user_id, idempotency_key) DO NOTHING
                                """
                            ),
                            {
                                "user_id": order["user_id"],
                                "portfolio_id": order["portfolio_id"],
                                "asset_id": order["asset_id"],
                                "quantity": qty,
                                "quoted_price": price,
                                "stop_loss_price": order["stop_loss_price"],
                                "stop_loss_currency": order.get("stop_loss_currency"),
                                "parent_order_id": order["id"],
                                "idempotency_key": f"attached-stop-{order['id']}",
                            },
                        )
                    if order["side"] == "SELL" and order["order_type"] != "STOP_MARKET":
                        await self._normalize_stop_orders(
                            session, order["portfolio_id"], order["asset_id"], qty
                        )
                    completed += 1

        return completed

    async def _normalize_stop_orders(
        self, session, portfolio_id: int, asset_id: int, sold_quantity: Decimal
    ) -> None:
        remaining = await session.scalar(
            text(
                """
                SELECT COALESCE(quantity, 0) FROM portfolio_assets
                WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                """
            ),
            {"portfolio_id": portfolio_id, "asset_id": asset_id},
        )
        available = Decimal(str(remaining or 0))
        manual_reduction = sold_quantity
        result = await session.execute(
            text(
                """
                SELECT id, quantity FROM orders
                WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                  AND order_type = 'STOP_MARKET' AND status = 'PENDING'
                ORDER BY created_at, id
                FOR UPDATE
                """
            ),
            {"portfolio_id": portfolio_id, "asset_id": asset_id},
        )
        for stop in result.mappings().all():
            original = Decimal(str(stop["quantity"]))
            reduction = min(original, manual_reduction)
            manual_reduction -= reduction
            protected = min(original - reduction, available)
            if protected <= 0:
                await session.execute(
                    text(
                        "UPDATE orders SET status = 'CANCELLED', updated_at = now() WHERE id = :id"
                    ),
                    {"id": stop["id"]},
                )
            elif protected != original:
                await session.execute(
                    text(
                        "UPDATE orders SET quantity = :quantity, updated_at = now() WHERE id = :id"
                    ),
                    {"quantity": protected, "id": stop["id"]},
                )
            available -= protected

    async def _queue_notification(
        self, session, order_id: int, event_type: str, extra: dict | None = None
    ) -> None:
        """Bildirim olayini outbox'a yazar - CAGIRAN TRANSACTION ICINDE.

        Ayni transaction bilincli bir tercihtir: gerceklesme geri alinirsa
        bildirim de geri alinir; gerceklesme yazildiysa bildirim de yazilmis
        olur. Ayri bir transaction "gerceklesmeyen emir icin bildirim" ve
        "bildirimsiz gerceklesme" hatalarinin IKISINI DE mumkun kilardi.

        Alici adresi ve sembol OLAY ANINDA fotograflanir: kullanici sonradan
        e-postasini degistirse bile gecmis bildirim kaydi degismez.
        """
        await session.execute(
            text(
                """
                INSERT INTO notification_outbox (
                    user_id, order_id, event_type, channel, recipient, payload
                )
                SELECT o.user_id, o.id, :event_type, 'EMAIL', u.email,
                       jsonb_build_object(
                           'symbol', a.symbol,
                           'asset_name', a.name,
                           'side', o.side,
                           'order_type', o.order_type,
                           'quantity', o.quantity,
                           'rejection_reason', o.rejection_reason
                       ) || CAST(:extra AS JSONB)
                FROM orders o
                JOIN users u ON u.id = o.user_id
                JOIN assets a ON a.id = o.asset_id
                WHERE o.id = :order_id
                """
            ),
            {
                "event_type": event_type,
                "order_id": order_id,
                "extra": json.dumps(extra or {}),
            },
        )

    async def _reject_order(self, session, order: dict, reason: str) -> None:
        reserved = Decimal(str(order.get("reserved_amount") or 0))
        if reserved > 0:
            await session.execute(
                text(
                    """
                    UPDATE cash_accounts
                    SET available_balance = available_balance + :reserved,
                        reserved_balance = reserved_balance - :reserved,
                        updated_at = now()
                    WHERE portfolio_id = :portfolio_id AND currency = 'TRY'
                    """
                ),
                {"reserved": reserved, "portfolio_id": order["portfolio_id"]},
            )
        await session.execute(
            text(
                """
                UPDATE orders
                SET status = 'REJECTED', rejection_reason = :reason, updated_at = now()
                WHERE id = :order_id
                """
            ),
            {"reason": reason, "order_id": order["id"]},
        )
        await self._queue_notification(session, order["id"], "ORDER_REJECTED")


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SqlRecommendationRepository(_SqlRepository):
    """Otonom oneri motorunun kalici durumu (AUT / D-02, D-07)."""

    #: Kullanicinin `user_trading_limits` satiri yoksa uygulanan degerler.
    #: Satirin YOKLUGU bir hata degildir: kullanici limit ekranina hic
    #: girmemis olabilir ve otonom akis yine de calismalidir.
    VARSAYILAN_LIMITLER = {
        "per_order_limit_try": 5000.0,
        "daily_limit_try": 15000.0,
        "allowed_asset_classes": [],
        "autonomous_enabled": True,
        "max_daily_recommendations": 4,
    }

    # ---------------- kill-switch ----------------

    async def kill_switch_active(self) -> bool:
        row = await self._row("SELECT active FROM autonomous_kill_switch WHERE id")
        return bool(row and row["active"])

    async def set_kill_switch(self, active: bool, reason: str | None, actor: str) -> dict:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        UPDATE autonomous_kill_switch
                        SET active = :active, reason = :reason,
                            activated_by = :actor, updated_at = now()
                        WHERE id
                        RETURNING active, reason, activated_by, updated_at
                        """
                    ),
                    {"active": active, "reason": reason, "actor": actor},
                )
                return dict(result.mappings().one())

    # ---------------- limitler ----------------

    async def get_limits(self, user_id: int) -> dict:
        row = await self._row(
            """
            SELECT per_order_limit_try, daily_limit_try, allowed_asset_classes,
                   autonomous_enabled, max_daily_recommendations
            FROM user_trading_limits WHERE user_id = :user_id
            """,
            {"user_id": user_id},
        )
        if row is None:
            return dict(self.VARSAYILAN_LIMITLER)
        return {
            "per_order_limit_try": float(row["per_order_limit_try"]),
            "daily_limit_try": float(row["daily_limit_try"]),
            "allowed_asset_classes": list(row["allowed_asset_classes"] or []),
            "autonomous_enabled": bool(row["autonomous_enabled"]),
            "max_daily_recommendations": int(row["max_daily_recommendations"]),
        }

    async def upsert_limits(self, user_id: int, fields: dict) -> dict:
        mevcut = await self.get_limits(user_id)
        birlesik = {**mevcut, **{k: v for k, v in fields.items() if v is not None}}
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO user_trading_limits (
                            user_id, per_order_limit_try, daily_limit_try,
                            allowed_asset_classes, autonomous_enabled,
                            max_daily_recommendations, updated_at
                        ) VALUES (
                            :user_id, :per_order, :daily, CAST(:classes AS JSONB),
                            :enabled, :max_daily, now()
                        )
                        ON CONFLICT (user_id) DO UPDATE SET
                            per_order_limit_try = EXCLUDED.per_order_limit_try,
                            daily_limit_try = EXCLUDED.daily_limit_try,
                            allowed_asset_classes = EXCLUDED.allowed_asset_classes,
                            autonomous_enabled = EXCLUDED.autonomous_enabled,
                            max_daily_recommendations = EXCLUDED.max_daily_recommendations,
                            updated_at = now()
                        """
                    ),
                    {
                        "user_id": user_id,
                        "per_order": birlesik["per_order_limit_try"],
                        "daily": birlesik["daily_limit_try"],
                        "classes": _json(birlesik["allowed_asset_classes"]),
                        "enabled": birlesik["autonomous_enabled"],
                        "max_daily": birlesik["max_daily_recommendations"],
                    },
                )
        return birlesik

    # ---------------- sinyal ----------------

    async def assets_for_scan(self) -> list[dict]:
        return await self._rows(
            """
            SELECT a.id AS asset_id, a.symbol, a.name, ac.code AS asset_class,
                   a.currency, a.sector, a.region,
                   CASE
                       WHEN fx.try_rate IS NULL THEN a.current_price
                       ELSE a.current_price * fx.try_rate
                   END AS current_price,
                   a.daily_change_pct, a.weekly_change_pct, a.yearly_change_pct,
                   a.price_updated_at, vol.volatility_20d_pct,
                   COALESCE(vol.volatility_observation_count, 0)
                       AS volatility_observation_count,
                   COALESCE(vol.daily_returns_252d, '{}'::jsonb) AS daily_returns_252d
            FROM assets a
            JOIN asset_categories ac ON ac.id = a.category_id
            LEFT JOIN v_fx_rates fx ON fx.currency = a.currency
            LEFT JOIN LATERAL (
                SELECT CASE WHEN count(return_pct) FILTER (WHERE recency <= 20) >= 20
                            THEN stddev_samp(return_pct) FILTER (WHERE recency <= 20)
                       END AS volatility_20d_pct,
                       count(return_pct) FILTER (WHERE recency <= 20)
                           AS volatility_observation_count,
                       jsonb_object_agg(ts::text, return_pct ORDER BY ts)
                           FILTER (WHERE return_pct IS NOT NULL) AS daily_returns_252d
                FROM (
                    SELECT ts, return_pct,
                           row_number() OVER (ORDER BY ts DESC) AS recency
                    FROM (
                        SELECT ts,
                               (price / lag(price) OVER (ORDER BY ts) - 1) * 100
                                   AS return_pct
                        FROM (
                            SELECT day AS ts, price
                            FROM (
                                SELECT DISTINCT ON ((ts AT TIME ZONE 'Europe/Istanbul')::date)
                                       (ts AT TIME ZONE 'Europe/Istanbul')::date AS day,
                                       price
                                FROM price_history
                                WHERE asset_id = a.id
                                ORDER BY (ts AT TIME ZONE 'Europe/Istanbul')::date DESC,
                                         ts DESC
                            ) daily_closes
                            ORDER BY day DESC
                            LIMIT 253
                        ) daily_points
                    ) returns
                ) ranked_returns
            ) vol ON true
            ORDER BY a.id
            """
        )

    async def save_signals(self, signals: list[dict]) -> list[dict]:
        if not signals:
            return []
        yayinlanan: list[dict] = []
        async with self._session_factory() as session:
            async with session.begin():
                for sig in signals:
                    result = await session.execute(
                        text(
                            """
                            INSERT INTO signals (
                                asset_id, direction, confidence, rule_code,
                                rationale, evidence, reference_price, expires_at,
                                engine_version, published, suppressed_reason
                            ) VALUES (
                                :asset_id, :direction, :confidence, :rule_code,
                                CAST(:rationale AS JSONB), CAST(:evidence AS JSONB),
                                :reference_price, :expires_at,
                                :engine_version, :published, :suppressed_reason
                            )
                            RETURNING id
                            """
                        ),
                        {
                            **{
                                k: sig[k]
                                for k in (
                                    "asset_id",
                                    "direction",
                                    "confidence",
                                    "rule_code",
                                    "reference_price",
                                    "expires_at",
                                    "engine_version",
                                    "published",
                                    "suppressed_reason",
                                )
                            },
                            "rationale": _json(sig["rationale"]),
                            "evidence": _json(sig["evidence"]),
                        },
                    )
                    signal_id = result.scalar_one()
                    if sig["published"]:
                        yayinlanan.append({**sig, "id": int(signal_id)})
        return yayinlanan

    # ---------------- oneri uretimi ----------------

    async def autonomous_users(self) -> list[dict]:
        """Otonom akisi acik, nakit hesabi olan kullanicilar ve baglamlari.

        PORTFOY SECIMI `get_order_context` ILE AYNI OLMALIDIR:
        `is_default` DESC, sonra en kucuk id. Depoda `is_default` her
        kullanicida isaretli DEGIL (9 portfoyun 2'si) ve nakit hesaplari
        varsayilan olmayan portfoylerde duruyor. `AND p.is_default` ile
        zorlansaydi hicbir kullanici taranmazdi; daha kotusu, oneri bir
        portfoye uretilip emir BASKA portfoye gitseydi bakiye ve pozisyon
        hesaplari tutmazdi.
        """
        return await self._rows(
            """
            SELECT DISTINCT ON (u.id)
                   u.id AS user_id, u.risk_tolerance,
                   p.id AS portfolio_id, ca.available_balance,
                   COALESCE(vs.total_value_try, 0) AS portfolio_value_try,
                   COALESCE(l.autonomous_enabled, true) AS autonomous_enabled,
                   COALESCE(l.per_order_limit_try, 5000) AS per_order_limit_try,
                   COALESCE(l.daily_limit_try, 15000) AS daily_limit_try,
                   COALESCE(l.allowed_asset_classes, '[]'::jsonb) AS allowed_asset_classes,
                   COALESCE(l.max_daily_recommendations, 4) AS max_daily_recommendations
            FROM users u
            JOIN portfolios p ON p.user_id = u.id
            JOIN cash_accounts ca ON ca.portfolio_id = p.id AND ca.currency = 'TRY'
            LEFT JOIN user_trading_limits l ON l.user_id = u.id
            LEFT JOIN v_portfolio_summary vs ON vs.portfolio_id = p.id
            WHERE COALESCE(l.autonomous_enabled, true)
            ORDER BY u.id, p.is_default DESC, p.id
            """
        )

    async def user_context(self, user_id: int) -> dict | None:
        return await self._row(
            """
            SELECT u.id AS user_id, u.risk_tolerance,
                   p.id AS portfolio_id, ca.available_balance,
                   COALESCE(vs.total_value_try, 0) AS portfolio_value_try,
                   COALESCE(l.allowed_asset_classes, '[]'::jsonb) AS allowed_asset_classes
            FROM users u
            JOIN portfolios p ON p.user_id = u.id
            JOIN cash_accounts ca ON ca.portfolio_id = p.id AND ca.currency = 'TRY'
            LEFT JOIN user_trading_limits l ON l.user_id = u.id
            LEFT JOIN v_portfolio_summary vs ON vs.portfolio_id = p.id
            WHERE u.id = :user_id
            ORDER BY p.is_default DESC, p.id
            LIMIT 1
            """,
            {"user_id": user_id},
        )

    async def holdings_map(self, portfolio_id: int) -> dict[int, float]:
        rows = await self._rows(
            """
            SELECT asset_id, quantity FROM portfolio_assets
            WHERE portfolio_id = :portfolio_id AND quantity > 0
            """,
            {"portfolio_id": portfolio_id},
        )
        return {int(r["asset_id"]): float(r["quantity"]) for r in rows}

    async def get_basket_state(self, user_id: int, goal: str) -> dict | None:
        row = await self._row(
            """
            SELECT user_id, goal, memberships, breach_counts,
                   membership_since, change_signals, profile_signature,
                   evaluated_at, changed_at, created_at, updated_at
            FROM idle_cash_basket_states
            WHERE user_id = :user_id AND goal = :goal
            """,
            {"user_id": user_id, "goal": goal},
        )
        if row is None:
            return None
        return {
            **row,
            "memberships": list(row.get("memberships") or []),
            "breach_counts": dict(row.get("breach_counts") or {}),
            "membership_since": dict(row.get("membership_since") or {}),
            "change_signals": dict(row.get("change_signals") or {}),
        }

    async def upsert_basket_state(self, user_id: int, goal: str, state: dict) -> dict:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO idle_cash_basket_states (
                            user_id, goal, memberships, breach_counts,
                            membership_since, change_signals, profile_signature,
                            evaluated_at, changed_at, updated_at
                        ) VALUES (
                            :user_id, :goal, CAST(:memberships AS JSONB),
                            CAST(:breach_counts AS JSONB),
                            CAST(:membership_since AS JSONB),
                            CAST(:change_signals AS JSONB), :profile_signature,
                            :evaluated_at, :changed_at, now()
                        )
                        ON CONFLICT (user_id, goal) DO UPDATE SET
                            memberships = EXCLUDED.memberships,
                            breach_counts = EXCLUDED.breach_counts,
                            membership_since = EXCLUDED.membership_since,
                            change_signals = EXCLUDED.change_signals,
                            profile_signature = EXCLUDED.profile_signature,
                            evaluated_at = EXCLUDED.evaluated_at,
                            changed_at = EXCLUDED.changed_at,
                            updated_at = now()
                        """
                    ),
                    {
                        "user_id": user_id,
                        "goal": goal,
                        "memberships": _json(state["memberships"]),
                        "breach_counts": _json(state.get("breach_counts") or {}),
                        "membership_since": _json(state.get("membership_since") or {}),
                        "change_signals": _json(state.get("change_signals") or {}),
                        "profile_signature": state["profile_signature"],
                        "evaluated_at": state["evaluated_at"],
                        "changed_at": state["changed_at"],
                    },
                )
        return await self.get_basket_state(user_id, goal) or {}

    async def daily_stats(self, user_id: int) -> dict:
        row = await self._row(
            """
            SELECT count(*) AS adet,
                   COALESCE(SUM(estimated_amount), 0) AS toplam
            FROM recommendations
            WHERE user_id = :user_id AND created_at >= date_trunc('day', now())
            """,
            {"user_id": user_id},
        )
        return {"count": int(row["adet"]), "amount": float(row["toplam"])}

    async def open_recommendation_asset_ids(self, user_id: int) -> list[int]:
        rows = await self._rows(
            """
            SELECT DISTINCT asset_id FROM recommendations
            WHERE user_id = :user_id AND status IN ('PUBLISHED', 'VIEWED', 'APPROVED')
            """,
            {"user_id": user_id},
        )
        return [int(r["asset_id"]) for r in rows]

    async def create_recommendation(self, row: dict) -> dict:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        INSERT INTO recommendations (
                            signal_id, user_id, portfolio_id, asset_id, side,
                            quantity, reference_price, estimated_amount, confidence,
                            rationale, risk_note, sources, personalization, expires_at
                        ) VALUES (
                            :signal_id, :user_id, :portfolio_id, :asset_id, :side,
                            :quantity, :reference_price, :estimated_amount, :confidence,
                            CAST(:rationale AS JSONB), :risk_note,
                            CAST(:sources AS JSONB), CAST(:personalization AS JSONB),
                            :expires_at
                        )
                        RETURNING id
                        """
                    ),
                    {
                        **{
                            k: row[k]
                            for k in (
                                "signal_id",
                                "user_id",
                                "portfolio_id",
                                "asset_id",
                                "side",
                                "quantity",
                                "reference_price",
                                "estimated_amount",
                                "confidence",
                                "risk_note",
                                "expires_at",
                            )
                        },
                        "rationale": _json(row["rationale"]),
                        "sources": _json(row["sources"]),
                        "personalization": _json(row["personalization"]),
                    },
                )
                yeni_id = int(result.scalar_one())
                # FR-AUT-006: bildirim, onerinin yazildigi AYNI transaction'da
                # kuyruga girer. Geri alinan bir oneri icin bildirim uretilmez.
                await session.execute(
                    text(
                        """
                        INSERT INTO notification_outbox (
                            user_id, order_id, event_type, channel, recipient, payload
                        )
                        SELECT r.user_id, NULL, 'RECOMMENDATION_CREATED', 'EMAIL', u.email,
                               jsonb_build_object(
                                   'symbol', a.symbol,
                                   'asset_name', a.name,
                                   'side', r.side,
                                   'quantity', r.quantity,
                                   'reference_price', r.reference_price,
                                   'estimated_amount', r.estimated_amount,
                                   'confidence', r.confidence,
                                   'rationale', r.rationale
                               )
                        FROM recommendations r
                        JOIN users u ON u.id = r.user_id
                        JOIN assets a ON a.id = r.asset_id
                        WHERE r.id = :rid
                        """
                    ),
                    {"rid": yeni_id},
                )
        return await self.get_recommendation(row["user_id"], yeni_id) or {}

    # ---------------- okuma ----------------

    _SECIM = """
        SELECT r.*, a.symbol AS asset_symbol, a.name AS asset_name,
               ac.code AS asset_class
        FROM recommendations r
        JOIN assets a ON a.id = r.asset_id
        JOIN asset_categories ac ON ac.id = a.category_id
    """

    async def list_recommendations(
        self, user_id: int, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        return await self._rows(
            self._SECIM
            + """
            WHERE r.user_id = :user_id
              AND (CAST(:status AS TEXT) IS NULL OR r.status = :status)
            ORDER BY r.created_at DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "status": status, "limit": limit},
        )

    async def counts_by_status(self, user_id: int) -> dict:
        rows = await self._rows(
            """
            SELECT status, count(*) AS adet FROM recommendations
            WHERE user_id = :user_id GROUP BY status
            """,
            {"user_id": user_id},
        )
        return {r["status"]: int(r["adet"]) for r in rows}

    async def get_recommendation(self, user_id: int, recommendation_id: int) -> dict | None:
        return await self._row(
            self._SECIM + " WHERE r.user_id = :user_id AND r.id = :rid",
            {"user_id": user_id, "rid": recommendation_id},
        )

    # ---------------- durum gecisleri (D-07) ----------------

    async def mark_viewed(self, user_id: int, recommendation_id: int) -> dict | None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE recommendations
                        SET status = 'VIEWED', viewed_at = now(), updated_at = now()
                        WHERE id = :rid AND user_id = :user_id AND status = 'PUBLISHED'
                        """
                    ),
                    {"rid": recommendation_id, "user_id": user_id},
                )
        return await self.get_recommendation(user_id, recommendation_id)

    async def reject(self, user_id: int, recommendation_id: int, reason: str) -> dict:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        UPDATE recommendations
                        SET status = 'REJECTED', rejection_reason = :reason,
                            decided_at = now(), updated_at = now()
                        WHERE id = :rid AND user_id = :user_id
                          AND status IN ('PUBLISHED', 'VIEWED')
                        RETURNING id
                        """
                    ),
                    {"rid": recommendation_id, "user_id": user_id, "reason": reason},
                )
                if result.first() is None:
                    raise BusinessRuleError("Bu oneri artik reddedilemez.")
        return await self.get_recommendation(user_id, recommendation_id) or {}

    async def attach_order(self, user_id: int, recommendation_id: int, order_id: int) -> dict:
        """BR-AUT-08: bir oneri EN FAZLA bir emir dogurur.

        Kosuldaki `order_id IS NULL` ve tablodaki tekil kisit birlikte calisir:
        ilki yarisi es zamanli ikinci onayi eler, ikincisi veritabani
        seviyesinde son sozu soyler.
        """
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        UPDATE recommendations
                        SET status = 'CONVERTED', order_id = :order_id,
                            decided_at = now(), updated_at = now()
                        WHERE id = :rid AND user_id = :user_id
                          AND order_id IS NULL
                          AND status IN ('PUBLISHED', 'VIEWED', 'APPROVED')
                        RETURNING id
                        """
                    ),
                    {"rid": recommendation_id, "user_id": user_id, "order_id": order_id},
                )
                if result.first() is None:
                    raise BusinessRuleError("Bu oneri zaten bir emre donusmus.")
        return await self.get_recommendation(user_id, recommendation_id) or {}

    async def expire_due(self, now=None) -> int:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        UPDATE recommendations
                        SET status = 'EXPIRED', updated_at = now()
                        WHERE status IN ('PUBLISHED', 'VIEWED') AND expires_at <= now()
                        RETURNING id
                        """
                    )
                )
                return len(result.fetchall())

    async def halt_open(self, reason: str) -> int:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        UPDATE recommendations
                        SET status = 'HALTED', updated_at = now()
                        WHERE status IN ('PUBLISHED', 'VIEWED')
                        RETURNING id
                        """
                    )
                )
                return len(result.fetchall())

    # ---------------- denetim ----------------

    async def log_audit(self, record: dict) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO recommendation_audit (
                            recommendation_id, user_id, event_type, actor,
                            old_status, new_status, reason, detail
                        ) VALUES (
                            :recommendation_id, :user_id, :event_type, :actor,
                            :old_status, :new_status, :reason, CAST(:detail AS JSONB)
                        )
                        """
                    ),
                    {
                        "recommendation_id": record.get("recommendation_id"),
                        "user_id": record.get("user_id"),
                        "event_type": record["event_type"],
                        "actor": record.get("actor", "SYSTEM"),
                        "old_status": record.get("old_status"),
                        "new_status": record.get("new_status"),
                        "reason": record.get("reason"),
                        "detail": _json(record.get("detail") or {}),
                    },
                )


class SqlNotificationRepository(_SqlRepository):
    """`notification_outbox` okuma ve kapatma.

    Satirlari YAZAN taraf burasi degil `SqlTradingRepository`dir (bildirim,
    gerceklesmeyle ayni transaction'da yazilir). Burasi bekleyenleri alip
    sonucu isler.
    """

    async def claim_pending(self, limit: int, max_attempts: int = 5) -> list[dict]:
        """Bekleyenleri alir ve deneme sayacini artirir.

        `FOR UPDATE SKIP LOCKED`: ayni anda birden fazla surec (ornegin iki
        uygulama ornegi) calisirsa ayni satir iki kez gonderilmez; kilitli
        satir beklenmeden atlanir.

        Sayac ONCEDEN artirilir. Surec gonderim sirasinda cokerse satir
        PENDING kalir ve tekrar denenir - ama sonsuza kadar degil, cunku
        `attempts` her denemede artar ve `max_attempts`e ulasinca artik
        alinmaz (dispatcher onu FAILED olarak kapatir).
        """
        # `_rows()` KULLANILMAZ: o yardimci commit etmez ve bu bir YAZMA
        # sorgusudur - sayac artisi geri alinirdi.
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        WITH secilen AS (
                            SELECT id FROM notification_outbox
                            WHERE status = 'PENDING' AND attempts < :max_attempts
                            ORDER BY created_at
                            LIMIT :limit
                            FOR UPDATE SKIP LOCKED
                        )
                        UPDATE notification_outbox o
                        SET attempts = o.attempts + 1
                        FROM secilen
                        WHERE o.id = secilen.id
                        RETURNING o.id, o.user_id, o.order_id, o.event_type,
                                  o.channel, o.recipient, o.payload,
                                  o.attempts, o.created_at
                        """
                    ),
                    {"limit": limit, "max_attempts": max_attempts},
                )
                return [dict(row) for row in result.mappings().all()]

    async def mark(self, outbox_id: int, status: str, error: str | None = None) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE notification_outbox
                        SET status = :status, last_error = :error, processed_at = now()
                        WHERE id = :outbox_id
                        """
                    ),
                    {"status": status, "error": error, "outbox_id": outbox_id},
                )

    async def list_for_user(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self._rows(
            """
            SELECT id, order_id, event_type, channel, status, payload,
                   created_at, processed_at
            FROM notification_outbox
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )


class SqlRagRepository(_SqlRepository):
    """Haber/rapor arama.

    Iki arama yolu vardir:
      * `search()`        - yalnizca BM25 (tam eslesme/`content_tsv`).
      * `hybrid_search()`  - dense (anlamsal) + BM25 -> RRF (`rag.hybrid_search`).
        `rag_search` MCP tool'unun cagirdigi BIRINCIL yoldur.

    `hybrid_search()` `search()`'in YERINE GECMEZ, UZERINE KURULUR: embedder
    enjekte edilmediyse (`EMBEDDING_API_KEY`/`EMBEDDING_MODEL` tanimli degil)
    ya da sorgu-zamani embedding cagrisi basarisiz/zaman asimina ugrarsa
    dogrudan `search()`'e (BM25) duser - istek asla coker, yalnizca dense ayak
    devre disi kalir. Bu yuzden `search()` bagimsiz, kalici bir sozlesme
    olarak kalir (mimari v4 bolum 16, madde 1; roadmap Faz 4+5).

    BM25 sorgusunda `plainto_tsquery`'nin AND davranisi OR'a cevrilir: dogal
    dildeki bir sorunun TUM kelimelerinin ayni chunk'ta gecmesi neredeyse
    imkansizdir; cevrilmezse arama sessizce bos doner (db/README.md).

    ALAKA ESIGI (`settings.rag_min_similarity`)
    -------------------------------------------
    OR'lama aramayi calisir kilar ama BEDELI vardir: tek bir genel kelime
    ("sektor") alakasiz dokumanlari aday havuzuna sokar. Donen `score` bunu
    ayiklamaya YETMEZ - RRF rank tabanlidir, 1. sira alakasiz olsa da ayni
    degeri alir. Bu yuzden `hybrid_search()` ayrica gercek kosinus benzerligini
    (`cos_sim`) doner ve esigin altindakileri `rag.hybrid_search`'un ICINDE,
    `LIMIT`ten ONCE eler.

    Esik YALNIZCA bu yolda islenir; `search()` (BM25) yolunda karsilastirilacak
    vektor olmadigi icin uygulanamaz.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedder: Embedder | None = None,
    ) -> None:
        super().__init__(session_factory)
        self._embedder = embedder

    async def search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        return await self._rows(
            """
            WITH q AS (
                SELECT NULLIF(replace(plainto_tsquery('turkish', :query)::TEXT,
                                      ' & ', ' | '), '')::tsquery AS tsq
            )
            SELECT c.id AS chunk_id, d.external_id AS doc_id, d.baslik, d.sirket,
                   a.symbol,
                   to_char(d.tarih, 'YYYY-MM-DD') AS tarih, d.tip,
                   d.kaynak_url,
                   c.content,
                   ts_rank_cd(c.content_tsv, q.tsq) AS score
            FROM rag.chunks c
            JOIN rag.documents d ON d.id = c.document_id
            LEFT JOIN assets a   ON a.id = d.asset_id
            CROSS JOIN q
            WHERE q.tsq IS NOT NULL
              AND c.content_tsv @@ q.tsq
              -- `d.sirket` KULLANILMAZ: bu kolon haberin KAYNAGINI tutar
              -- ("AA Ekonomi", "BigPara Doviz"), haberin KONUSU olan
              -- sirketi degil (bkz. embedding pipeline oturum notlari,
              -- 2026-08-19). Sirket filtresi bu yuzden yalnizca `assets`
              -- join'ine (SEMBOL - "THYAO" - ve UNVAN - "Turk Hava
              -- Yollari") ve baslik fallback'ine bakar; `rag.hybrid_search()`
              -- ile ayni desen.
              AND (CAST(:sirket AS TEXT) IS NULL
                   OR upper(a.symbol) = upper(:sirket)
                   OR upper(a.name) = upper(:sirket)
                   OR d.baslik ILIKE '%' || :sirket || '%')
              AND (CAST(:tip AS TEXT) IS NULL OR d.tip = :tip)
              AND (CAST(:date_from AS DATE) IS NULL OR d.tarih >= CAST(:date_from AS DATE))
              AND (CAST(:date_to AS DATE) IS NULL OR d.tarih <= CAST(:date_to AS DATE))
            ORDER BY score DESC
            LIMIT :top_k
            """,
            {
                "query": query,
                "sirket": sirket,
                "tip": tip,
                "date_from": date_from,
                "date_to": date_to,
                "top_k": top_k,
            },
        )

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        if self._embedder is None:
            logger.debug("embedder baglanmadi; BM25'e dusuluyor")
            return await self.search(
                query, top_k=top_k, sirket=sirket, tip=tip, date_from=date_from, date_to=date_to
            )

        try:
            embedding = await asyncio.wait_for(
                self._embedder.embed_query(query),
                timeout=settings.rag_query_embedding_timeout_seconds,
            )
        except Exception:  # noqa: BLE001 - embedding basarisiz olsa da arama COKMEMELI
            logger.warning(
                "sorgu embedding'i basarisiz/zaman asimina ugradi; BM25'e dusuluyor",
                exc_info=True,
            )
            return await self.search(
                query, top_k=top_k, sirket=sirket, tip=tip, date_from=date_from, date_to=date_to
            )

        # `rag.hybrid_search()` `document_id`/`sirket` (KAYNAK) doner - `doc_id`
        # (external_id) ve `symbol` icin `rag.documents`/`assets`'e geri
        # JOIN edilir; boylece donus sekli `search()` ile BIREBIR aynidir
        # (`_chunk_payload` ikisini ayirt etmeden isler).
        #
        # Isimli parametreler (`p_x => ...`) KULLANILIR: `p_asset_id` ve
        # `p_k_rrf` varsayilanlarinda birakilir, pozisyonel cagrida aralarina
        # NULL yazmaya gerek kalmaz.
        #
        # `:embedding` icin ACIK `CAST(... AS vector)` ZORUNLUDUR - aksi
        # halde SQLAlchemy/psycopg parametreyi `double precision[]` olarak
        # gonderir ve Postgres fonksiyon overload'unu bulamaz (bkz. embedding
        # pipeline oturum notlari, 2026-08-19/20 - ayni hata local'de
        # `rag.hybrid_search`'u dogrudan cagirirken de yasanmisti).
        # ASGARI BENZERLIK ESIGI: `0` kapali demektir ve SQL tarafina NULL gider
        # (fonksiyon NULL'da hicbir satir elemez). Esik SQL'in ICINDE, `LIMIT`ten
        # ONCE uygulanir - Python'da sonradan filtrelemek `top_k` satirin bir
        # kismini silip geriye cok az sonuc birakirdi; SQL'de elenenlerin yeri
        # aday havuzunun derinliginden dolar.
        esik = settings.rag_min_similarity
        return await self._rows(
            """
            SELECT hs.chunk_id, d.external_id AS doc_id, hs.baslik, hs.sirket,
                   a.symbol, to_char(hs.tarih, 'YYYY-MM-DD') AS tarih, hs.tip,
                   -- `kaynak_url` `hybrid_search()`'un donus tipinde YOKTUR;
                   -- zaten var olan `rag.documents` join'inden alinir.
                   d.kaynak_url,
                   hs.content, hs.score, hs.cos_sim
            FROM rag.hybrid_search(
                     p_query     => CAST(:query AS TEXT),
                     p_embedding => CAST(:embedding AS vector),
                     p_top_k     => CAST(:top_k AS INT),
                     p_sirket    => CAST(:sirket AS TEXT),
                     p_tip       => CAST(:tip AS TEXT),
                     p_date_from => CAST(:date_from AS DATE),
                     p_date_to   => CAST(:date_to AS DATE),
                     p_min_cos   => CAST(:min_cos AS DOUBLE PRECISION)
                 ) hs
            JOIN rag.documents d ON d.id = hs.document_id
            LEFT JOIN assets a   ON a.id = d.asset_id
            ORDER BY hs.score DESC
            """,
            {
                "query": query,
                "embedding": embedding,
                "top_k": top_k,
                "sirket": sirket,
                "tip": tip,
                "date_from": date_from,
                "date_to": date_to,
                "min_cos": esik if esik > 0 else None,
            },
        )

    async def list_news(self, limit: int = 20, kategori: str | None = None) -> list[dict]:
        return await self._rows(
            """
            SELECT d.id, d.baslik, d.sirket, a.symbol,
                   to_char(d.tarih, 'YYYY-MM-DD') AS tarih, d.tip, d.kategori,
                   d.kaynak_url, d.raw_text, d.image_url
            FROM rag.documents d
            LEFT JOIN assets a ON a.id = d.asset_id
            WHERE CAST(:kategori AS TEXT) IS NULL OR d.kategori = :kategori
            ORDER BY d.tarih DESC NULLS LAST, d.id DESC
            LIMIT :limit
            """,
            {"kategori": kategori, "limit": limit},
        )

    async def set_news_image(self, document_id: int, image_url: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("UPDATE rag.documents SET image_url = :image_url WHERE id = :id"),
                {"id": document_id, "image_url": image_url},
            )
            await session.commit()


class SqlChatRepository(_SqlRepository):
    async def list_sessions(self, user_id: int, limit: int = 50) -> list[dict]:
        return await self._rows(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   (SELECT count(*) FROM chat_messages m WHERE m.session_id = s.id)
                       AS message_count
            FROM chat_sessions s
            WHERE s.user_id = :user_id
            ORDER BY s.updated_at DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )

    async def create_session(self, user_id: int, title: str) -> dict:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO chat_sessions (user_id, title)
                    VALUES (:user_id, :title)
                    RETURNING id, title, created_at, updated_at
                    """
                ),
                {"user_id": user_id, "title": title[:100]},
            )
            await session.commit()
            return dict(result.mappings().one())

    async def get_session(self, session_id: int, user_id: int) -> dict | None:
        return await self._row(
            """
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            WHERE id = :session_id AND user_id = :user_id
            """,
            {"session_id": session_id, "user_id": user_id},
        )

    async def list_messages(self, session_id: int, limit: int = 200) -> list[dict]:
        return await self._rows(
            """
            SELECT id, session_id, sender_role, message_content, meta,
                   request_id, created_at
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY created_at, id
            LIMIT :limit
            """,
            {"session_id": session_id, "limit": limit},
        )

    async def add_message(
        self,
        session_id: int,
        sender_role: str,
        content: str,
        meta: dict | None = None,
        request_id: str | None = None,
    ) -> dict:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO chat_messages
                        (session_id, sender_role, message_content, meta, request_id)
                    VALUES
                        (:session_id, :sender_role, :content, CAST(:meta AS JSONB),
                         CAST(NULLIF(:request_id, '') AS UUID))
                    RETURNING id, session_id, sender_role, message_content, meta,
                              request_id, created_at
                    """
                ),
                {
                    "session_id": session_id,
                    "sender_role": sender_role,
                    "content": content,
                    "meta": _json(meta or {}),
                    "request_id": request_id or "",
                },
            )
            await session.execute(
                text("UPDATE chat_sessions SET updated_at = now() WHERE id = :session_id"),
                {"session_id": session_id},
            )
            await session.commit()
            return dict(result.mappings().one())

    async def message_owner_id(self, message_id: int) -> int | None:
        satir = await self._row(
            """
            SELECT s.user_id
            FROM chat_messages m
            JOIN chat_sessions s ON s.id = m.session_id
            WHERE m.id = :message_id
            """,
            {"message_id": message_id},
        )
        return int(satir["user_id"]) if satir else None


class SqlAuditRepository(_SqlRepository):
    """`tool_calls` ve `security_events` yazimi.

    Denetim kaydi istegi DUSURMEZ: yazma basarisiz olursa hata loglanip
    yutulur. Denetim onemli ama kullanicinin sohbetinden daha onemli degil.
    """

    async def log_tool_call(self, record: dict) -> None:
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO tool_calls (request_id, session_id, user_id, agent_name,
                                                tool_name, args, success, latency_ms, error)
                        VALUES (CAST(:request_id AS UUID), :session_id, :user_id, :agent_name,
                                :tool_name, CAST(:args AS JSONB), :success, :latency_ms, :error)
                        """
                    ),
                    {**record, "args": _json(record.get("args") or {})},
                )
                await session.commit()
        except Exception:  # noqa: BLE001 - denetim yazimi akisi durdurmamali
            logger.exception("tool_calls kaydi yazilamadi")

    async def log_security_event(self, record: dict) -> None:
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO security_events (request_id, user_id, phase, flags,
                                                     risk_score, action, excerpt)
                        VALUES (CAST(:request_id AS UUID), :user_id, :phase, :flags,
                                :risk_score, :action, :excerpt)
                        """
                    ),
                    record,
                )
                await session.commit()
        except Exception:  # noqa: BLE001
            logger.exception("security_events kaydi yazilamadi")


class SqlLeadRepository(_SqlRepository):
    """Lead motoru veri erisimi (`lead_scans`, `lead_queue_entries`,
    `lead_contacts`, `v_lead_user_signals`).
    """

    async def list_lead_signals(self) -> list[dict]:
        return await self._rows("SELECT * FROM v_lead_user_signals")

    async def last_contacted_map(self, cooldown_days: int) -> dict[int, Any]:
        rows = await self._rows(
            """
            SELECT user_id, MAX(created_at) AS last_contact_at
            FROM lead_contacts
            WHERE channel = 'EMAIL'
              AND status = 'SENT'
              AND created_at >= now() - make_interval(days => CAST(:cooldown_days AS INT))
            GROUP BY user_id
            """,
            {"cooldown_days": cooldown_days},
        )
        return {row["user_id"]: row["last_contact_at"] for row in rows}

    async def start_scan(self, trigger: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                text("INSERT INTO lead_scans (trigger) VALUES (:trigger) RETURNING id"),
                {"trigger": trigger},
            )
            await session.commit()
            return int(result.scalar_one())

    async def finish_scan(
        self, scan_id: int, counts: dict[str, int], error: str | None = None
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE lead_scans
                    SET finished_at = now(),
                        scanned_count = :scanned_count,
                        bsd_count = :bsd_count,
                        autonomous_count = :autonomous_count,
                        excluded_count = :excluded_count,
                        emailed_count = :emailed_count,
                        error = :error
                    WHERE id = :scan_id
                    """
                ),
                {
                    "scan_id": scan_id,
                    "scanned_count": counts.get("scanned_count", 0),
                    "bsd_count": counts.get("bsd_count", 0),
                    "autonomous_count": counts.get("autonomous_count", 0),
                    "excluded_count": counts.get("excluded_count", 0),
                    "emailed_count": counts.get("emailed_count", 0),
                    "error": error,
                },
            )
            await session.commit()

    async def latest_scan(self) -> dict | None:
        return await self._row(
            """
            SELECT * FROM lead_scans
            WHERE finished_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 1
            """
        )

    async def minutes_since_last_scan(self) -> float | None:
        row = await self._row(
            """
            SELECT EXTRACT(EPOCH FROM (now() - MAX(finished_at))) / 60 AS dakika
            FROM lead_scans
            WHERE finished_at IS NOT NULL
            """
        )
        return float(row["dakika"]) if row and row["dakika"] is not None else None

    async def record_decision(self, scan_id: int, entry: dict) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO lead_queue_entries
                        (scan_id, user_id, decision, exclusion_reason, score,
                         score_components, reasons, total_value_try, monthly_income,
                         likit_para, days_since_activity)
                    VALUES
                        (:scan_id, :user_id, :decision, :exclusion_reason, :score,
                         CAST(:score_components AS JSONB), CAST(:reasons AS JSONB),
                         :total_value_try, :monthly_income, :likit_para,
                         :days_since_activity)
                    """
                ),
                {
                    "scan_id": scan_id,
                    "user_id": entry["user_id"],
                    "decision": entry["decision"],
                    "exclusion_reason": entry.get("exclusion_reason"),
                    "score": entry.get("score", 0),
                    "score_components": _json(entry.get("score_components") or {}),
                    "reasons": _json(entry.get("reasons") or []),
                    "total_value_try": entry.get("total_value_try", 0),
                    "monthly_income": entry.get("monthly_income", 0),
                    "likit_para": entry.get("likit_para", 0),
                    "days_since_activity": entry.get("days_since_activity"),
                },
            )
            await session.commit()

    async def claim_email_contact(
        self, user_id: int, scan_id: int, to_email: str, subject: str
    ) -> int | None:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO lead_contacts (user_id, scan_id, channel, status, to_email, subject)
                    VALUES (:user_id, :scan_id, 'EMAIL', 'SENT', :to_email, :subject)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """
                ),
                {"user_id": user_id, "scan_id": scan_id, "to_email": to_email, "subject": subject},
            )
            await session.commit()
            row = result.first()
            return int(row[0]) if row else None

    async def mark_contact_failed(self, contact_id: int, error: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("UPDATE lead_contacts SET status = 'FAILED', error = :error WHERE id = :id"),
                {"id": contact_id, "error": error},
            )
            await session.commit()

    async def mark_contact_skipped(self, contact_id: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("UPDATE lead_contacts SET status = 'SKIPPED' WHERE id = :id"),
                {"id": contact_id},
            )
            await session.commit()

    async def list_queue(self, decision: str, limit: int = 100) -> list[dict]:
        return await self._rows(
            """
            SELECT q.user_id, u.first_name, u.last_name, u.email,
                   u.phone_number, u.birth_date, u.tckn_last4,
                   q.decision, q.exclusion_reason, q.score, q.score_components,
                   q.reasons, q.total_value_try, q.monthly_income, q.likit_para,
                   q.days_since_activity, q.created_at
            FROM lead_queue_entries q
            JOIN users u ON u.id = q.user_id
            WHERE q.decision = :decision
              AND q.scan_id = (
                    SELECT id FROM lead_scans
                    WHERE finished_at IS NOT NULL
                    ORDER BY started_at DESC LIMIT 1
                  )
            ORDER BY q.score DESC
            LIMIT :limit
            """,
            {"decision": decision, "limit": limit},
        )

    async def list_emailed(self, days: int, limit: int = 100) -> list[dict]:
        # Skor/bakiye bilgisi mailin gonderildigi TARAMANIN karar satirindan
        # gelir (LEFT JOIN): temas kaydi kalicidir, o taramanin satiri
        # silinmis olsa bile satir dusmez.
        return await self._rows(
            """
            SELECT * FROM (
                SELECT DISTINCT ON (c.user_id)
                       c.user_id, u.first_name, u.last_name, u.email,
                       u.phone_number, u.birth_date, u.tckn_last4,
                       'AUTONOMOUS' AS decision,
                       CAST(NULL AS VARCHAR) AS exclusion_reason,
                       COALESCE(q.score, 0) AS score,
                       COALESCE(q.score_components, '{}'::jsonb) AS score_components,
                       COALESCE(q.reasons, '[]'::jsonb) AS reasons,
                       COALESCE(q.total_value_try, 0) AS total_value_try,
                       COALESCE(q.monthly_income, 0) AS monthly_income,
                       COALESCE(q.likit_para, 0) AS likit_para,
                       q.days_since_activity,
                       c.created_at
                FROM lead_contacts c
                JOIN users u ON u.id = c.user_id
                LEFT JOIN lead_queue_entries q
                       ON q.scan_id = c.scan_id AND q.user_id = c.user_id
                WHERE c.channel = 'EMAIL'
                  AND c.status = 'SENT'
                  AND c.created_at >= now() - make_interval(days => CAST(:days AS INT))
                ORDER BY c.user_id, c.created_at DESC
            ) t
            ORDER BY t.created_at DESC
            LIMIT :limit
            """,
            {"days": days, "limit": limit},
        )


class SqlEconomicCalendarRepository(_SqlRepository):
    async def list_events(self, start: date, end: date) -> list[dict]:
        return await self._rows(
            """
            SELECT event_date, event_time, country, event_name, importance, source,
                   expected, actual, previous
            FROM economic_events
            WHERE event_date BETWEEN :start AND :end
            ORDER BY event_date
            """,
            {"start": start, "end": end},
        )


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)


class SqlContestRepository(_SqlRepository):
    """Sans Yatirimda oyunu (`db/v5_schema_and_data.sql` 7B bolumu).

    Rakip simulasyonu (isim/skor/yuzde) icin sorgu YOK - bkz.
    base.py::ContestRepository. `answer.is_correct` / `points_earned`
    servis katmanindan HAZIR gelir, burada hesaplanmaz.
    """

    async def get_active_contest(self) -> dict | None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO contest (contest_date, starts_at)
                        VALUES (
                            CURRENT_DATE,
                            (CURRENT_DATE::timestamp + TIME '20:00')
                                AT TIME ZONE 'Europe/Istanbul'
                        )
                        ON CONFLICT (contest_date) DO NOTHING
                        """
                    )
                )
                result = await session.execute(
                    text(
                        """
                        SELECT id, contest_date, starts_at, capacity_total,
                               prize_pool_points, question_count, created_at
                        FROM contest
                        WHERE contest_date = CURRENT_DATE
                        FOR UPDATE
                        """
                    )
                )
                contest = result.mappings().one()
                await session.execute(
                    text(
                        """
                        INSERT INTO contest_topic (contest_id, topic_id, sort_order)
                        SELECT :contest_id, t.id,
                               row_number() OVER (ORDER BY t.id)::smallint
                        FROM topic t
                        ON CONFLICT (contest_id, topic_id) DO NOTHING
                        """
                    ),
                    {"contest_id": contest["id"]},
                )
                await session.execute(
                    text(
                        """
                        INSERT INTO contest_question (
                            contest_id, question_id, sort_order
                        )
                        SELECT :contest_id, selected.id,
                               row_number() OVER (ORDER BY selected.selection_order)::smallint
                        FROM (
                            SELECT q.id,
                                   (q.id + EXTRACT(DOY FROM CURRENT_DATE)::integer)
                                       % GREATEST((SELECT count(*) FROM question), 1)
                                       AS selection_order
                            FROM question q
                            ORDER BY selection_order, q.id
                            LIMIT :question_count
                        ) selected
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "contest_id": contest["id"],
                        "question_count": contest["question_count"],
                    },
                )
                return dict(contest)

    async def get_contest_topics(self, contest_id: int) -> list[dict]:
        return await self._rows(
            """
            SELECT t.id, t.title_tr, t.title_en, t.body_tr, t.body_en
            FROM contest_topic ct
            JOIN topic t ON t.id = ct.topic_id
            WHERE ct.contest_id = :contest_id
            ORDER BY ct.sort_order
            """,
            {"contest_id": contest_id},
        )

    async def get_contest_questions(self, contest_id: int) -> list[dict]:
        return await self._rows(
            """
            SELECT cq.id AS contest_question_id, cq.sort_order,
                   q.id, q.topic_id, q.text_tr, q.text_en, q.options,
                   q.correct_index, q.education_note_tr, q.education_note_en,
                   q.difficulty, q.timer_seconds
            FROM contest_question cq
            JOIN question q ON q.id = cq.question_id
            WHERE cq.contest_id = :contest_id
            ORDER BY cq.sort_order
            """,
            {"contest_id": contest_id},
        )

    async def has_agreement(self, user_id: int) -> bool:
        row = await self._row(
            "SELECT 1 AS x FROM contest_agreement WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        return row is not None

    async def create_agreement(self, user_id: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO contest_agreement (user_id)
                    VALUES (:user_id)
                    ON CONFLICT (user_id) DO NOTHING
                    """
                ),
                {"user_id": user_id},
            )
            await session.commit()

    async def count_participants(self, contest_id: int) -> int:
        row = await self._row(
            "SELECT count(*) AS n FROM participation WHERE contest_id = :contest_id",
            {"contest_id": contest_id},
        )
        return int(row["n"]) if row else 0

    async def register_participation(self, contest_id: int, user_id: int) -> dict:
        """`UNIQUE (user_id, contest_date)` kisitina dayanir - once-SELECT-sonra-
        INSERT yerine `ON CONFLICT DO NOTHING RETURNING` kullanilir (bkz.
        `claim_email_contact`'teki ayni desen); boylece iki es zamanli istek
        arasinda yaris durumu (race condition) olmaz."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO participation (contest_id, user_id, contest_date)
                    VALUES (:contest_id, :user_id, CURRENT_DATE)
                    ON CONFLICT (user_id, contest_date) DO NOTHING
                    RETURNING id, contest_id, user_id, contest_date, registered_at,
                              eliminated_at_question, final_score, won
                    """
                ),
                {"contest_id": contest_id, "user_id": user_id},
            )
            row = result.mappings().first()
            await session.commit()
            if row is None:
                raise BusinessRuleError("Bugun icin katilim hakkini zaten kullandin.")
            return dict(row)

    async def get_participation(self, participation_id: int) -> dict | None:
        return await self._row(
            """
            SELECT id, contest_id, user_id, contest_date, registered_at,
                   eliminated_at_question, final_score, won
            FROM participation
            WHERE id = :participation_id
            """,
            {"participation_id": participation_id},
        )

    async def reset_todays_participation(self, user_id: int) -> None:
        # `answer`/`payout` -> participation ON DELETE CASCADE (bkz. schema),
        # tek DELETE ucu de siler.
        async with self._session_factory() as session:
            await session.execute(
                text(
                    (
                        "DELETE FROM participation WHERE user_id = :user_id AND "
                        "contest_date = CURRENT_DATE"
                    )
                ),
                {"user_id": user_id},
            )
            await session.commit()

    async def submit_answer(
        self,
        participation_id: int,
        contest_question_id: int,
        selected_index: int | None,
        is_correct: bool,
        points_earned: int,
        elapsed_seconds: float,
    ) -> dict:
        # NOT: `answer` tablosunda `elapsed_seconds` kolonu yok (bkz. schema);
        # servis bunu yalnizca `points_earned` hesabi icin kullanir, ayrica
        # saklanmaz. Parametre yine de aliniyor ki Protocol iki implementasyonda
        # da AYNI imzaya sahip olsun.
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO answer (
                        participation_id, contest_question_id, selected_index,
                        is_correct, points_earned
                    ) VALUES (
                        :participation_id, :contest_question_id, :selected_index,
                        :is_correct, :points_earned
                    )
                    RETURNING id, participation_id, contest_question_id, selected_index,
                              is_correct, points_earned, answered_at
                    """
                ),
                {
                    "participation_id": participation_id,
                    "contest_question_id": contest_question_id,
                    "selected_index": selected_index,
                    "is_correct": is_correct,
                    "points_earned": points_earned,
                },
            )
            row = result.mappings().one()
            await session.commit()
            return dict(row)

    async def list_answers(self, participation_id: int) -> list[dict]:
        return await self._rows(
            """
            SELECT a.id, a.participation_id, a.contest_question_id, a.selected_index,
                   a.is_correct, a.points_earned, a.answered_at
            FROM answer a
            JOIN contest_question cq ON cq.id = a.contest_question_id
            WHERE a.participation_id = :participation_id
            ORDER BY cq.sort_order
            """,
            {"participation_id": participation_id},
        )

    async def finalize_participation(
        self,
        participation_id: int,
        won: bool,
        final_score: int,
        eliminated_at_question: int | None,
    ) -> dict:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    UPDATE participation
                    SET won = :won, final_score = :final_score,
                        eliminated_at_question = :eliminated_at_question
                    WHERE id = :participation_id
                    RETURNING id, contest_id, user_id, contest_date, registered_at,
                              eliminated_at_question, final_score, won
                    """
                ),
                {
                    "participation_id": participation_id,
                    "won": won,
                    "final_score": final_score,
                    "eliminated_at_question": eliminated_at_question,
                },
            )
            row = result.mappings().first()
            await session.commit()
            if row is None:
                raise NotFoundError("Katilim bulunamadi.")
            return dict(row)

    async def create_payout(self, participation_id: int, payout_points: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO payout (participation_id, points_awarded)
                    VALUES (:participation_id, :points_awarded)
                    ON CONFLICT (participation_id) DO NOTHING
                    """
                ),
                {"participation_id": participation_id, "points_awarded": payout_points},
            )
            await session.commit()

    async def get_leaderboard(self, period: str) -> list[dict]:
        days = {"gunluk": 1, "haftalik": 7}.get(period)
        return await self._rows(
            """
            SELECT row_number() OVER (ORDER BY p.final_score DESC) AS rank,
                   u.first_name || ' ' || u.last_name AS label,
                   p.final_score AS score
            FROM participation p
            JOIN users u ON u.id = p.user_id
            WHERE CAST(:days AS INT) IS NULL
               OR p.registered_at >= now() - make_interval(days => CAST(:days AS INT))
            ORDER BY p.final_score DESC
            LIMIT 50
            """,
            {"days": days},
        )

    async def list_participations(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self._rows(
            """
            SELECT p.id, p.contest_id, p.user_id, p.contest_date, p.registered_at,
                   p.eliminated_at_question, p.final_score, p.won,
                   COALESCE(pay.points_awarded, 0) AS points_awarded
            FROM participation p
            LEFT JOIN payout pay ON pay.participation_id = p.id
            WHERE p.user_id = :user_id
            ORDER BY p.registered_at DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )

    async def get_points_balance(self, user_id: int) -> int:
        row = await self._row(
            """
            SELECT
                COALESCE((
                    SELECT sum(pay.points_awarded)
                    FROM payout pay
                    JOIN participation p ON p.id = pay.participation_id
                    WHERE p.user_id = :user_id
                ), 0)
                - COALESCE((
                    SELECT sum(price_points) FROM powerup_purchase WHERE user_id = :user_id
                ), 0)
                - COALESCE((
                    SELECT sum(price_points) FROM donation_purchase WHERE user_id = :user_id
                ), 0) AS balance
            """,
            {"user_id": user_id},
        )
        return int(row["balance"]) if row else 0

    async def get_user_powerups(self, user_id: int) -> dict[str, int]:
        rows = await self._rows(
            "SELECT kind, quantity FROM user_powerup WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        return {row["kind"]: row["quantity"] for row in rows}

    async def consume_powerup(self, user_id: int, kind: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    UPDATE user_powerup SET quantity = quantity - 1
                    WHERE user_id = :user_id AND kind = :kind AND quantity > 0
                    RETURNING id
                    """
                ),
                {"user_id": user_id, "kind": kind},
            )
            row = result.first()
            await session.commit()
            return row is not None

    async def record_powerup_purchase(self, user_id: int, kind: str, price_points: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO powerup_purchase (user_id, kind, price_points)
                    VALUES (:user_id, :kind, :price_points)
                    """
                ),
                {"user_id": user_id, "kind": kind, "price_points": price_points},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO user_powerup (user_id, kind, quantity)
                    VALUES (:user_id, :kind, 1)
                    ON CONFLICT (user_id, kind) DO UPDATE SET
                        quantity = user_powerup.quantity + 1
                    """
                ),
                {"user_id": user_id, "kind": kind},
            )
            await session.commit()

    async def list_powerup_purchases(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self._rows(
            """
            SELECT id, user_id, kind, price_points, purchased_at
            FROM powerup_purchase
            WHERE user_id = :user_id
            ORDER BY purchased_at DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )

    async def get_user_badges(self, user_id: int) -> list[str]:
        rows = await self._rows(
            "SELECT badge_label FROM donation_purchase WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        return [row["badge_label"] for row in rows]

    async def record_donation_purchase(
        self, user_id: int, donation_key: str, badge_label: str, price_points: int
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO donation_purchase (user_id, donation_key, badge_label, price_points)
                    VALUES (:user_id, :donation_key, :badge_label, :price_points)
                    ON CONFLICT (user_id, donation_key) DO NOTHING
                    """
                ),
                {
                    "user_id": user_id,
                    "donation_key": donation_key,
                    "badge_label": badge_label,
                    "price_points": price_points,
                },
            )
            await session.commit()

    async def list_donation_purchases(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self._rows(
            """
            SELECT id, user_id, donation_key, badge_label, price_points, purchased_at
            FROM donation_purchase
            WHERE user_id = :user_id
            ORDER BY purchased_at DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )
