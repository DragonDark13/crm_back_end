from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import relationship

from models.base import Base


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    contact_info = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    products = relationship("Product", back_populates="supplier", cascade="all, delete-orphan")
    purchase_history = relationship("PurchaseHistory", back_populates="supplier", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_info': self.contact_info,
            'email': self.email,
            'phone_number': self.phone_number,
            'address': self.address,
            'is_active': self.is_active  # ← ДОДАНО
        }
