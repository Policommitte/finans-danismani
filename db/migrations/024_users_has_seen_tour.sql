-- =====================================================================
-- 024 - users: has_seen_tour kolonu
-- =====================================================================
--
-- NEDEN GEREKLI
--   Urun turu (ProductTour.tsx) artik footer'daki manuel "Yardim" butonuyla
--   DEGIL, kullanicinin ilk kez kayit olup onboarding'i (anket -> sepet)
--   tamamladiktan hemen sonra OTOMATIK acilir (backend/app/api/routes/
--   auth.py -> /me, /tour-seen). Bu akisin kullaniciya SADECE BIR KEZ
--   gosterilmesi icin kalici bir bayrak gerekiyor - onboarding_completed
--   (004_users_onboarding.sql) ile AYNI desen, farkli anlam.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/024_users_has_seen_tour.sql
--
-- GUVENLIK
--   Idempotenttir: kolon zaten varsa hicbir sey yapmaz. DEFAULT true secildi
--   (backfill UPDATE'e gerek yok, tek deyim, MEVCUT KULLANICILAR tura
--   zorlanmaz - sadece bundan sonra kayit olacak yeni kullanicilar gorur).
--   Yeni kayitlar backend'in `create()` metodunda acikca false ile eklenir -
--   bu dosya sadece semayi hazirlar, hicbir satiri false yapmaz.
-- =====================================================================

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS has_seen_tour BOOLEAN NOT NULL DEFAULT true;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name, column_default FROM information_schema.columns
--    WHERE table_name = 'users' AND column_name = 'has_seen_tour';
--   -> bir satir donmelidir (column_default = 'true').
--   SELECT count(*) FILTER (WHERE has_seen_tour = false) AS bekleyen
--    FROM users;
--   -> mevcut kullanicilarda 0 olmalidir.
