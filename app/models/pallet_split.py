from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime

from app.database import Base


class PalletSplit(Base):
    __tablename__ = "pallet_splits"

    id = Column(Integer, primary_key=True, index=True)

    parent_label = Column(String, nullable=False)
    child_label = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)