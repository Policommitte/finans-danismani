-- Paper trading: sanal TRY hesabi, emirler, gerceklesmeler ve nakit defteri.

CREATE TABLE IF NOT EXISTS cash_accounts (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    currency VARCHAR(10) NOT NULL DEFAULT 'TRY',
    available_balance NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (available_balance >= 0),
    reserved_balance NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (reserved_balance >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (portfolio_id, currency)
);

CREATE TABLE IF NOT EXISTS paper_positions (
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    quantity NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    average_buy_price NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (average_buy_price >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (portfolio_id, asset_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY','SELL')),
    order_type VARCHAR(10) NOT NULL DEFAULT 'MARKET' CHECK (order_type IN ('MARKET')),
    quantity NUMERIC(20,6) NOT NULL CHECK (quantity > 0),
    quoted_price NUMERIC(20,6) NOT NULL CHECK (quoted_price > 0),
    status VARCHAR(12) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','FILLED','REJECTED','CANCELLED')),
    filled_quantity NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (filled_quantity >= 0),
    average_fill_price NUMERIC(20,6),
    commission NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (commission >= 0),
    reserved_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (reserved_amount >= 0),
    rejection_reason TEXT,
    idempotency_key VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    filled_at TIMESTAMPTZ,
    UNIQUE (user_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS order_fills (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    quantity NUMERIC(20,6) NOT NULL CHECK (quantity > 0),
    price NUMERIC(20,6) NOT NULL CHECK (price > 0),
    commission NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (commission >= 0),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cash_ledger (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES cash_accounts(id) ON DELETE CASCADE,
    order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL,
    entry_type VARCHAR(20) NOT NULL
        CHECK (entry_type IN ('DEPOSIT','BUY_FILL','SELL_PROCEEDS','ADJUSTMENT')),
    amount NUMERIC(18,2) NOT NULL,
    balance_after NUMERIC(18,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS orders_user_created_idx ON orders (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS orders_pending_asset_idx
    ON orders (asset_id, created_at) WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS order_fills_order_idx ON order_fills (order_id, executed_at);
CREATE INDEX IF NOT EXISTS cash_ledger_account_idx ON cash_ledger (account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS paper_positions_portfolio_idx ON paper_positions (portfolio_id);

INSERT INTO cash_accounts (portfolio_id, currency, available_balance)
SELECT p.id, 'TRY', CASE WHEN p.user_id = 1 THEN 100000.00 ELSE 75000.00 END
FROM portfolios p
ON CONFLICT (portfolio_id, currency) DO NOTHING;

INSERT INTO cash_ledger (account_id, entry_type, amount, balance_after)
SELECT ca.id, 'DEPOSIT', ca.available_balance, ca.available_balance
FROM cash_accounts ca
WHERE NOT EXISTS (
    SELECT 1 FROM cash_ledger cl WHERE cl.account_id = ca.id
);
