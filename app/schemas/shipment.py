from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.pallet import PalletResponse

# Vstupní data pro vytvoření expedice
class ShipmentCreate(BaseModel):
    customer_name: str
    truck_plate: str
    cmr_number: str

# Požadavek na přidání palet do expedice pomocí čárových kódů
class AddPalletsRequest(BaseModel):
    barcodes: List[str]

# Schéma pro response (výstup z API)
class ShipmentResponse(BaseModel):
    id: int
    customer_name: str
    truck_plate: str
    cmr_number: str
    status: str
    created_at: datetime
    shipped_at: Optional[datetime] = None
    pallets: List[PalletResponse] = []

    class Config:
        from_attributes = True
