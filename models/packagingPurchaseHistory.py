from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Float
from sqlalchemy.orm import relationship

from models.base import Base


class PackagingPurchaseHistory(Base):
    __tablename__ = 'packaging_purchase_history'

    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='CASCADE'))
    supplier_id = Column(Integer, ForeignKey('packaging_material_suppliers.id',
                                             ondelete='SET NULL'))  # Updated to reference packaging_material_suppliers
    quantity_purchased = Column(Float, nullable=False)
    purchase_price_per_unit = Column(DECIMAL(10, 2), default=0.00)
    purchase_total_price = Column(DECIMAL(12, 2), default=0.00)
    purchase_date = Column(DateTime, default=datetime.now)
    material = relationship("PackagingMaterial", back_populates="purchase_history")
    packaging_material_supplier = relationship("PackagingMaterialSupplier")  # Updated to PackagingMaterialSupplier

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'supplier_id': self.supplier_id,
            'quantity_purchased': self.quantity_purchased,
            'purchase_price_per_unit': float(self.purchase_price_per_unit),
            'purchase_total_price': float(self.purchase_total_price),
            'purchase_date': self.purchase_date.isoformat()
        }
