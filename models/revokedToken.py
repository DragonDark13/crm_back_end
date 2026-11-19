from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from models.base import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True)
    jti = Column(String(36), unique=True, nullable=False, index=True)
    token_type = Column(String(16), nullable=False)
    user_identity = Column(String(255), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
