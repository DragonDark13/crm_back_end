from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship, backref

from models.base import Base


class ReturnHistory(Base):
    __tablename__ = 'return_history'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'))
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='RESTRICT'))
    quantity_returned = Column(Integer, nullable=False)
    return_reason = Column(String, nullable=True)
    return_date = Column(DateTime, default=datetime.now)

    # sale_id to link returns to sales
    sale_id = Column(Integer, ForeignKey('sale_history.id', ondelete='CASCADE'))

    # Relationships
    product = relationship("Product", backref=backref("returns", passive_deletes="all"))
    customer = relationship("Customer", backref=backref("returns", passive_deletes="all"))

    # Use 'sale_history' to reference the SaleHistory in the reverse relationship
    sale = relationship("SaleHistory", back_populates="returns", overlaps="sale_history")  # Resolve the overlap warning
