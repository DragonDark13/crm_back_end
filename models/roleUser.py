from flask_login import UserMixin
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from models.associations import user_roles_table
from models.base import Base


class Role(Base, UserMixin):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    users = relationship("User", secondary=user_roles_table, back_populates="roles")


class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)
    active = Column(Integer, default=1)
    confirmed_at = Column(DateTime, nullable=True)
    fs_uniquifier = Column(String(255), unique=True, nullable=False)  # Add fs_uniquifier
    roles = relationship("Role", secondary=user_roles_table, back_populates="users")

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def verify_password(self, password):
        """Verifies the provided password against the stored hashed password."""
        return check_password_hash(self.password, password)
