-- Emir bildirimleri icin outbox tablosu.
--
-- NEDEN OUTBOX: bildirim kaydi, emrin gerceklestigi AYNI transaction icinde
-- yazilir. Boylece geri alinan bir gerceklesme icin bildirim uretilmez ve
-- gerceklesen bir emrin bildirimi -- uygulama o anda cokse bile -- kaybolmaz.
--
-- MAIL KANALI SU AN BAGLI DEGIL. Olaylar yine de yazilir; SMTP tanimlandiginda
-- KOD degil yalnizca AYAR degisir (bkz. app/notifications/deps.py).

CREATE TABLE IF NOT EXISTS notification_outbox (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL,
    event_type VARCHAR(24) NOT NULL
        CHECK (event_type IN ('ORDER_FILLED', 'ORDER_REJECTED', 'ORDER_EXPIRED')),
    channel VARCHAR(12) NOT NULL DEFAULT 'EMAIL' CHECK (channel IN ('EMAIL')),
    recipient VARCHAR(200) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- PENDING  : gonderilmeyi bekliyor
    -- SENT     : kanaldan basariyla cikti
    -- SKIPPED  : kanal kapali ya da olay cok eski (bilincli gonderilmedi)
    -- FAILED   : kanal acikti ama gonderim hata verdi
    status VARCHAR(10) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'SENT', 'SKIPPED', 'FAILED')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS notification_outbox_pending_idx
    ON notification_outbox (created_at)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS notification_outbox_user_idx
    ON notification_outbox (user_id, created_at DESC);
