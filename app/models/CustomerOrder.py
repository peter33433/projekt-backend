# app/models/CustomerOrder.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base  # <-- OPRAVENÉ: Pridaný chýbajúci import pre Base

class CustomerOrder(Base):
    __tablename__ = "customer_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)  # napr. Xerox 1234
    created_at = Column(DateTime, default=datetime.utcnow)

    # Vzťah na palety, ktoré patria pod túto zákazku
    # (back_populates="order" musí sedieť s premennou order v modeli Pallet)
    pallets = relationship("Pallet", back_populates="order")
