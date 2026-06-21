from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.pallet import Pallet
from app.models.location import Location
from app.models.pallet_event import PalletEvent
from app.database import get_db

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.post("/release-to-customer")
def release_to_customer(barcode: str, db: Session = Depends(get_db)):
    # 1. Vyhľadanie palety
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta sa nenašla.")

    # 2. Kontrola stavu
    if pallet.status not in ["SORTED", "CRUSHED", "STORED"]:
        raise HTTPException(status_code=400, detail="Materiál nemožno vydať.")

    # 3. Uvoľnenie lokácie (Kritická oprava)
    if pallet.location_id:
        location = db.query(Location).filter(Location.id == pallet.location_id).first()
        if location:
            location.status = "empty" # Zmena na 'empty'

    # 4. Aktualizácia palety
    pallet.status = "RETURNED_TO_CUSTOMER"
    pallet.location_id = None 

    # Bezpečná oprava popisu (odstránenie chyby s customer_name)
    order_info = f"Objednávka ID: {pallet.customer_order_id}"
    if hasattr(pallet, 'customer_order') and pallet.customer_order:
        order_info = f"Číslo objednávky: {pallet.customer_order.order_number}"

    # 5. História a commit
    new_event = PalletEvent(
        pallet_id=pallet.id,
        event_type="RELEASED",
        description=f"Vydané: {order_info}"
    )
    db.add(new_event)
    db.commit()
    db.refresh(pallet)

    return {"message": "Materiál bol úspešne odovzdaný.", "pallet": pallet}
