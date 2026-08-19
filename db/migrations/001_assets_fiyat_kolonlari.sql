-- =====================================================================
-- 001 - assets tablosundaki fiyat kolonlarini tamamlar
-- =====================================================================
--
-- NEDEN GEREKLI
--   `db/v5_schema_and_data.sql` sifirdan kurulan bir veritabaninda bu uc
--   kolonu zaten yaratir. Ancak ekibin PAYLASILAN Supabase veritabani daha
--   eski bir semadan turedi ve 16 Agustos 2026'da bu kolonlar orada YOKTU.
--
--   Backend'in fiyat gorevi bu kolonlari opsiyonel saymaz, dogrudan kullanir:
--     * app/repositories/sql.py -> get_prices_for_simulation()  : sim_volatility
--     * app/repositories/sql.py -> apply_price_updates()        : prev_close,
--                                                                 price_updated_at
--   Kolonlar eksikse sorgular "UndefinedColumn" ile patlar. Hata
--   `run_price_scheduler` icinde yakalanip loglandigi icin uygulama AYAKTA
--   KALIR ama fiyatlar hic guncellenmez - yani ariza SESSIZDIR.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/001_assets_fiyat_kolonlari.sql
--
-- GUVENLIK
--   Tamamen idempotenttir: kolonlar zaten varsa hicbir sey yapmaz, veri
--   silmez, mevcut degerleri EZMEZ. Iki kez calistirmak zararsizdir.
-- =====================================================================

BEGIN;

-- 1) Eksik kolonlari ekle -------------------------------------------------
--    NOT NULL DEFAULT ile eklemek mevcut satirlari da doldurur; sim_volatility
--    simulatorun adim buyuklugudur ve NULL kalirsa saglayici 0.015'e duser.
ALTER TABLE assets ADD COLUMN IF NOT EXISTS prev_close       NUMERIC;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS price_updated_at TIMESTAMPTZ;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS sim_volatility   NUMERIC NOT NULL DEFAULT 0.0150;

-- 2) Yeni eklenen kolonlari makul baslangic degerleriyle doldur -----------
--    prev_close bos kalirsa daily_change_pct hesabi (bkz. apply_price_updates)
--    ilk tick'te calismaz. Mevcut fiyat ve gunluk degisimden geriye donuk
--    turetiyoruz - v5_schema_and_data.sql ile AYNI formul.
UPDATE assets
   SET prev_close = ROUND(current_price / (1 + COALESCE(daily_change_pct, 0) / 100.0), 4)
 WHERE prev_close IS NULL
   AND current_price IS NOT NULL;

UPDATE assets
   SET price_updated_at = now()
 WHERE price_updated_at IS NULL;

-- 3) Kota sayaci tablosu --------------------------------------------------
--    `market_api_usage` da eski semalarda olmayabilir. Backend bu tabloyu
--    gunluk Yahoo istek tavani icin kullanir; yoksa tavan devre disi kalir.
CREATE TABLE IF NOT EXISTS market_api_usage (
    usage_date   DATE PRIMARY KEY,
    call_count   INT NOT NULL DEFAULT 0,
    last_call_at TIMESTAMPTZ
);

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name FROM information_schema.columns
--    WHERE table_schema = 'public' AND table_name = 'assets'
--      AND column_name IN ('prev_close','price_updated_at','sim_volatility');
--   -> uc satir donmelidir.
