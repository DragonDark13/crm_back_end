from models.associations import product_categories_table
from models.base import Base
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Float
from sqlalchemy.orm import relationship


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    products = relationship("Product", secondary=product_categories_table, back_populates="categories")
