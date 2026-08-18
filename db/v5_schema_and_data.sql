-- =====================================================================
-- Akıllı Kişisel Finans Danışmanı — v5 Şema + Dummy Data
-- PostgreSQL 16+ · pgvector 0.7+
-- Eşlik ettiği doküman: SYSTEM_ARCHITECTURE_v3.md
--
-- ⚠️ vector(1024) İKİ yerde geçer — embedding kararıyla ikisi de değişir.
-- =====================================================================

DROP SCHEMA IF EXISTS rag CASCADE;
DROP VIEW  IF EXISTS v_portfolio_summary CASCADE;
DROP VIEW  IF EXISTS v_portfolio_allocation CASCADE;
DROP VIEW  IF EXISTS v_holdings_valued CASCADE;
DROP VIEW  IF EXISTS v_fx_rates CASCADE;
DROP TABLE IF EXISTS security_events CASCADE;
DROP TABLE IF EXISTS tool_calls CASCADE;
DROP TABLE IF EXISTS market_api_usage CASCADE;
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;
DROP TABLE IF EXISTS user_alerts CASCADE;
DROP TABLE IF EXISTS watchlists CASCADE;
DROP TABLE IF EXISTS price_history CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS portfolio_assets CASCADE;
DROP TABLE IF EXISTS portfolios CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
DROP TABLE IF EXISTS asset_categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA rag;


-- =====================================================================
-- 1 · KİMLİK
-- =====================================================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    risk_tolerance VARCHAR(20) DEFAULT 'MEDIUM',   -- LOW · MEDIUM · HIGH
    monthly_income NUMERIC DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT now()
);


-- =====================================================================
-- 2 · VARLIK & PİYASA
-- =====================================================================

CREATE TABLE asset_categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES asset_categories(id),
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    currency VARCHAR(10) DEFAULT 'TRY',
    current_price NUMERIC NOT NULL,
    prev_close NUMERIC,
    daily_change_pct NUMERIC DEFAULT 0.0,
    weekly_change_pct NUMERIC DEFAULT 0.0,
    yearly_change_pct NUMERIC DEFAULT 0.0,
    sim_volatility NUMERIC NOT NULL DEFAULT 0.0150,
    price_updated_at TIMESTAMPTZ
);

CREATE TABLE price_history (
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    ts TIMESTAMPTZ NOT NULL,
    price NUMERIC NOT NULL CHECK (price > 0),
    source VARCHAR(20) NOT NULL DEFAULT 'simulated'
           CHECK (source IN ('simulated','api','backfill')),
    PRIMARY KEY (asset_id, ts)
);

CREATE TABLE market_api_usage (
    usage_date DATE PRIMARY KEY,
    call_count INTEGER NOT NULL DEFAULT 0,
    last_call_at TIMESTAMPTZ
);


-- =====================================================================
-- 3 · PORTFÖY
-- =====================================================================

CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,     -- "aktif portföy"
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX portfolios_one_default_uidx
    ON portfolios (user_id) WHERE is_default;

CREATE TABLE portfolio_assets (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    quantity NUMERIC NOT NULL DEFAULT 0.0,
    average_buy_price NUMERIC NOT NULL DEFAULT 0.0,
    UNIQUE (portfolio_id, asset_id)
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    transaction_type VARCHAR(10) NOT NULL,          -- BUY · SELL
    quantity NUMERIC NOT NULL,
    unit_price NUMERIC NOT NULL,
    transaction_date TIMESTAMPTZ DEFAULT now()
);


-- =====================================================================
-- 4 · SOHBET       AgentState.thread_id == chat_sessions.id
-- =====================================================================

CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(100) DEFAULT 'Yeni Sohbet',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender_role VARCHAR(20) NOT NULL,               -- user · assistant
    message_content TEXT NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,        -- sources · agent_errors · intent
    request_id UUID,
    created_at TIMESTAMPTZ DEFAULT now()
);


-- =====================================================================
-- 5 · DENETİM & GÜVENLİK
-- =====================================================================

