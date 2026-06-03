# app/models/location.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)  # LTR1, SORTING_H12, H9-R1-P1
    zone = Column(String, nullable=False)                           # Hala 12, Hala 9
    status = Column(String, default="empty")                        # empty, occupied
    created_at = Column(DateTime, default=datetime.utcnow)

    # Vzťah na palety
    pallets = relationship("Pallet", back_populates="location")