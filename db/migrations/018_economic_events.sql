-- =====================================================================
-- 018 - economic_events: Turkiye'ye ozel ekonomik takvim olaylari
-- =====================================================================
--
-- NEDEN GEREKLI
--   UC-09 (Ekonomik Takvim): global buyuk ekonomilerin olaylari (Fed, ECB
--   gibi) backend/app/services/economic_calendar.py -> yfinance'ten CANLI
--   cekiliyor, ama yfinance Turkiye'ye ozel resmi olaylari (TCMB PPK faiz
--   karari, TUIK enflasyon aciklamasi) icermiyor. Bu tablo o bosluk icin -
--   backend/app/api/routes/economic_calendar.py iki kaynagi birlestirip
--   GET /api/economic-calendar altinda tek liste olarak sunuyor.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/018_economic_events.sql
--
-- GUVENLIK
--   Idempotenttir: tablo zaten varsa dokunulmaz, INSERT'ler `ON CONFLICT DO
--   NOTHING` ile korunur (tekil kisit: ayni tarih+olay+ulke ikinci kez
--   eklenmez - asagidaki UNIQUE index). Tarihler kaynagindan (tcmb.gov.tr,
--   TUIK takvimi) elle girildi; TUFE tarihleri "ayin yaklasik 3. gunu"
--   notuna gore ayin 3'u secildi - resmi TUIK takvimi yayinlaninca
--   guncellenmeli.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS economic_events (
    id SERIAL PRIMARY KEY,
    event_date DATE NOT NULL,
    country VARCHAR(4) NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    importance VARCHAR(10) NOT NULL CHECK (importance IN ('low', 'medium', 'high')),
    source VARCHAR(100) NOT NULL,
    expected VARCHAR(50),
    actual VARCHAR(50),
    previous VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS economic_events_tarih_olay_uidx
    ON economic_events (event_date, country, event_name);

INSERT INTO economic_events (event_date, country, event_name, importance, source) VALUES
    ('2026-09-10', 'TR', 'TCMB PPK Faiz Kararı', 'high', 'TCMB'),
    ('2026-10-22', 'TR', 'TCMB PPK Faiz Kararı', 'high', 'TCMB'),
    ('2026-12-10', 'TR', 'TCMB PPK Faiz Kararı', 'high', 'TCMB'),
    ('2026-09-03', 'TR', 'TÜİK Enflasyon (TÜFE) Açıklaması', 'medium', 'TÜİK'),
    ('2026-10-03', 'TR', 'TÜİK Enflasyon (TÜFE) Açıklaması', 'medium', 'TÜİK'),
    ('2026-11-03', 'TR', 'TÜİK Enflasyon (TÜFE) Açıklaması', 'medium', 'TÜİK'),
    ('2026-12-03', 'TR', 'TÜİK Enflasyon (TÜFE) Açıklaması', 'medium', 'TÜİK')
ON CONFLICT DO NOTHING;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT event_date, event_name, importance, source FROM economic_events
--    ORDER BY event_date;
--   -> 7 satir donmelidir (3 TCMB + 4 TUIK).
