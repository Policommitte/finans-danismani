-- =====================================================================
-- 017 - users: TCKN dogrulama alanlari (tckn_hash, tckn_last4, dogum
-- tarihi, telefon)
-- =====================================================================
--
-- NEDEN GEREKLI
--   Kayit formuna TC Kimlik No + NVI (Nufus ve Vatandaslik Isleri Genel
--   Mudurlugu) dogrulamasi eklendi (bkz. backend/app/api/routes/auth.py
--   -> POST /api/auth/register, backend/app/services/nvi.py). Dogrulanan
--   bilgiler kalici olarak saklanmali; TCKN KVKK kapsaminda ozel nitelikli
--   kisisel veridir, bu yuzden DUZ METIN DEGIL, tek yonlu bir ozet (HMAC-
--   SHA256, bkz. backend/app/core/tckn.py::hash_tckn) olarak yazilir.
--   Ekranlarda/normal sorgularda yalnizca son 4 hane (`tckn_last4`)
--   gosterilir; tam numara HICBIR API yanitinda donmez.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/017_users_tckn_verification.sql
--
-- GUVENLIK
--   Idempotenttir: kolonlar zaten varsa hicbir sey yapmaz. Tumu NULL
--   varsayilanla eklenir - MEVCUT (seed) kullanicilarin bu alanlari yoktur
--   ve backfill edilmez; yalnizca YENI kayitlar `create()` icinde doldurur.
--
--   `tckn_hash` DETERMINISTIKTIR (HMAC-SHA256 + sunucu tarafi pepper,
--   bcrypt DEGIL): ayni TCKN her zaman ayni hash'i uretir. Bu bilinçli bir
--   tercih - amac ayni kisinin farkli e-postalarla birden fazla hesap
--   acmasini asagidaki UNIQUE index ile engellemek. Pepper sunucu
--   tarafinda kaldigi surece hash tek yonludur (DB sizintisi tek basina
--   TCKN'i geri vermez).
-- =====================================================================

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS tckn_hash VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS tckn_last4 CHAR(4);
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);

CREATE UNIQUE INDEX IF NOT EXISTS users_tckn_hash_uidx
    ON users (tckn_hash) WHERE tckn_hash IS NOT NULL;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name, data_type FROM information_schema.columns
--    WHERE table_name = 'users'
--      AND column_name IN ('tckn_hash','tckn_last4','birth_date','phone_number')
--    ORDER BY column_name;
--   -> dort satir donmelidir.
--   SELECT count(*) FILTER (WHERE tckn_hash IS NOT NULL) AS dogrulanmis_kayit
--    FROM users;
--   -> yeni kayit olusturulmadan once 0 olmalidir.