CREATE TABLE tool_calls (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL,
    session_id INTEGER,
    user_id INTEGER,
    agent_name VARCHAR(50) NOT NULL,
    tool_name VARCHAR(50) NOT NULL,
    args JSONB NOT NULL DEFAULT '{}'::jsonb,        -- PII maskelenmiş
    success BOOLEAN NOT NULL,
    latency_ms NUMERIC,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE security_events (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL,
    user_id INTEGER,
    phase VARCHAR(10) NOT NULL CHECK (phase IN ('input','output')),
    flags TEXT[] NOT NULL DEFAULT '{}',
    risk_score NUMERIC,                             -- NULL = LLM'e gidilmedi
    action VARCHAR(10) NOT NULL CHECK (action IN ('allow','flag','block')),
    excerpt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =====================================================================
-- 6 · KAPSAM DIŞI (tablolar dursun, özellik yazılmasın)
-- =====================================================================

CREATE TABLE user_alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    target_price NUMERIC NOT NULL,
    condition VARCHAR(20) NOT NULL,                 -- ABOVE · BELOW
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE watchlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    added_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, asset_id)
);


-- =====================================================================
-- 7 · RAG      embedding varlığa değil, CHUNK'a aittir
-- =====================================================================

CREATE TABLE rag.documents (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(100) UNIQUE,                -- Source.doc_id
    baslik TEXT NOT NULL,
    sirket VARCHAR(100),
    asset_id INTEGER REFERENCES assets(id),
    tarih DATE,
    tip VARCHAR(30) CHECK (tip IN ('haber','bilanco','analist_raporu','duyuru')),
    kaynak_url TEXT,
    raw_text TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rag.chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES rag.documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),                         -- ⚠️ EMBEDDING_DIM 1/2
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('turkish', content)) STORED,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE rag.ingestion_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    embedding_model VARCHAR(100) NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'running'
);


-- =====================================================================
-- 8 · INDEXLER
-- =====================================================================

CREATE UNIQUE INDEX users_email_lower_uidx ON users (lower(email));
CREATE INDEX assets_name_trgm_idx      ON assets USING gin (name gin_trgm_ops);
CREATE INDEX price_history_asset_ts_idx ON price_history (asset_id, ts DESC);
CREATE INDEX portfolios_user_idx       ON portfolios (user_id);
CREATE INDEX portfolio_assets_pf_idx   ON portfolio_assets (portfolio_id);
CREATE INDEX transactions_pf_date_idx  ON transactions (portfolio_id, transaction_date DESC);
CREATE INDEX chat_sessions_user_idx    ON chat_sessions (user_id, updated_at DESC);
CREATE INDEX chat_messages_session_idx ON chat_messages (session_id, created_at);
CREATE INDEX tool_calls_request_idx    ON tool_calls (request_id);
CREATE INDEX security_events_block_idx ON security_events (created_at DESC) WHERE action <> 'allow';
CREATE INDEX documents_asset_idx       ON rag.documents (asset_id);
CREATE INDEX chunks_tsv_idx            ON rag.chunks USING gin (content_tsv);
CREATE INDEX chunks_hnsw_idx           ON rag.chunks USING hnsw (embedding vector_cosine_ops);


-- =====================================================================
-- 9 · VIEW'LAR — hesabın TEK kaynağı
--     Ajan da dashboard da buradan okur.
-- =====================================================================

CREATE VIEW v_fx_rates AS
SELECT 'TRY'::VARCHAR AS currency, 1.0::NUMERIC AS try_rate
UNION ALL SELECT 'USD', current_price FROM assets WHERE symbol = 'USD/TRY'
UNION ALL SELECT 'EUR', current_price FROM assets WHERE symbol = 'EUR/TRY';

CREATE VIEW v_holdings_valued AS
SELECT p.user_id, pa.portfolio_id, p.is_default,
       a.id AS asset_id, a.symbol, a.name AS asset_name,
       ac.code AS asset_class, a.currency,
       pa.quantity, pa.average_buy_price,
       a.current_price, a.daily_change_pct,
       pa.quantity * a.current_price * fx.try_rate                          AS market_value_try,
       pa.quantity * pa.average_buy_price * fx.try_rate                     AS cost_basis_try,
       pa.quantity * (a.current_price - pa.average_buy_price) * fx.try_rate AS pnl_try,
       CASE WHEN pa.average_buy_price > 0
            THEN (a.current_price - pa.average_buy_price) / pa.average_buy_price * 100
       END AS pnl_pct
