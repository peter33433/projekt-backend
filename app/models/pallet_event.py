from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class PalletEvent(Base):
    __tablename__ = "pallet_events"

    id = Column(Integer, primary_key=True, index=True)
    pallet_id = Column(Integer, ForeignKey("pallets.id"), nullable=False)
    event_type = Column(String, nullable=False)  # napr. "RECEIVED", "MOVED", "SHREDDED"
    
    # ✨ PRIDÁVAME NOVÉ STĹPCE ✨
    description = Column(String, nullable=True)   # Textový popis udalosti
    timestamp = Column(DateTime, server_default=func.now(), nullable=False) # Automatický čas z DB