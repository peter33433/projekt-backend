from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.pallet import Pallet
from app.models.location import Location
from app.models.pallet_event import PalletEvent

router = APIRouter(prefix="/recycled", tags=["Recycled Materials Inventory"])

class QualityCheckRequest(BaseModel):
    approved: bool
    notes: str = ""

@router.get("/inventory")
def get_recycled_inventory(db: Session = Depends(get_db)):
    """
    Vráti zoznam všetkého hotového recyklovaného materiálu, ktorý je aktuálne na sklade.
    """
    recycled_materials = db.query(Pallet).filter(Pallet.status.in_(["CRUSHED", "SORTED", "STORED"])).all()
    
    inventory_summary = {}
    for item in recycled_materials:
        mat_type = item.material_type or "Neznámy mix"
        if mat_type not in inventory_summary:
            inventory_summary[mat_type] = {"total_pallets": 0, "total_net_weight": 0.0}
        
        inventory_summary[mat_type]["total_pallets"] += 1
        inventory_summary[mat_type]["total_net_weight"] += item.net_weight or 0.0
        
    return {
        "summary": inventory_summary,
        "detailed_pallets": [
            {
                "barcode": p.barcode,
                "material_type": p.material_type,
                "net_weight": p.net_weight,
                "status": p.status,
                "location_code": p.location.code if p.location else None
            } for p in recycled_materials
        ]
    }

@router.post("/{barcode}/quality-check")
def verify_recycled_material(barcode: str, request: QualityCheckRequest, db: Session = Depends(get_db)):
    """
    Schválenie výstupnej kvality recyklátu pred finálnym naskladnením alebo expedíciou.
    """
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode.strip()).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Materiál podľa čiarového kódu sa nenašiel.")

    if not request.approved:
        pallet.status = "QUALITY_REJECTED"
        event_type = "RECYCLED_QUALITY_FAILED"
        msg = f"Materiál neprešiel kontrolou kvality. Poznámka: {request.notes}"
    else:
        pallet.status = "STORED"
        event_type = "RECYCLED_QUALITY_PASSED"
        msg = f"Materiál úspešne schválený do zásob. Poznámka: {request.notes}"

    event = PalletEvent(
        pallet_id=pallet.id,
        event_type=event_type,
        description=msg
    )
    db.add(event)
    db.commit()
    
    return {"message": "Kontrola kvality bola zaevidovaná.", "pallet_barcode": pallet.barcode, "new_status": pallet.status}