FROM portfolio_assets pa
JOIN portfolios       p  ON p.id  = pa.portfolio_id
JOIN assets           a  ON a.id  = pa.asset_id
JOIN asset_categories ac ON ac.id = a.category_id
JOIN v_fx_rates       fx ON fx.currency = a.currency;

CREATE VIEW v_portfolio_allocation AS
SELECT user_id, portfolio_id, asset_class,
       SUM(market_value_try) AS class_value,
       ROUND(100 * SUM(market_value_try)
             / NULLIF(SUM(SUM(market_value_try)) OVER (PARTITION BY portfolio_id), 0), 2)
           AS class_pct
FROM v_holdings_valued
GROUP BY user_id, portfolio_id, asset_class;

CREATE VIEW v_portfolio_summary AS
SELECT user_id, portfolio_id,
       COUNT(*)              AS holding_count,
       SUM(market_value_try) AS total_value_try,
       SUM(cost_basis_try)   AS total_cost_try,
       SUM(pnl_try)          AS total_pnl_try,
       CASE WHEN SUM(cost_basis_try) > 0
            THEN SUM(pnl_try) / SUM(cost_basis_try) * 100 END AS total_pnl_pct
FROM v_holdings_valued
GROUP BY user_id, portfolio_id;


-- =====================================================================
-- 10 · HİBRİT ARAMA — rag_search tool'unun tek sorgusu
--      Dense (anlamsal) + BM25 (tam eşleşme) → RRF
-- =====================================================================

CREATE OR REPLACE FUNCTION rag.hybrid_search(
    p_query     TEXT,
    p_embedding vector(1024),                       -- ⚠️ EMBEDDING_DIM 2/2
    p_top_k     INT DEFAULT 5,
    p_asset_id  INT DEFAULT NULL,
    p_k_rrf     INT DEFAULT 60
)
RETURNS TABLE (chunk_id INT, document_id INT, content TEXT,
               baslik TEXT, sirket VARCHAR, tarih DATE, tip VARCHAR,
               score DOUBLE PRECISION)
LANGUAGE sql STABLE AS $$
-- plainto_tsquery terimleri AND'ler: dogal dildeki bir soruda tum kelimelerin
-- ayni chunk'ta gecmesi neredeyse imkansiz oldugu icin BM25 ayagi sessizce bos
-- doner ve arama saf vektor aramasina duserdi. Bu yuzden OR'a cevriliyor.
-- NULLIF: sorgu yalnizca stopword iceriyorsa tsquery bos kalir, eslesme aranmaz.
WITH q AS (
    SELECT NULLIF(replace(plainto_tsquery('turkish', p_query)::TEXT,
                          ' & ', ' | '), '')::tsquery AS tsq
),
filtered AS (
    SELECT c.id, c.content, c.embedding, c.content_tsv, c.document_id
    FROM rag.chunks c JOIN rag.documents d ON d.id = c.document_id
    WHERE p_asset_id IS NULL OR d.asset_id = p_asset_id
),
dense AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> p_embedding) rnk
    FROM filtered WHERE embedding IS NOT NULL
    ORDER BY embedding <=> p_embedding LIMIT p_top_k * 4
),
lexical AS (
    SELECT f.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(f.content_tsv, q.tsq) DESC) rnk
    FROM filtered f CROSS JOIN q
    WHERE f.content_tsv @@ q.tsq
    LIMIT p_top_k * 4
),
fused AS (
    SELECT COALESCE(d.id, l.id) id,
           COALESCE(1.0/(p_k_rrf+d.rnk),0) + COALESCE(1.0/(p_k_rrf+l.rnk),0) rrf
    FROM dense d FULL OUTER JOIN lexical l ON l.id = d.id
)
SELECT c.id, c.document_id, c.content, doc.baslik, doc.sirket, doc.tarih, doc.tip, f.rrf
FROM fused f
JOIN rag.chunks c      ON c.id  = f.id
JOIN rag.documents doc ON doc.id = c.document_id
ORDER BY f.rrf DESC LIMIT p_top_k;
$$;
-- score = RRF skorudur, kosinüs benzerliği DEĞİL.


