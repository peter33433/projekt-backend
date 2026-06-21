from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.pallet import Pallet
from app.models.location import Location
from app.models.pallet_event import PalletEvent
# Předpokládá se existence modelu Shipment v app/models/shipment.py
from app.models.shipment import Shipment  

router = APIRouter(prefix="/shipping", tags=["Shipping & Expeditions"])

# Pydantic schémata pro validaci vstupů
class ShipmentCreate(BaseModel):
    customer_name: str
    truck_plate: str  # SPZ kamionu
    cmr_number: str   # Číslo nákladního listu CMR

class AddPalletsRequest(BaseModel):
    barcodes: List[str]

@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_shipment(data: ShipmentCreate, db: Session = Depends(get_db)):
    """
    Založí nový expediční list (nakládku kamionu).
    """
    new_shipment = Shipment(
        customer_name=data.customer_name,
        truck_plate=data.truck_plate,
        cmr_number=data.cmr_number,
        status="PREPARING",  # PREPARING, SHIPPED, CANCELLED
        created_at=datetime.utcnow()
    )
    db.add(new_shipment)
    db.commit()
    db.refresh(new_shipment)
    
    return {"message": "Expedícia bola úspešne vytvorená.", "shipment_id": new_shipment.id, "status": new_shipment.status}

@router.post("/{shipment_id}/add-pallets")
def add_pallets_to_shipment(shipment_id: int, request: AddPalletsRequest, db: Session = Depends(get_db)):
    """
    Přiřadí naskenované palety k rozpracované expedici.
    """
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Expedícia sa nenašla.")
    
    if shipment.status != "PREPARING":
        raise HTTPException(status_code=400, detail="Do tejto expedície už nie je možné pridávať palety.")

    updated_count = 0
    
    for barcode in request.barcodes:
        pallet = db.query(Pallet).filter(Pallet.barcode == barcode.strip()).first()
        if not pallet:
            raise HTTPException(status_code=404, detail=f"Paleta s kódom {barcode} sa nenašla.")
        
        if pallet.status not in ["STORED", "CRUSHED", "SORTED"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Paleta {barcode} má stav {pallet.status}. Expedovať možno len hotový/naskladnený materiál."
            )

        # Navázání palety na expedici (předpokládá sloupec shipment_id v modelu Pallet)
        if hasattr(pallet, 'shipment_id'):
            pallet.shipment_id = shipment.id
            pallet.status = "READY_TO_SHIP"
            
            # Zápis události
            event = PalletEvent(
                pallet_id=pallet.id,
                event_type="ADDED_TO_SHIPPING",
                description=f"Paleta pripravená na nakládku do expedície ID {shipment_id}."
            )
            db.add(event)
            updated_count += 1

    db.commit()
    return {"message": f"Úspešne pridaných {updated_count} paliet do expedície.", "shipment_id": shipment_id}

@router.post("/{shipment_id}/dispatch")
def dispatch_shipment(shipment_id: int, db: Session = Depends(get_db)):
    """
    Potvrdí odjezd kamionu. Hromadně uvolní pozice v regálech a uzavře palety i expedici.
    """
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Expedícia sa nenašla.")
        
    if shipment.status != "PREPARING":
        raise HTTPException(status_code=400, detail="Expedícia už bola odoslaná alebo zrušená.")

    # Vyhledání všech paliet v této expedici
    pallets = db.query(Pallet).filter(Pallet.shipment_id == shipment_id).all()
    if not pallets:
        raise HTTPException(status_code=400, detail="Nie je možné odoslať prázdnu expedíciu bez paliet.")

    try:
        for pallet in pallets:
            # Uvolnění pozice v regálu
            if pallet.location_id:
                location = db.query(Location).filter(Location.id == pallet.location_id).first()
                if location:
                    location.status = "empty"
            
            # Finální stav palety
            pallet.location_id = None
            pallet.status = "SHIPPED"
            
            # Zápis do historie palety
            event = PalletEvent(
                pallet_id=pallet.id,
                event_type="SHIPPED",
                description=f"Materiál opustil sklad kamiónom {shipment.truck_plate}. CMR: {shipment.cmr_number}."
            )
            db.add(event)

        # Uzavření expedice
        shipment.status = "SHIPPED"
        shipment.shipped_at = datetime.utcnow()
        
        db.commit()
        return {"message": "Expedícia bola úspešne odoslaná, kamión odišiel a pozície sú voľné."}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Chyba pri uzatváraní expedície: {e}")
