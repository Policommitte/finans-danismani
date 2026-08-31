-- Yeni stop-loss esiklerini varligin kendi para biriminde saklar.
--
-- Eski satirlarda bu kolon NULL kalir; backend bu satirlari geriye donuk
-- uyumluluk icin TRY esigi olarak yorumlamaya devam eder. Yeni satirlarda
-- USD/EUR/TRY gibi varligin `assets.currency` degeri yazilir.

BEGIN;

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS stop_loss_currency VARCHAR(10);

COMMENT ON COLUMN orders.stop_loss_currency IS
    'Stop-loss esiginin para birimi; NULL olan eski kayitlar TRY kabul edilir.';

COMMIT;
