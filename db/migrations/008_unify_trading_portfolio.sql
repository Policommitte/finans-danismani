-- Paper emir pozisyonlarini dashboard'un kullandigi ana portfoy kaynagina tasi.
-- Bu migrasyondan sonra yeni gerceklesmeler dogrudan portfolio_assets'i gunceller.

BEGIN;

WITH normalized_positions AS (
    SELECT pp.portfolio_id,
           pp.asset_id,
           pp.quantity,
           pp.average_buy_price / NULLIF(fx.try_rate, 0) AS average_buy_price
    FROM paper_positions pp
    JOIN assets a ON a.id = pp.asset_id
    JOIN v_fx_rates fx ON fx.currency = a.currency
    WHERE pp.quantity > 0
)
INSERT INTO portfolio_assets (portfolio_id, asset_id, quantity, average_buy_price)
SELECT portfolio_id, asset_id, quantity, average_buy_price
FROM normalized_positions
ON CONFLICT (portfolio_id, asset_id) DO UPDATE SET
    average_buy_price = CASE
        WHEN portfolio_assets.quantity + EXCLUDED.quantity > 0 THEN (
            portfolio_assets.quantity * portfolio_assets.average_buy_price
            + EXCLUDED.quantity * EXCLUDED.average_buy_price
        ) / (portfolio_assets.quantity + EXCLUDED.quantity)
        ELSE 0
    END,
    quantity = portfolio_assets.quantity + EXCLUDED.quantity;

-- Migrasyon tekrar calistirilirsa pozisyonlar ikinci kez eklenmesin.
DELETE FROM paper_positions;

COMMIT;
