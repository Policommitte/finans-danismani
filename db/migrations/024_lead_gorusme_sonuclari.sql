-- 024_lead_gorusme_sonuclari.sql
-- Danismanin telefon gorusmesinden sonra ELLE isaretledigi sonuc.
--
-- Neden AYRI tablo: `lead_queue_entries` ve `lead_contacts` tarama
-- motoruna aittir ve her taramada yeniden uretilir; danismanin girdigi
-- bilgi taramadan BAGIMSIZ olarak kalici olmali.
--
-- Ekleme-only: her gorusme bir satir, EN SON satir gecerli. Boylece
-- "iki kez ulasilamadi, ucuncude kabul etti" gecmisi durur ve kimin
-- isaretledigi bellidir.
--
-- ACIK: "sonucu temizle" - yanlis isaretlemeyi satir silmeden geri alir.
--
-- View'de `advisor_outcome` EN SONA eklenir: CREATE OR REPLACE VIEW
-- mevcut kolonlarin adini/sirasini degistiremez.

CREATE TABLE IF NOT EXISTS lead_call_outcomes (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    advisor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    outcome VARCHAR(20) NOT NULL
            CHECK (outcome IN ('KABUL','ISTEMIYOR','ULASILAMADI','ACIK')),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lead_call_outcomes_user_idx
    ON lead_call_outcomes (user_id, created_at DESC);

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
), son_gorusme AS (
    SELECT DISTINCT ON (user_id) user_id, outcome
    FROM lead_call_outcomes
    ORDER BY user_id, created_at DESC, id DESC
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
       )) / 86400)::INT AS days_since_activity,
       u.likit_para,
       sg.outcome AS advisor_outcome
FROM users u
LEFT JOIN portfoy_degeri pd ON pd.user_id = u.id
LEFT JOIN son_islem      si ON si.user_id = u.id
LEFT JOIN son_sohbet     sc ON sc.user_id = u.id
LEFT JOIN son_gorusme    sg ON sg.user_id = u.id
WHERE u.role = 'customer';