from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)  # napr. H9-R1-P1, LTR1, SORTING_H12
    zone = Column(String, nullable=False)  # napr. Hala 9, Hala 12
    status = Column(String, default="empty")  # empty, occupied

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # RELÁCIA (Prepojenie s modelom Pallet pre správny obojstranný chod)
    pallets = relationship("Pallet", back_populates="location")
