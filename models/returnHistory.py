from datetime import datetime

from sqlalchemy import Column, String, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship, backref

from models.base import Base


class ReturnHistory(Base):
    __tablename__ = 'return_history'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'))
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='RESTRICT'))
    quantity_returned = Column(Integer, nullable=False)
    return_reason = Column(String, nullable=True)
    return_date = Column(DateTime, default=datetime.now, nullable=False)
    sale_id = Column(Integer, ForeignKey('sale_history.id', ondelete='RESTRICT'))
    return_amount = Column(DECIMAL(12, 2), nullable=True)
    returned_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    returned_by_username = Column(String(255), nullable=True)

    product = relationship("Product", backref=backref("returns", passive_deletes="all"))
    customer = relationship("Customer", backref=backref("returns", passive_deletes="all"))
    sale = relationship("SaleHistory", back_populates="returns")
    returned_by = relationship("User")
