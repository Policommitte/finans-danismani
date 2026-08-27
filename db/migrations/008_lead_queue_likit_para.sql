-- 008_lead_queue_likit_para.sql
-- lead_queue_entries'e likit_para ekler: pivot sonrasi karari veren asil
-- sayi (atil bakiye) hicbir yerde arsivlenmiyordu, total_value_try artik
-- uygun her lead icin sabit 0 - anlamsiz bir anlik goruntu.

ALTER TABLE lead_queue_entries
    ADD COLUMN IF NOT EXISTS likit_para NUMERIC NOT NULL DEFAULT 0;
