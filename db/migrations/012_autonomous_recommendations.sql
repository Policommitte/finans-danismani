-- =====================================================================
-- 012 - Otonom oneri motoru (AUT modulu, D-02 + D-07)
-- =====================================================================
--
-- NUMARA NOTU: bu depoda 003 ve 004 numaralari IKISER kez kullanilmis
-- (003_bist100_benchmark + 003_rag_documents_image_url,
--  004_remove_simulated_market_data + 004_users_onboarding). Bu dosya
-- catisma olmasin diye 012'den devam eder; 011 bildirim outbox'idir.
--
-- CALISTIRMA
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/012_autonomous_recommendations.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Sinyal: ENSTRUMAN bazli, kullanicidan bagimsiz (FR-SIG-026).
-- Kisisellestirme bir sonraki katmanda, `recommendations` uretilirken yapilir.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('BUY', 'SELL')),
    -- 0..1 arasi. Esigin altinda kalan sinyal kullaniciya HIC ulasmaz;
    -- ic kayda alinir (D-02 "Sinyali ic kayda al" kutusu).
    confidence NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    rule_code VARCHAR(40) NOT NULL,
    -- Gerekce maddeleri ve sayisal kanit; oneri kartina birebir tasinir.
    rationale JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    reference_price NUMERIC(20,6) NOT NULL CHECK (reference_price > 0),
    -- BR-AUT-04: haber bazli 60 dk, tarama bazli seans sonu.
    expires_at TIMESTAMPTZ NOT NULL,
    engine_version VARCHAR(20) NOT NULL DEFAULT 'scan-v1',
    published BOOLEAN NOT NULL DEFAULT false,
    suppressed_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS signals_asset_created_idx ON signals (asset_id, created_at DESC);
CREATE INDEX IF NOT EXISTS signals_live_idx ON signals (expires_at) WHERE published;

