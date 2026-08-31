-- =====================================================================
-- 003 - lead motoru: BSD kuyrugu / otonom davet
-- =====================================================================
--
-- NEDEN GEREKLI (EPIC 2)
--   Kayitli kullanicilari (users) tarayip uygunluk kurallarindan gecirir,
--   skorlar ve iki kuyruktan birine yazar: yuksek varlikli kullanicilar
--   BSD (insan danisman) kuyruguna, digerleri otonom mail kuyruguna.
--   Detay: db/v5_schema_and_data.sql "5B" bolumu.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/003_lead_engine.sql
--
-- GUVENLIK
--   Idempotenttir: hicbir satir SILMEZ, mevcut degerleri EZMEZ, iki kez
--   calistirmak zararsizdir.
-- =====================================================================

BEGIN;

-- 1) users.marketing_consent -----------------------------------------------
--    Iys yerine basitlestirilmis riza alani. DEFAULT TRUE: mevcut satirlar
--    otomatik "izinli" sayilir, elle guncelleme gerekmez.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN NOT NULL DEFAULT TRUE;

-- 2) lead_scans --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_scans (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    trigger VARCHAR(20) NOT NULL DEFAULT 'startup',
    scanned_count INTEGER NOT NULL DEFAULT 0,
    bsd_count INTEGER NOT NULL DEFAULT 0,
    autonomous_count INTEGER NOT NULL DEFAULT 0,
    excluded_count INTEGER NOT NULL DEFAULT 0,
    emailed_count INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'lead_scans_trigger_check'
    ) THEN
        ALTER TABLE lead_scans
            ADD CONSTRAINT lead_scans_trigger_check
            CHECK (trigger IN ('startup','manual','test'));
    END IF;
END
$$;

-- 3) lead_queue_entries -------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_queue_entries (
    id BIGSERIAL PRIMARY KEY,
    scan_id BIGINT NOT NULL REFERENCES lead_scans(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    decision VARCHAR(20) NOT NULL,
    exclusion_reason VARCHAR(40),
    score INTEGER NOT NULL DEFAULT 0,
    score_components JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_value_try NUMERIC NOT NULL DEFAULT 0,
    monthly_income NUMERIC NOT NULL DEFAULT 0,
    days_since_activity INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (scan_id, user_id)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'lead_queue_entries_decision_check'
    ) THEN
        ALTER TABLE lead_queue_entries
            ADD CONSTRAINT lead_queue_entries_decision_check
            CHECK (decision IN ('BSD','AUTONOMOUS','EXCLUDED'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'lead_queue_entries_reason_check'
    ) THEN
        ALTER TABLE lead_queue_entries
            ADD CONSTRAINT lead_queue_entries_reason_check
            CHECK ((decision = 'EXCLUDED') = (exclusion_reason IS NOT NULL));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'lead_queue_entries_score_check'
    ) THEN
        ALTER TABLE lead_queue_entries
            ADD CONSTRAINT lead_queue_entries_score_check
            CHECK (score BETWEEN 0 AND 100);
    END IF;
END
$$;

-- 4) lead_contacts -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_contacts (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scan_id BIGINT REFERENCES lead_scans(id) ON DELETE SET NULL,
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    to_email VARCHAR(150),
    subject VARCHAR(200),
    error TEXT,
    contact_day DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'lead_contacts_channel_check'
    ) THEN
        ALTER TABLE lead_contacts
            ADD CONSTRAINT lead_contacts_channel_check
            CHECK (channel IN ('EMAIL','BSD_QUEUE'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'lead_contacts_status_check'
    ) THEN
        ALTER TABLE lead_contacts
            ADD CONSTRAINT lead_contacts_status_check
            CHECK (status IN ('SENT','FAILED','SKIPPED'));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS lead_contacts_gunluk_uidx
    ON lead_contacts (user_id, channel, contact_day) WHERE status = 'SENT';

-- 5) Indeksler -------------------------------------------------------------
CREATE INDEX IF NOT EXISTS lead_scans_started_idx
    ON lead_scans (started_at DESC);
CREATE INDEX IF NOT EXISTS lead_queue_entries_scan_idx
    ON lead_queue_entries (scan_id);
CREATE INDEX IF NOT EXISTS lead_queue_entries_user_idx
    ON lead_queue_entries (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS lead_queue_entries_decision_idx
    ON lead_queue_entries (decision, created_at DESC);
CREATE INDEX IF NOT EXISTS lead_contacts_user_idx
    ON lead_contacts (user_id, created_at DESC);

-- 6) v_lead_user_signals view ------------------------------------------------
--    CREATE OR REPLACE zaten idempotent.
CREATE OR REPLACE VIEW v_lead_user_signals AS
WITH portfoy_degeri AS (
    SELECT user_id,
           SUM(total_value_try) AS total_value_try,
           SUM(holding_count)   AS holding_count
    FROM v_portfolio_summary
    GROUP BY user_id
), son_islem AS (
    SELECT p.user_id, MAX(t.transaction_date) AS last_transaction_at
    FROM transactions t
    JOIN portfolios p ON p.id = t.portfolio_id
    GROUP BY p.user_id
), son_sohbet AS (
    SELECT user_id, MAX(updated_at) AS last_chat_at
    FROM chat_sessions
    GROUP BY user_id
)
SELECT u.id AS user_id, u.first_name, u.last_name, u.email,
       u.monthly_income, u.marketing_consent, u.created_at AS registered_at,
       COALESCE(pd.total_value_try, 0) AS total_value_try,
       COALESCE(pd.holding_count, 0)   AS holding_count,
       si.last_transaction_at,
       sc.last_chat_at,
       GREATEST(si.last_transaction_at, sc.last_chat_at) AS last_activity_at,
       FLOOR(EXTRACT(EPOCH FROM (
           now() - GREATEST(si.last_transaction_at, sc.last_chat_at)
       )) / 86400)::INT AS days_since_activity
FROM users u
LEFT JOIN portfoy_degeri pd ON pd.user_id = u.id
LEFT JOIN son_islem      si ON si.user_id = u.id
LEFT JOIN son_sohbet     sc ON sc.user_id = u.id;

COMMIT;

-- Dogrulama (elle calistirin, bu betigin parcasi degildir):
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name = 'users' AND column_name = 'marketing_consent';
--
--   SELECT table_name FROM information_schema.tables
--    WHERE table_name IN ('lead_scans','lead_queue_entries','lead_contacts');
--
--   SELECT * FROM v_lead_user_signals ORDER BY total_value_try DESC;