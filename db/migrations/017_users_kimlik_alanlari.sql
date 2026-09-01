-- =====================================================================
-- 017 - users: kimlik alanlari (TCKN, dogum tarihi, telefon)
-- =====================================================================
--
-- NEDEN GEREKLI
--   Bu dort kolon CANLI Supabase'e elle eklenmisti; repoda hicbir
--   migration'da ve `db/v5_schema_and_data.sql` icinde YOKTU. Yani
--   sifirdan kurulan bir veritabaninda (CI dahil) hic olusmuyorlardi.
--   Bu dosya, calisan veritabani ile repoyu yeniden hizalar.
--
-- TCKN NEDEN TAM SAKLANMIYOR
--   TCKN dogrudan tutulmaz: `tckn_hash` (SHA-256, 64 karakter hex) ile
--   yalnizca dogrulama/tekillik yapilir, `tckn_last4` ise arayuzde
--   "•••• 1234" bicimindeki gosterim icindir. Boylece tam numara
--   veritabaninda hicbir yerde bulunmaz.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/017_users_kimlik_alanlari.sql
--
-- GUVENLIK
--   Idempotenttir: kolonlar/indeks zaten varsa hicbir sey yapmaz. Hepsi
--   NULL kabul eder, mevcut satirlar etkilenmez.
-- =====================================================================

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS tckn_hash    VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS tckn_last4   CHAR(4);
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date   DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);

-- Kismi unique: TCKN girilmis kullanicilar arasinda tekillik saglanir,
-- girilmemis (NULL) satirlar kisitlamaya takilmaz.
CREATE UNIQUE INDEX IF NOT EXISTS users_tckn_hash_uidx
    ON users (tckn_hash) WHERE tckn_hash IS NOT NULL;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name, data_type, character_maximum_length
--     FROM information_schema.columns
--    WHERE table_name = 'users'
--      AND column_name IN ('tckn_hash','tckn_last4','birth_date','phone_number');
--   -> dort satir donmelidir.
