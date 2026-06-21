from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.pallet import Pallet
from app.models.location import Location
from app.models.pallet_event import PalletEvent
from app.database import get_db

router = APIRouter(prefix="/shredding", tags=["Shredding"])

@router.post("/start")
def start_shredding(barcode: str, line_code: str, db: Session = Depends(get_db)):
    clean_barcode = barcode.strip()
    clean_line = line_code.strip()

    location = db.query(Location).filter(Location.code == clean_line).first()
    if not location:
        raise HTTPException(status_code=404, detail=f"Linka {clean_line} nenalezena.")

    pallet = db.query(Pallet).filter(func.trim(Pallet.barcode) == clean_barcode).first()
    if not pallet or pallet.status not in ["WEIGHTED", "SORTED", "RECEIVED", "TRANSFERRED", "LABELED"]:
        raise HTTPException(status_code=400, detail="Paleta není připravena k drcení.")

    pallet.status = "SHREDDING"
    pallet.location_id = location.id
    db.add(PalletEvent(pallet_id=pallet.id, event_type="SHREDDING_STARTED", description=f"Linka {clean_line}"))
    db.commit()
    return {"message": "Drcení zahájeno", "pallet": pallet}

@router.post("/end")
def end_shredding(barcode: str, db: Session = Depends(get_db)):
    pallet = db.query(Pallet).filter(func.trim(Pallet.barcode) == barcode.strip()).first()
    if not pallet or pallet.status != "SHREDDING":
        raise HTTPException(status_code=400, detail="Paleta se nedrtí.")

    pallet.status = "CRUSHED"
    pallet.location_id = None
    db.add(PalletEvent(pallet_id=pallet.id, event_type="SHREDDING_ENDED", description="Drcení ukončeno"))
    db.commit()
    return {"message": "Drcení ukončeno", "pallet": pallet}
