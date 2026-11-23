"""Prevent destructive cascades from erasing inventory and sales history.

Revision ID: b6d9e2a4c810
Revises: f2c7a91e6b40
"""
from alembic import op

revision = "b6d9e2a4c810"
down_revision = "f2c7a91e6b40"
branch_labels = None
depends_on = None


def _replace_fk(table, column, referred_table, name, ondelete):
    op.execute(f"""
    DO $$
    DECLARE fk_record RECORD;
    BEGIN
        FOR fk_record IN
            SELECT conname
            FROM pg_constraint
            WHERE contype = 'f'
              AND conrelid = '{table}'::regclass
              AND confrelid = '{referred_table}'::regclass
              AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY ({column})%'
        LOOP
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', '{table}', fk_record.conname);
        END LOOP;
    END $$;
    """)
    op.execute(
        f"ALTER TABLE {table} ADD CONSTRAINT {name} "
        f"FOREIGN KEY ({column}) REFERENCES {referred_table}(id) ON DELETE {ondelete}"
    )


def upgrade():
    # Deleting a supplier must not delete purchase history.
    _replace_fk("purchase_history", "supplier_id", "suppliers",
                "fk_purchase_history_supplier_set_null", "SET NULL")

    # Packaging purchase and stock ledgers must survive attempts to delete materials.
    _replace_fk("packaging_purchase_history", "material_id", "packaging_materials",
                "fk_packaging_purchase_material_restrict", "RESTRICT")
    _replace_fk("packaging_stock_history", "material_id", "packaging_materials",
                "fk_packaging_stock_material_restrict", "RESTRICT")

    # A sale cannot be removed while its payment or packaging-sale record exists.
    _replace_fk("payments", "sale_id", "sale_history",
                "fk_payments_sale_restrict", "RESTRICT")
    _replace_fk("packaging_sale_history", "sale_id", "sale_history",
                "fk_packaging_sale_history_sale_restrict", "RESTRICT")

    # Enforce the historical references already intended by the SQL migration.
    _replace_fk("sale_history", "product_id", "products",
                "fk_sale_history_product_restrict", "RESTRICT")
    _replace_fk("sale_history", "customer_id", "customers",
                "fk_sale_history_customer_restrict", "RESTRICT")
    _replace_fk("purchase_history", "product_id", "products",
                "fk_purchase_history_product_restrict", "RESTRICT")
    _replace_fk("stock_history", "product_id", "products",
                "fk_stock_history_product_restrict", "RESTRICT")
    _replace_fk("return_history", "product_id", "products",
                "fk_return_history_product_restrict", "RESTRICT")
    _replace_fk("return_history", "customer_id", "customers",
                "fk_return_history_customer_restrict", "RESTRICT")


def downgrade():
    # Downgrade restores the previous schema behavior. Do not run it on a live
    # database unless the operator explicitly accepts the historical-data risk.
    _replace_fk("purchase_history", "supplier_id", "suppliers",
                "fk_purchase_history_supplier_cascade", "CASCADE")
    _replace_fk("packaging_purchase_history", "material_id", "packaging_materials",
                "fk_packaging_purchase_material_cascade", "CASCADE")
    _replace_fk("packaging_stock_history", "material_id", "packaging_materials",
                "fk_packaging_stock_material_cascade", "CASCADE")
    _replace_fk("payments", "sale_id", "sale_history",
                "fk_payments_sale_cascade", "CASCADE")
    _replace_fk("packaging_sale_history", "sale_id", "sale_history",
                "fk_packaging_sale_history_sale_cascade", "CASCADE")
