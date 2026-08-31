-- Saatlik mumlari iki yillik arsiv olarak sakla. 4 saatlik mumlar API
-- katmaninda bu 1h satirlarindan uretilir; ayri bir 4h kopyasi tutulmaz.

ALTER TABLE market_candles
    DROP CONSTRAINT IF EXISTS market_candles_interval_check;

ALTER TABLE market_candles
    ADD CONSTRAINT market_candles_interval_check
    CHECK (interval IN ('1m','5m','1h','1d'));
