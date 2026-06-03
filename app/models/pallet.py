# app/models/pallet.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Pallet(Base):
    __tablename__ = "pallets"

    id = Column(Integer, primary_key=True, index=True)
    # Kancelária vygeneruje dočasný kód alebo ID, logista po zvážení dostane finálny barcode
    barcode = Column(String, unique=True, index=True, nullable=True) 
    
    order_id = Column(Integer, ForeignKey("customer_orders.id"), nullable=False)
    material_type = Column(String, nullable=False) # Mix, Cartridge, PS, HDPE...
    
    # --- Váhová logika (vypĺňa logista na váhe) ---
    gross_weight = Column(Float, default=0.0)      # Váha s obalom
    tare_weight = Column(Float, default=0.0)       # Váha obalu (podľa package_type)
    net_weight = Column(Float, default=0.0)        # Čistá váha (gross - tare)
    package_type = Column(String, nullable=True)   # paleta (25kg), plastovy_box (35kg), big_bag (3kg)
    
    # --- Stavy palety ---
    # PENDING (vytvorená v kancelárii) -> WEIGHTED (odvážená logistom) -> SHREDDED / SORTED_DONE
    status = Column(String, default="PENDING") 
    
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    
    # Prepojenia
    order = relationship("CustomerOrder", back_populates="pallets")
    location = relationship("Location", back_populates="pallets")