-- =====================================================================
-- 11 · DUMMY DATA
-- =====================================================================

INSERT INTO asset_categories (code, name) VALUES
('STOCK','BIST Hisse Senedi'), ('GOLD','Altın & Gümüş'), ('FOREX','Döviz (Fiat)'),
('BOND','Tahvil & Bono'), ('CRYPTO','Kripto Varlıklar'),
('USA_STOCK','USA Hisse'), ('EU_STOCK','Avrupa Hisse');

INSERT INTO assets (category_id, symbol, name, currency, current_price,
                    daily_change_pct, weekly_change_pct, yearly_change_pct, sim_volatility) VALUES
(1,'THYAO','Türk Hava Yolları','TRY',315.50,1.2,4.5,65.2,0.0200),
(1,'GARAN','Garanti BBVA','TRY',125.40,-0.5,2.1,45.8,0.0200),
(1,'TCELL','Turkcell','TRY',95.80,2.1,8.4,55.3,0.0200),
(1,'SASA','Sasa Polyester','TRY',45.20,-1.8,-5.2,-15.4,0.0250),
(1,'ASELS','Aselsan','TRY',62.10,0.4,1.2,85.0,0.0200),
(1,'EREGL','Erdemir','TRY',55.00,3.2,6.7,12.5,0.0200),
(2,'GRAM_ALTIN','Gram Altın','TRY',2550.00,0.8,3.5,82.4,0.0080),
(2,'GUMUS','Gram Gümüş','TRY',31.50,-0.2,1.1,42.6,0.0120),
(3,'USD/TRY','Amerikan Doları','TRY',33.55,0.1,0.8,25.4,0.0050),
(3,'EUR/TRY','Euro','TRY',36.80,0.3,1.2,28.7,0.0050),
(4,'TR10Y','Türkiye 10 Yıllık Tahvil','TRY',100.00,0.0,0.0,15.5,0.0020),
(5,'BTC','Bitcoin','USD',65400.00,4.5,-2.3,125.6,0.0400),
(5,'ETH','Ethereum','USD',3450.00,2.1,-1.5,85.2,0.0450),
(5,'SOL','Solana','USD',145.20,-5.4,12.4,340.5,0.0550),
(6,'AAPL','Apple Inc.','USD',215.30,1.1,3.2,22.4,0.0150),
(6,'TSLA','Tesla Inc.','USD',245.80,-2.3,-8.5,5.6,0.0300),
(6,'NVDA','Nvidia','USD',130.50,5.6,18.2,215.8,0.0280);

UPDATE assets SET prev_close = ROUND(current_price / (1 + daily_change_pct/100.0), 4),
                  price_updated_at = now();

-- Şifre hepsinde: demo1234
INSERT INTO users (first_name, last_name, email, password_hash, risk_tolerance, monthly_income) VALUES
('Mehmet','Yılmaz','mehmet@example.com','$2b$10$IR711tECQxZE.JMPUjgWs.y9LzkCYTDDqbejiRAB7YkEYAvSdDIXW','HIGH',150000.0),
('Ayşe','Kaya','ayse@example.com','$2b$10$Yb8T7yJiAWQQD71v45o/EOpGCQVCWj9sAbJmjl5R6HKa39lyKW36S','LOW',75000.0),
('Can','Öztürk','can@example.com','$2b$10$tFWB6HyIOE91rFskCogI1.n8WmSV4zqdJ/Y2rbOzAIOZwcutolnZq','HIGH',45000.0),
('Zeynep','Demir','zeynep@example.com','$2b$10$bYkcSp99rikfo9Xqc0vWjO03J832PUdeC4orqCO.AJTIY1yJmnC4e','MEDIUM',95000.0),
('Ahmet','Şahin','ahmet@example.com','$2b$10$OStPyyZDG6togEcTURO7NOPmNQoyjtzcx.LUaArmpU9LHX0ICXHre','LOW',40000.0),
('Elif','Çelik','elif@example.com','$2b$10$U92TKkQv7nXd39NVPKYXFOVT0BEM9ltkUNaYGExj5SSuj77m2Nyou','HIGH',250000.0),
('Burak','Tekin','burak@example.com','$2b$10$5NrnZAcGw5PZ7xSl8upei.87KMfLCacEPhUwj.DoFNizbMhbkQ9.K','MEDIUM',60000.0),
('Selin','Aydın','selin@example.com','$2b$10$5cTFiUiaaDlCeL9vT3/1cuK5Wu/gqhOnRLDJTEeiYLNgrAmtrT3Je','MEDIUM',85000.0),
('Kemal','Yıldız','kemal@example.com','$2b$10$tSimnfkYhkhV/dSs/t4gteqrGgWs6ut9DuCet2nihoL3w0khrswOu','LOW',30000.0),
('Büşra','Koç','busra@example.com','$2b$10$.35my8JfMBBHGpo/AbH/0Ogb1FbMPHXuRnB8P5fuCKojKK2014GvW','HIGH',120000.0);

