from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship

from models.associations import product_categories_table
from models.base import Base


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    action = Column(String, nullable=False)  # Наприклад, "add_product", "update_stock"
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    user = relationship("User")
