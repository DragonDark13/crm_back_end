from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Float
from sqlalchemy.orm import relationship

from models.base import Base

class PackagingSaleHistory(Base):
    __tablename__ = 'packaging_sale_history'

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sale_history.id', ondelete='CASCADE'))
    packaging_material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='SET NULL'))
    packaging_quantity = Column(Float, nullable=False)
    total_packaging_cost = Column(DECIMAL(12, 2), nullable=False)
    sale_date = Column(DateTime, default=datetime.now)

    sale = relationship("SaleHistory", back_populates="packaging_sale_history")
    packaging_material = relationship("PackagingMaterial")

    def to_dict(self):
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'packaging_material_id': self.packaging_material_id,
            'packaging_quantity': self.packaging_quantity,
            'total_packaging_cost': float(self.total_packaging_cost),
            'sale_date': self.sale_date.isoformat()
        }
