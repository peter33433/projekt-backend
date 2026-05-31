from typing import Optional
from pydantic import BaseModel

class PalletCreate(BaseModel):
    customer_name: str
    material_type: str
    package_type: str


class PalletOut(BaseModel):
    id: int
    barcode: str
    customer_name: str
    material_type: str
    package_type: str
    status: str

    location_id: int | None = None
    parent_id: int | None = None

    gross_weight: float | None = None
    net_weight: float | None = None
    tare_weight: float | None = None

    is_sorted: int | None = None

    class Config:
        from_attributes = True

class DashboardSummary(BaseModel):
    location: str
    count: int

    class Config:
        from_attributes = True  # Umožní Pydanticu priamo konvertovať výsledky zo SQLAlchemy        

        