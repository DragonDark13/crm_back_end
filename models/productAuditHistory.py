from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from models.base import Base


class ProductAuditHistory(Base):
    __tablename__ = "product_audit_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_by_username = Column(String(255), nullable=False, default="Невідомий користувач")
    action = Column(String(50), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=False, default=datetime.now)