INSERT INTO portfolios (user_id, name, is_default) VALUES
(1, 'Agresif BIST & Kripto',      TRUE),
(2, 'Güvenli Liman (Emeklilik)',  TRUE),
(3, 'Kripto Sepetim',             TRUE),
(4, 'Uzun Vade Değer Yatırımı',   TRUE),
(6, 'Global Teknoloji Fonu',      TRUE),
(6, 'Yüksek Riskli Altcoinler',   FALSE),
(10,'Temettü Portföyü',           TRUE);       -- kasıtlı BOŞ: edge case

INSERT INTO transactions (portfolio_id, asset_id, transaction_type, quantity, unit_price, transaction_date) VALUES
(1, 1,'BUY',1000,  290.00, now() - INTERVAL '75 days'),
(1, 4,'BUY',5000,   52.00, now() - INTERVAL '60 days'),
(1,12,'BUY', 0.5,60000.00, now() - INTERVAL '40 days'),
(2, 7,'BUY', 200, 2300.00, now() - INTERVAL '80 days'),
(2, 9,'BUY',5000,   31.50, now() - INTERVAL '70 days'),
(3,13,'BUY',   5, 4000.00, now() - INTERVAL '55 days'),
(3,14,'BUY', 100,   85.00, now() - INTERVAL '50 days'),
(4, 2,'BUY',2000,   95.00, now() - INTERVAL '85 days'),
(4, 6,'BUY',1500,   42.00, now() - INTERVAL '65 days'),
(4,15,'BUY',  50,  180.00, now() - INTERVAL '45 days'),
(5,17,'BUY', 500,   90.00, now() - INTERVAL '70 days'),
(6,14,'BUY',2000,  120.00, now() - INTERVAL '30 days');

INSERT INTO portfolio_assets (portfolio_id, asset_id, quantity, average_buy_price) VALUES
(1, 1,1000,  290.00), (1, 4,5000,   52.00), (1,12, 0.5,60000.00),
(2, 7, 200, 2300.00), (2, 9,5000,   31.50),
(3,13,   5, 4000.00), (3,14, 100,   85.00),
(4, 2,2000,   95.00), (4, 6,1500,   42.00), (4,15,  50,  180.00),
(5,17, 500,   90.00),
(6,14,2000,  120.00);

INSERT INTO user_alerts (user_id, asset_id, target_price, condition) VALUES
(1,4,60.00,'ABOVE'), (1,12,70000.00,'ABOVE'), (2,7,2400.00,'BELOW'),
(3,13,3000.00,'BELOW'), (6,17,150.00,'ABOVE');

INSERT INTO watchlists (user_id, asset_id) VALUES (1,16), (3,12), (4,7), (10,6);

INSERT INTO chat_sessions (user_id, title) VALUES
(1,'SASA Zararı ve Kripto Fırsatları'),
(3,'Altcoin Sepeti Yorumu');

