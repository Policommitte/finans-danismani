-- Gerceklesen alimlara bagli koruyucu stop-market emirlerini ekler.

BEGIN;

ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_order_type_check;
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_limit_price_check;
ALTER TABLE orders
    ALTER COLUMN order_type TYPE VARCHAR(12),
    ADD COLUMN IF NOT EXISTS stop_loss_price NUMERIC(20,6),
    ADD COLUMN IF NOT EXISTS parent_order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL;

ALTER TABLE orders
    ADD CONSTRAINT orders_order_type_check
        CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP_MARKET')),
    ADD CONSTRAINT orders_limit_price_check
        CHECK (
            (order_type IN ('MARKET', 'STOP_MARKET') AND limit_price IS NULL)
            OR (order_type = 'LIMIT' AND limit_price > 0)
        ),
    ADD CONSTRAINT orders_stop_loss_check
        CHECK (
            (order_type = 'STOP_MARKET' AND side = 'SELL' AND stop_loss_price > 0
             AND parent_order_id IS NOT NULL)
            OR order_type <> 'STOP_MARKET'
        );

CREATE INDEX IF NOT EXISTS orders_pending_stop_idx
    ON orders (asset_id, stop_loss_price)
    WHERE status = 'PENDING' AND order_type = 'STOP_MARKET';

COMMIT;
