-- Runtime market simulation was removed. Keep only verified API prices and
-- remove the simulator-only volatility column.

BEGIN;

DELETE FROM live_prices WHERE source <> 'api';
DELETE FROM price_history WHERE source <> 'api';

ALTER TABLE live_prices ALTER COLUMN source SET DEFAULT 'api';
ALTER TABLE price_history ALTER COLUMN source SET DEFAULT 'api';

ALTER TABLE live_prices DROP CONSTRAINT IF EXISTS live_prices_source_check;
ALTER TABLE live_prices
    ADD CONSTRAINT live_prices_source_check CHECK (source = 'api');

ALTER TABLE price_history DROP CONSTRAINT IF EXISTS price_history_source_check;
ALTER TABLE price_history
    ADD CONSTRAINT price_history_source_check CHECK (source = 'api');

ALTER TABLE assets DROP COLUMN IF EXISTS sim_volatility;

COMMIT;