-- ---------------------------------------------------------------------
-- Oneri: sinyalin BIR kullaniciya kisisellestirilmis hali.
-- Durum kumesi D-07 ile birebir.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recommendations (
    id BIGSERIAL PRIMARY KEY,
    signal_id BIGINT REFERENCES signals(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    -- FR-AUT-001: her oneri TEK enstruman ve TEK yon icerir.
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity NUMERIC(20,6) NOT NULL CHECK (quantity > 0),
    reference_price NUMERIC(20,6) NOT NULL CHECK (reference_price > 0),
    estimated_amount NUMERIC(18,2) NOT NULL CHECK (estimated_amount >= 0),
    confidence NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    -- FR-AUT-003 zorunlu alanlar: gerekce (en cok 5 madde), risk notu, kaynak.
    rationale JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_note TEXT NOT NULL,
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- FR-AUT-012 "neden bana geldi?"
    personalization JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(16) NOT NULL DEFAULT 'PUBLISHED' CHECK (status IN (
        'PUBLISHED',    -- Yayinlandi
        'VIEWED',       -- Goruntulendi
        'APPROVED',     -- Onaylandi
        'CONVERTED',    -- Emre donustu
        'REJECTED',     -- Reddedildi
        'EXPIRED',      -- Suresi doldu
        'HALTED'        -- Durduruldu (kill-switch)
    )),
    -- FR-AUT-023: ret gerekcesi sabit kume.
    rejection_reason VARCHAR(24) CHECK (rejection_reason IN (
        'NOT_INTERESTED', 'TOO_RISKY', 'NO_CASH', 'BAD_TIMING', 'NOT_UNDERSTOOD'
    )),
    -- BR-AUT-08: bir oneri EN FAZLA bir emir dogurur.
    order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    viewed_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ,
    CONSTRAINT recommendations_order_once UNIQUE (order_id)
);

CREATE INDEX IF NOT EXISTS recommendations_user_status_idx
    ON recommendations (user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS recommendations_open_expiry_idx
    ON recommendations (expires_at) WHERE status IN ('PUBLISHED', 'VIEWED');
-- BR-AUT-03 gunluk limit sayimi bu indeksi kullanir.
CREATE INDEX IF NOT EXISTS recommendations_user_created_idx
    ON recommendations (user_id, created_at DESC);

-- ---------------------------------------------------------------------
-- FR-PRF-014: kullanici otonom islem limitleri.
-- Satir yoksa VARSAYILAN uygulanir (bkz. services/recommendation.py).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_trading_limits (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    per_order_limit_try NUMERIC(18,2) NOT NULL DEFAULT 5000
        CHECK (per_order_limit_try > 0),
    daily_limit_try NUMERIC(18,2) NOT NULL DEFAULT 15000
        CHECK (daily_limit_try > 0),
    -- Bos dizi = TUM siniflara izinli. INDEX zaten islem disidir.
    allowed_asset_classes JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- FR-AUT-026: kullanici otonom akisi tamamen kapatabilir.
    autonomous_enabled BOOLEAN NOT NULL DEFAULT true,
    max_daily_recommendations INTEGER NOT NULL DEFAULT 3
        CHECK (max_daily_recommendations >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- FR-AUT-032: onay, ret, duzenleme ve emir olaylarinin tamami
-- DEGISTIRILEMEZ denetim kaydi olarak saklanir.
--
-- Degistirilemezlik uygulama katmaninda degil, TRIGGER ile zorlanir:
-- kod hatasi ya da elle mudahale kaydi degistiremesin.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recommendation_audit (
    id BIGSERIAL PRIMARY KEY,
    -- YABANCI ANAHTAR YOK - bilincli. Asagidaki degistirilemezlik trigger'i
    -- ON DELETE SET NULL'un yapacagi UPDATE'i de reddeder; FK konsaydi bir
    -- oneri (ve zincirleme, bir KULLANICI) hic silinemezdi. Denetim kaydi
    -- zaten anlattigi kaydin omrunden uzun yasamalidir.
    recommendation_id BIGINT,
    user_id INTEGER,
    event_type VARCHAR(32) NOT NULL,
    actor VARCHAR(24) NOT NULL DEFAULT 'SYSTEM',
    old_status VARCHAR(16),
    new_status VARCHAR(16),
    reason TEXT,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS recommendation_audit_rec_idx
    ON recommendation_audit (recommendation_id, created_at);
CREATE INDEX IF NOT EXISTS recommendation_audit_user_idx
    ON recommendation_audit (user_id, created_at DESC);

CREATE OR REPLACE FUNCTION recommendation_audit_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'recommendation_audit degistirilemez (FR-AUT-032)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS recommendation_audit_no_update ON recommendation_audit;
CREATE TRIGGER recommendation_audit_no_update
    BEFORE UPDATE OR DELETE ON recommendation_audit
    FOR EACH ROW EXECUTE FUNCTION recommendation_audit_immutable();

-- ---------------------------------------------------------------------
-- FR-AUT-034 / UC-18: kill-switch. Tek satirli ayar tablosu.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS autonomous_kill_switch (
    id BOOLEAN PRIMARY KEY DEFAULT true CHECK (id),
    active BOOLEAN NOT NULL DEFAULT false,
    reason TEXT,
    activated_by VARCHAR(100),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO autonomous_kill_switch (id, active) VALUES (true, false)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------
-- FR-AUT-006: oneri bildirimleri mevcut outbox'tan gider (011).
-- Olay tipi kumesi genisletilir.
-- ---------------------------------------------------------------------
ALTER TABLE notification_outbox DROP CONSTRAINT IF EXISTS notification_outbox_event_type_check;
ALTER TABLE notification_outbox ADD CONSTRAINT notification_outbox_event_type_check
    CHECK (event_type IN (
        'ORDER_FILLED', 'ORDER_REJECTED', 'ORDER_EXPIRED', 'RECOMMENDATION_CREATED'
    ));

COMMIT;
