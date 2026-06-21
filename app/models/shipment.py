from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    truck_plate = Column(String, nullable=False)  # ŠPZ kamiónu
    cmr_number = Column(String, nullable=False)   # Číslo nákladného listu CMR
    status = Column(String, default="PREPARING")  # PREPARING, SHIPPED, CANCELLED
    
    created_at = Column(DateTime, default=datetime.utcnow)
    shipped_at = Column(DateTime, nullable=True)  # Vyplní sa až pri odchode kamiónu

    # RELÁCIA (Prepojenie s modelom Pallet – jedna expedícia obsahuje viacero paliet)
    pallets = relationship("Pallet", back_populates="shipment")
