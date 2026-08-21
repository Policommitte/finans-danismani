-- =====================================================================
-- 002 - live_prices: gun ici canli fiyat tablosu
-- =====================================================================
--
-- NEDEN GEREKLI
--   Fiyat gorevi 15 dakikada bir calisiyor. Her tick `price_history`'ye
--   yazilinca tablo gunde ~1.536 satirla siserken grafikler icin gereken
--   cozunurluk gunluk kapanistir. Ekip bu yuzden Supabase'de `live_prices`
--   tablosunu ELLE yaratti; bu betik ayni tabloyu repoya tasir ve
--   backend'in ihtiyac duydugu eksikleri tamamlar.
--
--   Yeni akis:
--     her tick        -> live_prices'a INSERT      (gun ici)
--     gun bitince     -> gunun SON satiri price_history'ye kapanis olarak
--                        yazilir, o gune ait live_prices satirlari silinir
--   Gun siniri `MARKET_DAY_TIMEZONE` (varsayilan Europe/Istanbul) ile
--   belirlenir. Bkz. app/repositories/sql.py -> close_out_day().
--
-- ELLE YARATILAN TABLODA EKSIK OLANLAR
--   1. `source` kolonu YOK. Onsuz gun sonunda yazilan kapanis satirinin
--      gercek Yahoo verisi mi yoksa simulator yedegi mi oldugu ayirt
--      edilemez - yani sahte veri "api" etiketlenirdi.
--   2. `asset_id` NULL kabul ediyor. NULL asset_id'li satir price_history'ye
--      yazilamaz (NOT NULL) ve gunu asla kapanmayan bir artiga donusur.
--   3. `created_at` uzerinde indeks YOK. Gun kapanisi ve silme sorgulari
--      tam tarama yapar.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/002_live_prices.sql
--
-- GUVENLIK
--   Idempotenttir: hicbir satir SILMEZ, mevcut degerleri EZMEZ, iki kez
--   calistirmak zararsizdir. Tablo zaten varsa yalnizca eksikleri tamamlar.
-- =====================================================================

BEGIN;

-- 1) Tablo yoksa yarat (sifirdan kurulumlar icin; Supabase'de zaten var) ---
CREATE TABLE IF NOT EXISTS live_prices (
    id         SERIAL PRIMARY KEY,
    asset_id   INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    price      NUMERIC NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2) source kolonu --------------------------------------------------------
--    Varsayilan 'simulated': etiketsiz eski satirlar "gercek" sayilmaz.
--    Yanlis yonde hata yapmak (gercege sahte demek) tersinden guvenlidir.
ALTER TABLE live_prices
    ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'simulated';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'live_prices_source_check'
    ) THEN
        ALTER TABLE live_prices
            ADD CONSTRAINT live_prices_source_check
            CHECK (source IN ('simulated','api','backfill'));
    END IF;
END
$$;

-- 3) asset_id / created_at NOT NULL --------------------------------------
--    Yalnizca gercekten NULL satir YOKSA uygulanir; aksi halde betik
--    patlamak yerine o adimi atlar (idempotentlik bozulmasin).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM live_prices WHERE asset_id IS NULL) THEN
        ALTER TABLE live_prices ALTER COLUMN asset_id SET NOT NULL;
    ELSE
        RAISE NOTICE 'live_prices.asset_id NULL satir icerdigi icin NOT NULL yapilmadi';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM live_prices WHERE created_at IS NULL) THEN
        ALTER TABLE live_prices ALTER COLUMN created_at SET NOT NULL;
    ELSE
        RAISE NOTICE 'live_prices.created_at NULL satir icerdigi icin NOT NULL yapilmadi';
    END IF;
END
$$;

ALTER TABLE live_prices ALTER COLUMN created_at SET DEFAULT now();

-- 4) Indeksler ------------------------------------------------------------
--    (asset_id, created_at DESC) : gun kapanisindaki DISTINCT ON sorgusu
--    (created_at)                : gun araligina gore silme
CREATE INDEX IF NOT EXISTS live_prices_asset_created_idx
    ON live_prices (asset_id, created_at DESC);
CREATE INDEX IF NOT EXISTS live_prices_created_idx
    ON live_prices (created_at);

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name, is_nullable FROM information_schema.columns
--    WHERE table_schema = 'public' AND table_name = 'live_prices'
--    ORDER BY ordinal_position;
--   -> id, asset_id(NO), price(NO), created_at(NO), source(NO)
--
--   SELECT indexname FROM pg_indexes
--    WHERE tablename = 'live_prices';
--   -> live_prices_asset_created_idx ve live_prices_created_idx gorunmeli.
--
-- NOT: elle yaratilan `idx_live_prices_asset_id` indeksi
-- `live_prices_asset_created_idx` ile ayni isi gordugu icin gereksizdir;
-- silmek isterseniz (zorunlu degil):
--   DROP INDEX IF EXISTS idx_live_prices_asset_id;
