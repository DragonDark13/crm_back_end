from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship

from models.base import Base


class StockHistory(Base):
    __tablename__ = 'stock_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    change_amount = Column(Integer, nullable=False)
    change_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    product = relationship("Product", back_populates="stock_history")

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'timestamp': self.timestamp,
            'change_type': self.change_type,
            'change_amount': self.change_amount
            # Add any other fields that need to be returned
        }
