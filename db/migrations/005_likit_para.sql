-- 005_likit_para.sql
-- users tablosuna likit_para kolonu ekler (nakit/likit varlik, TRY).

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS likit_para DOUBLE PRECISION;