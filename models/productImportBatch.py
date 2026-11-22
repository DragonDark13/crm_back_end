from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from models.base import Base


class ProductImportBatch(Base):
    __tablename__ = "product_import_batches"

    id = Column(Integer, primary_key=True)
    file_hash = Column(String(64), nullable=False, unique=True, index=True)
    file_name = Column(String(255), nullable=False)
    rows_imported = Column(Integer, nullable=False)
    imported_at = Column(DateTime, nullable=False, default=datetime.now)
