-- 007_lead_role_filter.sql
-- v_lead_user_signals'a role='customer' filtresi ekler: danisman
-- hesaplari lead motorunun hicbir zaman taramadigi/skorlamadigi
-- garanti altina alinir (once yalnizca marketing_consent=false
-- vermeye guveniyorduk - kod seviyesinde bir garanti degildi).

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
       )) / 86400)::INT AS days_since_activity,
       u.likit_para
FROM users u
LEFT JOIN portfoy_degeri pd ON pd.user_id = u.id
LEFT JOIN son_islem      si ON si.user_id = u.id
LEFT JOIN son_sohbet     sc ON sc.user_id = u.id
WHERE u.role = 'customer';
