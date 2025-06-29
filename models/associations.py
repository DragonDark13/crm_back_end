# Association table for many-to-many relationships
from sqlalchemy import Column, Integer, ForeignKey, Table

from models.base import Base

user_roles_table = Table(
    'user_roles', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'))
)

product_categories_table = Table(
    'product_categories', Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE')),
    Column('category_id', Integer, ForeignKey('categories.id', ondelete='CASCADE'))
)