INSERT INTO chat_messages (session_id, sender_role, message_content) VALUES
(1,'user','SASA maliyetim 52 TL, şu an 45 TL. Zarardayım. Ne yapmalıyım?'),
(1,'assistant','Mehmet Bey, portföyünüzdeki SASA pozisyonu yaklaşık %13 ekside. Agresif risk profilinize uygun olarak piyasa dönüşünü bekleyebilir veya BTC pozisyonunuzdan elde ettiğiniz kârla maliyet düşürmeyi değerlendirebilirsiniz. Bu bir yatırım tavsiyesi değildir.'),
(2,'user','Ethereum maliyetim çok yüksek kaldı (4000$). Solana ise kârda. Nasıl dengeleyebilirim?'),
(2,'assistant','Can Bey, Solana pozisyonunuzdaki kârı realize edip bir kısmını Ethereum tarafına kaydırmak, yüksek risk profiliniz için değerlendirilebilecek bir yeniden dengeleme yaklaşımıdır. Bu bir yatırım tavsiyesi değildir.');


-- =====================================================================
-- 12 · FİYAT GEÇMİŞİ BACKFILL — 90 gün · 4 saat çözünürlük (~9.200 satır)
--      Bu olmadan grafikler boş, risk ajanı volatilite hesaplayamaz.
-- =====================================================================

INSERT INTO price_history (asset_id, ts, price, source)
SELECT a.id, g.ts,
       GREATEST(
           -- ::NUMERIC sart: SIN()/RANDOM() ifadeyi double precision yapar ve
           -- round(double precision, integer) PostgreSQL'de tanimli degildir.
           ROUND((a.current_price * (
               (1 - (a.yearly_change_pct/100.0) * (d.days_ago/365.0))
               + a.sim_volatility * 2.5 * SIN(d.days_ago/6.0)
               + a.sim_volatility * (RANDOM()-0.5) * 2
           ))::NUMERIC, 4),
           a.current_price * 0.05)
       , 'backfill'
FROM assets a
CROSS JOIN LATERAL (
    SELECT generate_series(now() - INTERVAL '90 days', now(), INTERVAL '4 hours') AS ts
) g
CROSS JOIN LATERAL (
    SELECT EXTRACT(EPOCH FROM (now() - g.ts))/86400.0 AS days_ago
) d;

UPDATE price_history ph SET price = a.current_price
FROM assets a
WHERE ph.asset_id = a.id
  AND ph.ts = (SELECT MAX(ts) FROM price_history WHERE asset_id = a.id);


-- =====================================================================
-- 13 · RAG ÖRNEK DOKÜMANLARI
--      Tamamı SENTETİK. embedding NULL — ingestion dolduracak.
-- =====================================================================

INSERT INTO rag.documents (external_id, baslik, sirket, asset_id, tarih, tip) VALUES
('DOC-001','THYAO 2026 2. Çeyrek Finansal Sonuçları','Türk Hava Yolları',1,'2026-07-28','bilanco'),
('DOC-002','Havacılık Sektöründe Yakıt Maliyetleri Geriliyor',NULL,1,'2026-07-15','haber'),
('DOC-003','SASA Polyester Kapasite Yatırımı Ertelendi','Sasa Polyester',4,'2026-06-30','duyuru'),
('DOC-004','Petrokimya Sektörü Değerlendirme Raporu','Sasa Polyester',4,'2026-07-10','analist_raporu'),
('DOC-005','Gram Altın Talebinde Mevsimsel Artış',NULL,7,'2026-08-01','haber'),
('DOC-006','Bitcoin Kurumsal Fon Girişleri Hızlandı',NULL,12,'2026-08-05','haber'),
('DOC-007','Nvidia Veri Merkezi Gelirleri Rekor Kırdı','Nvidia',17,'2026-07-22','bilanco'),
('DOC-008','Küresel Faiz Beklentileri ve Portföy Dağılımı',NULL,NULL,'2026-08-08','analist_raporu');

