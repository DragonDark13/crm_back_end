-- Preserve product and customer history when parent records are deleted.
-- The migration is repeatable: matching foreign keys are replaced on every run.

DO $$
DECLARE
    fk_record RECORD;
BEGIN
    FOR fk_record IN
        SELECT
            conrelid::regclass AS table_name,
            conname
        FROM pg_constraint
        WHERE contype = 'f'
          AND (
              (conrelid = 'sale_history'::regclass
               AND confrelid = 'products'::regclass
               AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (product_id)%')
              OR
              (conrelid = 'sale_history'::regclass
               AND confrelid = 'customers'::regclass
               AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (customer_id)%')
              OR
              (conrelid = 'purchase_history'::regclass
               AND confrelid = 'products'::regclass
               AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (product_id)%')
              OR
              (conrelid = 'stock_history'::regclass
               AND confrelid = 'products'::regclass
               AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (product_id)%')
              OR
              (conrelid = 'return_history'::regclass
               AND confrelid = 'products'::regclass
               AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (product_id)%')
              OR
              (conrelid = 'return_history'::regclass
               AND confrelid = 'customers'::regclass
               AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (customer_id)%')
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE %s DROP CONSTRAINT %I',
            fk_record.table_name,
            fk_record.conname
        );
    END LOOP;
END $$;

ALTER TABLE sale_history
    ADD CONSTRAINT fk_sale_history_product_restrict
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT;

ALTER TABLE sale_history
    ADD CONSTRAINT fk_sale_history_customer_restrict
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT;

ALTER TABLE purchase_history
    ADD CONSTRAINT fk_purchase_history_product_restrict
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT;

ALTER TABLE stock_history
    ADD CONSTRAINT fk_stock_history_product_restrict
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT;

ALTER TABLE return_history
    ADD CONSTRAINT fk_return_history_product_restrict
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT;

ALTER TABLE return_history
    ADD CONSTRAINT fk_return_history_customer_restrict
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT;
