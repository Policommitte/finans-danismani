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

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings

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
                   risk_tolerance, monthly_income
            FROM users WHERE lower(email) = lower(:email)
            """,
            {"email": email},
        )

    async def get_by_id(self, user_id: int) -> dict | None:
        return await self._row(
            """
            SELECT id, first_name, last_name, email, risk_tolerance, monthly_income
            FROM users WHERE id = :user_id
            """,
            {"user_id": user_id},
        )


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
                   ) AS total_value_try
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
            SELECT ph.ts, ph.price
            FROM price_history ph
            JOIN assets a ON a.id = ph.asset_id
            WHERE upper(a.symbol) = upper(:symbol)
              AND ph.ts >= now() - make_interval(days => :days)
            ORDER BY ph.ts
            """,
            {"symbol": symbol, "days": days},
        )

    async def get_prices_for_simulation(self) -> list[dict]:
        return await self._rows(
            """
            SELECT id AS asset_id, symbol, current_price, sim_volatility
            FROM assets ORDER BY id
            """
        )

    async def apply_price_updates(
        self, updates: list[dict], write_live: bool, source: str = "simulated"
    ) -> int:
        """Fiyatlari gunceller; istenirse `live_prices`'a gun ici satir yazar.

        GECMIS TABLOSUNA (`price_history`) BURADAN YAZILMAZ. 15 dakikalik
        tick'ler dogrudan oraya aksaydi tablo gunde ~1.536 satirla siserdi;
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

        `source` cagiran tarafindan verilir ve GERCEKTEN kullanilan kaynagi
        belirtir: saglayici Yahoo'ya ulasamayip simulatore dustuyse "api"
        DEGIL "simulated" yazilir (bkz. `ApiMarketProvider.son_kaynak`).
        Etiket `live_prices` uzerinden gun sonunda `price_history`'ye tasinir.
        """
        if not updates:
            return 0

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


class SqlRagRepository(_SqlRepository):
    """Haber/rapor arama.

    ⚠️ EMBEDDING MODELI SECILMEDIGI SURECE (mimari v4 bolum 16, madde 1)
    hibrit aramanin DENSE ayagi calistirilamaz - sorgu vektore cevrilemez.
    Bu yuzden varsayilan yol yalnizca BM25'tir. Model secilip
    `EMBEDDING_MODEL` tanimlandiginda `rag.hybrid_search(...)` fonksiyonu
    devreye girer; SQL zaten hazirdir ve bu sinifta yalnizca bir dal acilir.

    BM25 sorgusunda `plainto_tsquery`'nin AND davranisi OR'a cevrilir: dogal
    dildeki bir sorunun TUM kelimelerinin ayni chunk'ta gecmesi neredeyse
    imkansizdir; cevrilmezse arama sessizce bos doner (db/README.md).
    """

    async def search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
    ) -> list[dict]:
        if settings.embedding_model:
            logger.debug("embedding modeli tanimli; hibrit arama dali acilabilir")

        return await self._rows(
            """
            WITH q AS (
                SELECT NULLIF(replace(plainto_tsquery('turkish', :query)::TEXT,
                                      ' & ', ' | '), '')::tsquery AS tsq
            )
            SELECT c.id AS chunk_id, d.external_id AS doc_id, d.baslik, d.sirket,
                   a.symbol,
                   to_char(d.tarih, 'YYYY-MM-DD') AS tarih, d.tip,
                   c.content,
                   ts_rank_cd(c.content_tsv, q.tsq) AS score
            FROM rag.chunks c
            JOIN rag.documents d ON d.id = c.document_id
            LEFT JOIN assets a   ON a.id = d.asset_id
            CROSS JOIN q
            WHERE q.tsq IS NOT NULL
              AND c.content_tsv @@ q.tsq
              -- Sirket filtresi hem SEMBOL hem UNVAN ile eslesir: ajanlar
              -- sorgudan sembol cikarir ("THYAO"), dokumanda ise unvan yazar
              -- ("Turk Hava Yollari"). Yalnizca unvana bakilsaydi ajanin her
              -- filtreli aramasi sessizce bos donerdi.
              AND (CAST(:sirket AS TEXT) IS NULL
                   OR upper(d.sirket) = upper(:sirket)
                   OR upper(a.symbol) = upper(:sirket)
                   OR upper(a.name) = upper(:sirket)
                   OR d.baslik ILIKE '%' || :sirket || '%')
              AND (CAST(:tip AS TEXT) IS NULL OR d.tip = :tip)
            ORDER BY score DESC
            LIMIT :top_k
            """,
            {"query": query, "sirket": sirket, "tip": tip, "top_k": top_k},
        )


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


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)
