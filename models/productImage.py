from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import relationship

from models.base import Base


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(50), nullable=False)
    image_data = Column(LargeBinary, nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    product = relationship("Product", back_populates="images")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "url": f"/product/{self.product_id}/images/{self.id}",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
