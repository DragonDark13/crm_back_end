-- Add audit details for product inventory records.
-- Run this script once against the CRM PostgreSQL database.

BEGIN;

ALTER TABLE stock_history
    ADD COLUMN IF NOT EXISTS quantity_before INTEGER;

ALTER TABLE stock_history
    ADD COLUMN IF NOT EXISTS quantity_after INTEGER;

ALTER TABLE stock_history
    ADD COLUMN IF NOT EXISTS reason TEXT;

COMMIT;
