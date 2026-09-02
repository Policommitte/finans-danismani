-- Sepet uyeligini varlik bazinda izler ve ayni degisim sinyalinin
-- ard arda dogrulanmasini saglar. Eski satirlar uygulama tarafinda
-- changed_at degeriyle geriye uyumlu olarak doldurulur.

BEGIN;

ALTER TABLE idle_cash_basket_states
    ADD COLUMN IF NOT EXISTS membership_since JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS change_signals JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMIT;
