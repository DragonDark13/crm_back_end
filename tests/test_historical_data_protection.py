import unittest

from models.packagingPurchaseHistory import PackagingPurchaseHistory
from models.packagingSaleHistory import PackagingSaleHistory
from models.packagingStockHistory import PackagingStockHistory
from models.payment import Payment
from models.purchaseHistory import PurchaseHistory
from models.saleHistory import SaleHistory
from models.supplier import Supplier
from models.packagingMaterial import PackagingMaterial


def foreign_key_delete_rule(model, column_name):
    column = model.__table__.columns[column_name]
    foreign_key = next(iter(column.foreign_keys))
    return foreign_key.ondelete


class HistoricalDataProtectionTests(unittest.TestCase):
    def test_supplier_deletion_does_not_cascade_purchase_history(self):
        self.assertEqual(foreign_key_delete_rule(PurchaseHistory, "supplier_id"), "SET NULL")
        self.assertFalse(Supplier.purchase_history.property.cascade.delete)
        self.assertFalse(Supplier.products.property.cascade.delete)

    def test_packaging_material_deletion_is_restricted_by_ledgers(self):
        self.assertEqual(foreign_key_delete_rule(PackagingPurchaseHistory, "material_id"), "RESTRICT")
        self.assertEqual(foreign_key_delete_rule(PackagingStockHistory, "material_id"), "RESTRICT")
        self.assertFalse(PackagingMaterial.purchase_history.property.cascade.delete)
        self.assertFalse(PackagingMaterial.stock_history.property.cascade.delete)

    def test_sale_deletion_is_restricted_by_related_records(self):
        self.assertEqual(foreign_key_delete_rule(Payment, "sale_id"), "RESTRICT")
        self.assertEqual(foreign_key_delete_rule(PackagingSaleHistory, "sale_id"), "RESTRICT")
        self.assertFalse(SaleHistory.payment.property.cascade.delete)
        self.assertFalse(SaleHistory.packaging_sale_history.property.cascade.delete)


if __name__ == "__main__":
    unittest.main()
