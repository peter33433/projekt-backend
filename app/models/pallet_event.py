from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PalletEvent(Base):
    __tablename__ = "pallet_events"

    id = Column(Integer, primary_key=True, index=True)
    pallet_id = Column(Integer, ForeignKey("pallets.id"), nullable=False)
    event_type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    # RELÁCIA (Prepojenie s modelom Pallet pre bezchybný chod histórie)
    pallet = relationship("Pallet", back_populates="events")
