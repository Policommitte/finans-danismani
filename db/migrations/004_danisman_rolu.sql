-- 004_danisman_rolu.sql
-- users tablosuna rol kolonu ekler: customer (varsayilan) / advisor.
-- Danisman ekranina (/danisman) ve /api/leads/* uclarina erisim bu kolona
-- gore kisitlanacak (bkz. backend/app/auth/deps.py::CurrentAdvisor).

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'customer';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_role_check'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_role_check
            CHECK (role IN ('customer', 'advisor'));
    END IF;
END $$;