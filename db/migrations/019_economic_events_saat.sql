-- =====================================================================
-- 019 - economic_events: saat (event_time) kolonu
-- =====================================================================
--
-- NEDEN GEREKLI
--   Kullanici ekonomik takvimde saatlerin de gosterilmesini istedi.
--   Global (yfinance) taraf zaten gercek saat bilgisiyle geliyor
--   (backend/app/services/economic_calendar.py, Europe/Istanbul'a
--   cevriliyor); bu migration Turkiye'ye ozel (TCMB/TUIK) satirlara da
--   RESMI aciklama saatlerini ekliyor: TCMB PPK karari 14:00'te, TUIK
--   enflasyon (TUFE) verisi 10:00'da aciklanir (Turkiye saati, yerlesik/
--   uzun suredir degismeyen resmi uygulama).
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/019_economic_events_saat.sql
--
-- GUVENLIK
--   Idempotenttir: kolon zaten varsa `ADD COLUMN IF NOT EXISTS` hicbir
--   sey yapmaz. UPDATE'ler `source` alanina gore filtrelenir - sadece
--   018'de eklenen 7 TCMB/TUIK satirini gunceller, ileride baska
--   kaynaklardan eklenecek satirlara DOKUNMAZ.
-- =====================================================================

BEGIN;

ALTER TABLE economic_events ADD COLUMN IF NOT EXISTS event_time VARCHAR(5);

UPDATE economic_events SET event_time = '14:00' WHERE source = 'TCMB' AND event_time IS NULL;
UPDATE economic_events SET event_time = '10:00' WHERE source = 'TÜİK' AND event_time IS NULL;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT event_date, event_name, event_time, source FROM economic_events
--    ORDER BY event_date;
--   -> tum satirlarda event_time DOLU olmalidir (TCMB=14:00, TUIK=10:00).
