from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.pallet import PalletResponse

# Základ pro objednávku
class CustomerOrderBase(BaseModel):
    order_number: str

# Vytvoření objednávky
class CustomerOrderCreate(CustomerOrderBase):
    pass

# Výstupní schéma objednávky včetně navázaných palet
class CustomerOrderResponse(CustomerOrderBase):
    id: int
    created_at: datetime
    pallets: List[PalletResponse] = []

    class Config:
        from_attributes = True

# Základ pro zákazníka (pokud v budoucnu rozšíříte detaily)
class CustomerBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
