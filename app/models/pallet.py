from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Pallet(Base):
    __tablename__ = "pallets"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, nullable=False, default="")
    customer_name = Column(String, nullable=False)
    material_type = Column(String, nullable=False)
    package_type = Column(String, nullable=False)
    tare_weight = Column(Float, default=0)
    gross_weight = Column(Float, default=0)
    net_weight = Column(Float, default=0)
    status = Column(String, default="RECEIVED")
    weight = Column(Float, default=0)
    weight_added_at = Column(DateTime, nullable=True)
    parent_id = Column(Integer, nullable=True)
    is_sorted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Správne pre Location
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Location")