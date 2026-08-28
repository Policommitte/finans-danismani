-- 014 - gunluk oneri adedi varsayilani 3 -> 4 (urun karari).
-- Mevcut satirlarin acikca ayarlanmis degerlerine DOKUNULMAZ; yalnizca
-- varsayilan degisir ve hic ayar yapmamis kullanicilar 4 oneri alir.

BEGIN;

ALTER TABLE user_trading_limits
    ALTER COLUMN max_daily_recommendations SET DEFAULT 4;

UPDATE user_trading_limits
SET max_daily_recommendations = 4, updated_at = now()
WHERE max_daily_recommendations = 3;

COMMIT;
