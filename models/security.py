from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, Index

from models.base import Base


class TokenBlocklist(Base):
    __tablename__ = "jwt_token_blocklist"

    id = Column(Integer, primary_key=True)
    jti = Column(String(36), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_jwt_token_blocklist_expires_at", "expires_at"),
    )


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False)
    ip_address = Column(String(64), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    window_started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("username", "ip_address", name="uq_login_attempt_username_ip"),
        Index("ix_login_attempt_locked_until", "locked_until"),
    )


class LoginIPAttempt(Base):
    __tablename__ = "login_ip_attempts"

    id = Column(Integer, primary_key=True)
    ip_address = Column(String(64), nullable=False, unique=True, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    window_started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    locked_until = Column(DateTime(timezone=True), nullable=True)
