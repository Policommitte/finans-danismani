-- BIST 100 benchmark asset used by the portfolio performance comparison.
-- Safe to run repeatedly; existing prices and history are preserved.

BEGIN;

INSERT INTO asset_categories (code, name)
VALUES ('INDEX', 'Piyasa Endeksi')
ON CONFLICT (code) DO NOTHING;

INSERT INTO assets (
    category_id,
    symbol,
    name,
    currency,
    current_price,
    prev_close,
    daily_change_pct,
    weekly_change_pct,
    yearly_change_pct,
    price_updated_at
)
SELECT
    ac.id,
    'BIST100',
    'BIST 100 Endeksi',
    'TRY',
    14337.0,
    14337.0,
    0,
    0,
    0,
    now()
FROM asset_categories ac
WHERE ac.code = 'INDEX'
ON CONFLICT (symbol) DO NOTHING;

COMMIT;
