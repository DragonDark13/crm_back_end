from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from datetime import datetime

from models.base import Base


class ProductImportRow(Base):
    __tablename__ = "product_import_rows"
    __table_args__ = (
        UniqueConstraint(
            "fingerprint",
            "occurrence_index",
            name="uq_product_import_rows_fingerprint_occurrence",
        ),
    )

    id = Column(Integer, primary_key=True)
    purchase_history_id = Column(
        Integer,
        ForeignKey("purchase_history.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    fingerprint = Column(String(64), nullable=False, index=True)
    occurrence_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
