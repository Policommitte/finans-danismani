-- Limit emir, gecerlilik ve kullanici iptali icin emir semasini genisletir.

BEGIN;

ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_order_type_check;
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_validity_check;
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_limit_price_check;
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS limit_price NUMERIC(20,6),
    ADD COLUMN IF NOT EXISTS validity VARCHAR(4) NOT NULL DEFAULT 'GTC',
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

ALTER TABLE orders
    ADD CONSTRAINT orders_order_type_check
        CHECK (order_type IN ('MARKET', 'LIMIT')),
    ADD CONSTRAINT orders_validity_check
        CHECK (validity IN ('DAY', 'GTC')),
    ADD CONSTRAINT orders_limit_price_check
        CHECK (
            (order_type = 'MARKET' AND limit_price IS NULL)
            OR (order_type = 'LIMIT' AND limit_price > 0)
        );

CREATE INDEX IF NOT EXISTS orders_pending_expiry_idx
    ON orders (expires_at)
    WHERE status = 'PENDING' AND expires_at IS NOT NULL;

COMMIT;
