from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Float
from sqlalchemy.orm import relationship

from models.base import Base

class PackagingStockHistory(Base):
    __tablename__ = 'packaging_stock_history'

    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='CASCADE'))
    change_amount = Column(Float, nullable=False)  # Зміна кількості (позитивна або негативна)
    change_type = Column(String, nullable=False)  # Тип зміни (закупівля, списання тощо)
    timestamp = Column(DateTime, default=datetime.now)
    material = relationship("PackagingMaterial", back_populates="stock_history")

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'change_amount': self.change_amount,
            'change_type': self.change_type,
            'timestamp': self.timestamp.isoformat()
        }
