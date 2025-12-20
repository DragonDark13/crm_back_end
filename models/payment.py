from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship

from models.base import Base


class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sale_history.id', ondelete='CASCADE'))
    amount_paid = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(String, nullable=False)  # Наприклад, "Card", "Cash", "Online"
    payment_date = Column(DateTime, default=datetime.now)
    sale = relationship("SaleHistory", back_populates="payment")
