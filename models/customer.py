from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship

from models.base import Base


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    contact_info = Column(String, nullable=True)
    address = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    sales = relationship("SaleHistory", back_populates="customer", cascade="all, delete-orphan")
    gift_set_sales = relationship('GiftSetSalesHistory', back_populates='customer')  # <-- змінено ім'я

    def to_dict(self, include_sales=False):
        customer_data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'address': self.address,
            'phone_number': self.phone_number
        }

        if include_sales:
            customer_data['sales'] = [
                sale.to_dict() for sale in self.sales
            ]

        return customer_data
