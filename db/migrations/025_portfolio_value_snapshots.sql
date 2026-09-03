-- =====================================================================
-- 025 - Basarili fiyat turlarindaki portfoy degeri snapshot'lari
-- =====================================================================
-- Grafik, farkli varliklarin seyrek fiyat gecmisini sonradan birlestirmek
-- yerine scheduler aninda hesaplanan varlik + nakit toplamlarini okur.
-- Idempotenttir; mevcut portfoy, emir veya fiyat satirlarini degistirmez.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS portfolio_value_snapshots (
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    ts TIMESTAMPTZ NOT NULL,
    holdings_value_try NUMERIC(20,2) NOT NULL CHECK (holdings_value_try >= 0),
    cash_value_try NUMERIC(20,2) NOT NULL CHECK (cash_value_try >= 0),
    total_value_try NUMERIC(20,2) NOT NULL CHECK (total_value_try >= 0),
    source VARCHAR(20) NOT NULL DEFAULT 'scheduler',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (portfolio_id, ts)
);

CREATE INDEX IF NOT EXISTS portfolio_value_snapshots_portfolio_ts_idx
    ON portfolio_value_snapshots (portfolio_id, ts DESC);

COMMIT;
