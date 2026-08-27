-- 1 dakikalik gercek Yahoo mumlarini sakla. 1m satirlari uygulama tarafinda
-- 30 gunluk kayan pencereyle temizlenir; 5m ve 1d arsivi kalicidir.

ALTER TABLE market_candles
    DROP CONSTRAINT IF EXISTS market_candles_interval_check;

ALTER TABLE market_candles
    ADD CONSTRAINT market_candles_interval_check
    CHECK (interval IN ('1m','5m','1d'));
