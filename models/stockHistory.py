from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Text
from sqlalchemy.orm import relationship

from models.base import Base


class StockHistory(Base):
    __tablename__ = 'stock_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'))
    change_amount = Column(Integer, nullable=False)
    change_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    quantity_before = Column(Integer, nullable=True)
    quantity_after = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    product = relationship("Product", back_populates="stock_history")

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'timestamp': self.timestamp,
            'change_type': self.change_type,
            'change_amount': self.change_amount,
            'quantity_before': self.quantity_before,
            'quantity_after': self.quantity_after,
            'reason': self.reason
            # Add any other fields that need to be returned
        }
