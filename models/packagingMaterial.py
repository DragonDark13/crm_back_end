from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Float
from sqlalchemy.orm import relationship

from models.base import Base, db


class PackagingMaterial(Base):
    __tablename__ = 'packaging_materials'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # Назва матеріалу
    status = db.Column(db.String(50), default='available')  # статус пакування
    packaging_material_supplier_id = Column(Integer, ForeignKey('packaging_material_suppliers.id', ondelete='SET NULL'),
                                            nullable=True)  # Link to the new supplier model
    total_quantity = Column(Float, default=0)  # Загальна кількість закупленого
    available_quantity = Column(Float, default=0)  # Кількість в наявності
    sold_quantity = Column(Integer, default=0)
    purchase_price_per_unit = Column(DECIMAL(10, 2), default=0.00)  # Закупівельна ціна за одиницю
    reorder_level = Column(Float, default=0)  # Мінімальний рівень для повторного замовлення
    total_purchase_cost = Column(DECIMAL(12, 2), default=0.00)  # Загальна сума закупленого
    available_stock_cost = Column(DECIMAL(12, 2), default=0.00)  # Загальна сума того, що в наявності
    created_date = Column(DateTime, default=datetime.now)

    packaging_material_supplier = relationship("PackagingMaterialSupplier",
                                               back_populates="packaging_materials")  # New relationship
    stock_history = relationship("PackagingStockHistory", back_populates="material", cascade="all, delete-orphan")
    purchase_history = relationship("PackagingPurchaseHistory", back_populates="material", cascade="all, delete-orphan")
    reserved_quantity = Column(Integer, nullable=False, default=0)  # Додайте default=0

    # Зарезервована кількість

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'packaging_material_supplier_id': self.packaging_material_supplier_id,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'purchase_price_per_unit': float(self.purchase_price_per_unit or 0),
            'reorder_level': self.reorder_level,
            'total_purchase_cost': float(self.total_purchase_cost or 0),
            'available_stock_cost': float(self.available_stock_cost or 0),
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'supplier': self.packaging_material_supplier.to_dict() if self.packaging_material_supplier else None
        }

    def update_costs(self):
        """
        Оновлює загальну суму закупленого та суму матеріалів у наявності.
        """
        self.total_purchase_cost = self.total_quantity * float(self.purchase_price_per_unit or 0)
        self.available_stock_cost = self.available_quantity * float(self.purchase_price_per_unit or 0)
