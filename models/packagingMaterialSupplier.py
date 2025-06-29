from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship

from models.base import Base


class PackagingMaterialSupplier(Base):
    __tablename__ = 'packaging_material_suppliers'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    contact_info = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    packaging_materials = relationship("PackagingMaterial", back_populates="packaging_material_supplier",
                                       cascade="all, delete-orphan")
    purchase_history = relationship("PackagingPurchaseHistory",
                                    back_populates="packaging_material_supplier")  # New relationship added

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_info': self.contact_info,
            'email': self.email,
            'phone_number': self.phone_number,
            'address': self.address,
        }
