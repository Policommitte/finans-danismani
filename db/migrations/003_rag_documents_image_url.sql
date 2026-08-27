-- =====================================================================
-- 003 - rag.documents: haber gorseli icin image_url kolonu
-- =====================================================================
--
-- NEDEN GEREKLI
--   Bulten sayfasindaki her haber kartinin bir gorseli olmasi gerekiyor.
--   Ekibin ozel/one cikan bir haber icin gercek bir gorsel URL'si
--   girebilmesi icin bu kolon eklendi; coklugu bos kalacak ve backend
--   (app/services/news.py -> get_fallback_image) kategoriye/basliga gore
--   otomatik bir varsayilan atayacak.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/003_rag_documents_image_url.sql
--
-- GUVENLIK
--   Idempotenttir: kolon zaten varsa hicbir sey yapmaz, veri silmez,
--   mevcut degerleri EZMEZ. Iki kez calistirmak zararsizdir.
-- =====================================================================

BEGIN;

ALTER TABLE rag.documents ADD COLUMN IF NOT EXISTS image_url TEXT;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name FROM information_schema.columns
--    WHERE table_schema = 'rag' AND table_name = 'documents'
--      AND column_name = 'image_url';
--   -> bir satir donmelidir.
