from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Pallet(Base):
    __tablename__ = "pallets"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=True)
    customer_order_id = Column(Integer, ForeignKey("customer_orders.id"), nullable=False)
    
    # Informácie o materiáli a obale
    material_type = Column(String, nullable=True)
    packaging_type = Column(String, nullable=True)  # paleta, plastovy_box, big_bag
    
    # Váhové údaje
    gross_weight = Column(Float, nullable=True)
    net_weight = Column(Float, nullable=True)
    
    # Stav palety a umiestnenie
    status = Column(String, default="PENDING")
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    
    # Prepojenie na expedíciu (Pridané pre podporu shipping.py)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # RELÁCIE
    customer_order = relationship("CustomerOrder", back_populates="pallets")
    location = relationship("Location", back_populates="pallets")
    events = relationship("PalletEvent", back_populates="pallet", cascade="all, delete-orphan")
    
    # Nová relácia smerom k expedícii
    shipment = relationship("Shipment", back_populates="pallets")