INSERT INTO rag.chunks (document_id, chunk_index, content) VALUES
(1,0,'Türk Hava Yolları 2026 yılı ikinci çeyreğinde net kârını bir önceki yılın aynı dönemine göre yüzde 18 artırdı. Yolcu doluluk oranı yüzde 84 seviyesinde gerçekleşti.'),
(1,1,'Şirketin dış hat yolcu sayısındaki artış, kargo gelirlerindeki yavaşlamayı dengeledi. Yönetim yıl sonu kapasite hedefini korudu.'),
(2,0,'Jet yakıtı fiyatlarındaki gerileme havayolu şirketlerinin operasyonel maliyetlerini düşürüyor. Analistler bu eğilimin üçüncü çeyrekte kâr marjlarına olumlu yansıyacağını değerlendiriyor.'),
(3,0,'Sasa Polyester, planlanan kapasite artırım yatırımını finansman koşulları nedeniyle bir yıl erteleme kararı aldı. Şirket açıklamasında mevcut üretim hattının verimliliğine odaklanılacağı belirtildi.'),
(3,1,'Karar sonrası hisse fiyatında baskı gözlendi. Şirketin borçluluk oranı sektör ortalamasının üzerinde seyrediyor.'),
(4,0,'Petrokimya sektöründe talep zayıflığı sürüyor. Hammadde maliyetlerindeki oynaklık marjlar üzerinde baskı yaratmaya devam ediyor.'),
(4,1,'Sektörde yüksek borçluluğa sahip şirketler için finansman maliyeti kritik risk unsuru olmayı sürdürüyor. Kısa vadede toparlanma beklenmiyor.'),
(5,0,'Gram altın talebinde mevsimsel artış gözleniyor. Kuyumculuk sektörü temsilcileri düğün sezonunun perakende talebi desteklediğini belirtiyor.'),
(6,0,'Bitcoin''e yönelik kurumsal fon girişleri son çeyrekte hızlandı. Piyasa katılımcıları likidite koşullarındaki iyileşmenin fiyat üzerinde destekleyici olduğunu değerlendiriyor.'),
(6,1,'Yüksek oynaklık nedeniyle kripto varlıkların portföy içindeki ağırlığının risk toleransına göre sınırlandırılması öneriliyor.'),
(7,0,'Nvidia veri merkezi segmenti gelirleri çeyreklik bazda rekor seviyeye ulaştı. Yapay zeka altyapısına yönelik talep güçlü seyrini koruyor.'),
(7,1,'Şirket arz kısıtlarının kademeli olarak hafiflediğini bildirdi. Değerleme çarpanlarının tarihsel ortalamanın üzerinde olduğu vurgulanıyor.'),
(8,0,'Küresel faiz beklentilerindeki değişim varlık sınıfları arasındaki dağılımı yeniden şekillendiriyor. Tahvil getirilerindeki gerileme riskli varlıklara ilgiyi artırıyor.'),
(8,1,'Düşük risk toleransına sahip yatırımcılar için altın ve tahvil ağırlığının korunması, yüksek risk toleransına sahip yatırımcılar için hisse ve teknoloji ağırlığının değerlendirilmesi öneriliyor.');


-- =====================================================================
-- 14 · SEED SONRASI DOĞRULAMA
-- =====================================================================

-- a) transactions ↔ portfolio_assets tutuyor mu? (boş dönmeli)
--    SELECT h.portfolio_id, h.asset_id FROM portfolio_assets h JOIN (
--      SELECT portfolio_id, asset_id,
--             SUM(CASE transaction_type WHEN 'BUY' THEN quantity
--                 WHEN 'SELL' THEN -quantity ELSE 0 END) net
--      FROM transactions GROUP BY 1,2) t
--      ON t.portfolio_id=h.portfolio_id AND t.asset_id=h.asset_id
--    WHERE ABS(h.quantity - t.net) > 0.00000001;

-- b) Fiyat geçmişi olmayan varlık? (boş dönmeli)
--    SELECT a.symbol FROM assets a
--    LEFT JOIN price_history ph ON ph.asset_id=a.id
--    WHERE ph.asset_id IS NULL GROUP BY a.symbol;

-- c) Kur çevrimi doğru mu?
--    SELECT p.name, ROUND(s.total_value_try) deger, ROUND(s.total_pnl_pct,1) kar_yuzde
--    FROM v_portfolio_summary s JOIN portfolios p ON p.id=s.portfolio_id
--    ORDER BY s.portfolio_id;
--    → Mehmet ~1.64M TL olmalı (BTC 0.5 × 65.400 USD × 33,55 dahil).
--      ~540K çıkıyorsa USD varlıklar TRY'ye çevrilmiyor demektir.
