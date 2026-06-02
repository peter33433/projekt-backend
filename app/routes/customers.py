from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.pallet import Pallet  
from app.models.pallet_event import PalletEvent
from app.database import get_db

router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)

@router.post("/release-to-customer")
def release_to_customer(barcode: str, db: Session = Depends(get_db)):
    """
    Vydá vysortovaný materiál z Haly 9 späť zákazníkovi, ktorý si ho vyžiadal.
    """
    # 1. Vyhľadanie palety podľa čiarového kódu
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paleta s týmto kódom sa nenašla."
        )

    # 2. Kontrola, či je paleta v správnom stave na výdaj
    # Vydávame len materiál, ktorý už prešiel triedením (SORTED)
    if pallet.status != "SORTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Zákazníkovi je možné vydať len kompletne vytriedený materiál. Aktuálny stav: {pallet.status}"
        )

    # 3. Aktualizácia stavu palety
    pallet.status = "RETURNED_TO_CUSTOMER"
    pallet.location_id = None  # Materiál opúšťa sklad, uvoľníme skladovú pozíciu

    # 4. Zápis do histórie pohybov (PalletEvent)
    new_event = PalletEvent(
        pallet_id=pallet.id,
        event_type="RELEASED",
        description=f"Materiál bol úspešne odovzdaný a vydaný zákazníkovi: {pallet.customer_name}"
    )
    db.add(new_event)

    db.commit()
    db.refresh(pallet)
    
    return {"message": f"Materiál z palety {barcode} bol úspešne odovzdaný zákazníkovi.", "pallet": pallet}