from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Date, Float
from sqlalchemy.orm import relationship

from models.base import Base

class PurchaseHistory(Base):
    __tablename__ = 'purchase_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    supplier_id = Column(Integer, ForeignKey('suppliers.id', ondelete='CASCADE'))
    purchase_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    purchase_total_price = Column(DECIMAL(10, 2), default=0.00)
    purchase_date = Column(Date, nullable=False)
    quantity_purchase = Column(Float, nullable=False)
    product = relationship("Product", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchase_history")

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'supplier_id': self.supplier_id,
            'purchase_price_per_item': float(self.purchase_price_per_item),
            'purchase_total_price': float(self.purchase_total_price),
            'purchase_date': self.purchase_date.strftime('%Y-%m-%d'),
            'quantity_purchase': self.quantity_purchase,
            'supplier': self.supplier.to_dict() if self.supplier else None

        }


