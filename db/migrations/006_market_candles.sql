-- Yahoo'dan gelen gercek OHLCV mumlari. Mevcut fiyat isteginin ayni
-- cevabindan uretilir; ek API cagrisi gerektirmez.

CREATE TABLE IF NOT EXISTS market_candles (
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    interval VARCHAR(8) NOT NULL CHECK (interval IN ('5m','1d')),
    ts TIMESTAMPTZ NOT NULL,
    open NUMERIC NOT NULL CHECK (open > 0),
    high NUMERIC NOT NULL CHECK (high > 0),
    low NUMERIC NOT NULL CHECK (low > 0),
    close NUMERIC NOT NULL CHECK (close > 0),
    volume NUMERIC,
    source VARCHAR(20) NOT NULL DEFAULT 'yahoo',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, interval, ts),
    CHECK (high >= GREATEST(open, close, low)),
    CHECK (low <= LEAST(open, close, high))
);

CREATE INDEX IF NOT EXISTS market_candles_asset_interval_ts_idx
    ON market_candles (asset_id, interval, ts DESC);
