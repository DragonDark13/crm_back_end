from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship

from models.associations import product_categories_table
from models.base import Base


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True)
    total_quantity = Column(Integer, default=0)  # Загальна кількість закупленого
    available_quantity = Column(Integer, default=0)  # Кількість в наявності
    sold_quantity = Column(Integer, default=0)  # Кількість проданого
    purchase_total_price = Column(DECIMAL(10, 2), default=0.00)
    purchase_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    selling_total_price = Column(DECIMAL(10, 2), default=0.00)
    selling_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    selling_quantity = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.now)
    supplier = relationship("Supplier", back_populates="products")
    stock_history = relationship("StockHistory", back_populates="product", cascade="all, delete-orphan")
    purchases = relationship("PurchaseHistory", back_populates="product", cascade="all, delete-orphan")
    sales = relationship("SaleHistory", back_populates="product", cascade="all, delete-orphan")
    categories = relationship("Category", secondary=product_categories_table, back_populates="products")
    reorder_level = Column(Integer, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)  # Додайте default=0
    article = Column(String(20), unique=True, nullable=False)

    def to_dict(self):
        """Convert product instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'supplier_id': self.supplier_id,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'sold_quantity': self.sold_quantity,
            'purchase_total_price': float(self.purchase_total_price or 0),
            'purchase_price_per_item': float(self.purchase_price_per_item or 0),
            'selling_total_price': float(self.selling_total_price or 0),
            'selling_price_per_item': float(self.selling_price_per_item or 0),
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'article': self.article

        }
