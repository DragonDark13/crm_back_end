from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Float
from sqlalchemy.orm import relationship

from models.base import Base

class SaleHistory(Base):
    __tablename__ = 'sale_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='CASCADE'))
    quantity_sold = Column(Integer, nullable=False)
    selling_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    selling_total_price = Column(DECIMAL(12, 2), default=0.00)
    sale_date = Column(DateTime, default=datetime.now)
    product = relationship("Product", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    payment = relationship("Payment", uselist=False, back_populates="sale", cascade="all, delete-orphan")
    profit = Column(DECIMAL(10, 2), default=0.00)

    # Packaging material fields
    packaging_material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='SET NULL'), nullable=True)
    packaging_quantity = Column(Float, default=0, nullable=True)  # Packaging quantity can be null or 0
    total_packaging_cost = Column(Float, default=0, nullable=True)  # Packaging cost can be null or 0
    packaging_material = relationship("PackagingMaterial")  # Link to packaging material if exists

    returns = relationship("ReturnHistory", back_populates="sale", cascade="all, delete-orphan")
    packaging_sale_history = relationship("PackagingSaleHistory", back_populates="sale", cascade="all, delete-orphan")

    def to_dict(self, include_customer=False):
        result = {
            'id': self.id,
            'product_id': self.product_id,
            'customer_id': self.customer_id,
            'quantity_sold': self.quantity_sold,
            'selling_price_per_item': float(self.selling_price_per_item),
            'selling_total_price': float(self.selling_total_price),
            'sale_date': self.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            'profit': float(self.profit),
            'packaging_material_id': self.packaging_material_id,
            'packaging_quantity': self.packaging_quantity,
            'total_packaging_cost': self.total_packaging_cost
        }
        if include_customer and self.customer:
            result['customer'] = self.customer.to_dict()  # Add customer info if needed
        return result
