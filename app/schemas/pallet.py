from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Společný základ pro paletu
class PalletBase(BaseModel):
    packaging_type: Optional[str] = "paleta"
    material_type: Optional[str] = None

# Schéma pro vytvoření nové palety (při příjmu)
class PalletCreate(BaseModel):
    customer_order_id: int
    packaging_type: str

# Schéma pro vážení a naskladnění palety
class PalletWeighAndStore(BaseModel):
    gross_weight: float
    location_code: str

# Schéma pro response (výstup z API)
class PalletResponse(PalletBase):
    id: int
    barcode: Optional[str] = None
    customer_order_id: int
    gross_weight: Optional[float] = None
    net_weight: Optional[float] = None
    status: str
    location_id: Optional[int] = None
    shipment_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schémata pro operaci Třídění (Sorting Split)
class PalletSplitItem(BaseModel):
    material_type: str
    gross_weight: float
    packaging_type: str

class PalletSplitRequest(BaseModel):
    items: List[PalletSplitItem]

        