from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime, Float, Date
from sqlalchemy.orm import relationship

from models.base import Base


class OtherInvestment(Base):
    __tablename__ = "other_investments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String, nullable=False)  # Назва типу вкладення
    supplier = Column(String, nullable=False)
    cost = Column(Float, nullable=False)  # Вартість
    date = Column(Date, nullable=False)  # Дата

    def to_dict(self):
        """Convert OtherInvestment instance to a dictionary."""
        return {
            'id': self.id,
            'type_name': self.type_name,
            'supplier': self.supplier,
            'cost': float(self.cost or 0),  # Convert to float, handling possible None
            'date': self.date.isoformat() if self.date else None,  # Format date to ISO string
        }
