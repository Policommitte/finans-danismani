-- =====================================================================
-- 004 - users: onboarding_completed kolonu
-- =====================================================================
--
-- NEDEN GEREKLI
--   Yeni kayit olan kullanicilar ilk girislerinde zorunlu bir onboarding
--   akisindan (risk anketi -> sepet onerisi -> tanitim turu) gecirilecek.
--   Bu akisin sadece BIR KEZ gosterilmesi icin kullaniciya ait kalici bir
--   bayrak gerekiyor (backend/app/api/routes/auth.py -> /me, /onboarding/complete).
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/004_users_onboarding.sql
--
-- GUVENLIK
--   Idempotenttir: kolon zaten varsa hicbir sey yapmaz. DEFAULT true secildi
--   (backfill UPDATE'e gerek yok, tek deyim, MEVCUT KULLANICILAR onboarding'e
--   zorlanmaz). Yeni kayitlar backend'in `create()` metodunda acikca false
--   ile eklenir - bu dosya sadece semayi hazirlar, hicbir satiri false yapmaz.
-- =====================================================================

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT true;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name, column_default FROM information_schema.columns
--    WHERE table_name = 'users' AND column_name = 'onboarding_completed';
--   -> bir satir donmelidir (column_default = 'true').
--   SELECT count(*) FILTER (WHERE onboarding_completed = false) AS bekleyen
--    FROM users;
--   -> mevcut kullanicilarda 0 olmalidir.
