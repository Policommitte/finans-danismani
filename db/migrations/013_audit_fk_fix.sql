-- =====================================================================
-- 013 - recommendation_audit: yabanci anahtarlari kaldir
-- =====================================================================
--
-- SORUN
--   012'de `recommendation_id` ve `user_id` FK'leri ON DELETE SET NULL ile
--   tanimlanmisti. Ayni tabloda FR-AUT-032 icin bir DEGISTIRILEMEZLIK
--   trigger'i var (BEFORE UPDATE OR DELETE -> RAISE EXCEPTION).
--
--   Bu ikisi CAKISIYOR: bir oneri silinince PostgreSQL denetim satirinda
--   SET NULL yapmak icin UPDATE dener, trigger onu reddeder ve silme
--   basarisiz olur. Zincir yukari dogru isliyor:
--
--       users DELETE -> recommendations CASCADE -> audit SET NULL -> RED
--
--   Yani KULLANICI SILINEMIYORDU. KVKK/GDPR silme talebi karsilanamazdi.
--
-- COZUM
--   Denetim tablolarinin standart deseni: FK YOK. Denetim kaydi, anlattigi
--   kaydin OMRUNDEN UZUN yasar; silinen bir onerinin kaydi da durmalidir.
--   Kolonlar duz BIGINT/INTEGER olarak kalir, degerleri korunur.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/013_audit_fk_fix.sql
-- =====================================================================

BEGIN;

ALTER TABLE recommendation_audit
    DROP CONSTRAINT IF EXISTS recommendation_audit_recommendation_id_fkey,
    DROP CONSTRAINT IF EXISTS recommendation_audit_user_id_fkey;

COMMIT;

-- Dogrulama (elle):
--   SELECT conname FROM pg_constraint
--    WHERE conrelid = 'recommendation_audit'::regclass AND contype = 'f';
--   -> hicbir satir donmemelidir.
