from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class PalletEvent(Base):
    __tablename__ = "pallet_events"

    id = Column(Integer, primary_key=True, index=True)

    pallet_id = Column(Integer, ForeignKey("pallets.id"), nullable=False)

    event_type = Column(String, nullable=False)
    # napr: SCANNED, SORTED, SHREDDED, MOVED, LOADED

    from_location_id = Column(Integer, nullable=True)
    to_location_id = Column(Integer, nullable=True)

    event_metadata = Column(String, nullable=True)  # voliteľné JSON ako string

    created_at = Column(DateTime(timezone=True), server_default=func.now())