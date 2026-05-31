from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(String, unique=True, index=True)   # A1-01-03
    zone = Column(String)                            # WAREHOUSE / SORTING / LTR1
    is_active = Column(Boolean, default=True)