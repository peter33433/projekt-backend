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

    # 1. Ověření linky
    location = db.query(Location).filter(Location.code == clean_line).first()
    if not location:
        raise HTTPException(status_code=404, detail=f"Linka {clean_line} nenalezena.")

    # 2. Ověření palety
    pallet = db.query(Pallet).filter(func.trim(Pallet.barcode) == clean_barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta s tímto kódem neexistuje.")

    # Záchrana pro testování: Pokud paleta uvízla ve starém stavu, dovolíme ji drtit
    if pallet.status not in ["WEIGHTED", "SORTED", "RECEIVED", "TRANSFERRED", "LABELED", "SHREDDING"]:
        raise HTTPException(status_code=400, detail=f"Paleta má stav {pallet.status} a není připravena k drcení.")

    # 3. Změna stavu a uložení (OPRAVA: db.add)
    pallet.status = "SHREDDING"
    pallet.location_id = location.id
    
    db.add(pallet)  # Vynutíme aktualizaci palety v DB
    db.add(PalletEvent(pallet_id=pallet.id, event_type="SHREDDING_STARTED", description=f"Linka {clean_line}"))
    db.commit()
    db.refresh(pallet)
    
    return {"message": "Drcení úspěšně zahájeno", "pallet_barcode": pallet.barcode, "status": pallet.status}

@router.post("/end")
def end_shredding(barcode: str, db: Session = Depends(get_db)):
    pallet = db.query(Pallet).filter(func.trim(Pallet.barcode) == barcode.strip()).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta nenalezena.")
        
    if pallet.status != "SHREDDING":
        raise HTTPException(status_code=400, detail=f"Paleta se nedrtí. Její aktuální stav je: {pallet.status}")

    # 4. Ukončení drcení a uložení
    pallet.status = "CRUSHED"
    pallet.location_id = None
    
    db.add(pallet)  # Vynutíme aktualizaci palety v DB
    db.add(PalletEvent(pallet_id=pallet.id, event_type="SHREDDING_ENDED", description="Drcení ukončeno"))
    db.commit()
    
    return {"message": "Drcení úspěšně ukončeno", "pallet_barcode": pallet.barcode, "status": pallet.status}
