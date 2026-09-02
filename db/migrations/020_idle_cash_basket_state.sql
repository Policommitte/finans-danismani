-- Kalici yatirim sepeti uyelikleri ve yeniden dengeleme durumu.
-- Fiyat/adet bilgisi burada tutulmaz; her API isteginde guncel fiyatla
-- yeniden hesaplanir. Yalnizca hangi varliklarin sepette kaldigi saklanir.

BEGIN;

CREATE TABLE IF NOT EXISTS idle_cash_basket_states (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal VARCHAR(24) NOT NULL CHECK (
        goal IN ('LONG_TERM', 'GROWTH', 'MOMENTUM', 'LOW_VOLATILITY')
    ),
    memberships JSONB NOT NULL DEFAULT '[]'::jsonb,
    breach_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    profile_signature VARCHAR(128) NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, goal)
);

CREATE INDEX IF NOT EXISTS idle_cash_basket_states_evaluated_idx
    ON idle_cash_basket_states (evaluated_at);

COMMIT;
