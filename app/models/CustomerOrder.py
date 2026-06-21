from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class CustomerOrder(Base):
    __tablename__ = "customer_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False) # napr. Xerox 1234
    created_at = Column(DateTime, default=datetime.utcnow)

    # RELÁCIA (OPRAVA: back_populates upravené na customer_order, aby sedelo s modelom Pallet)
    pallets = relationship("Pallet", back_populates="customer_order", cascade="all, delete-orphan")
