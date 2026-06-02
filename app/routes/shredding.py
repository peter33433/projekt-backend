from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.pallet import Pallet  
from app.models.location import Location
from app.database import get_db

router = APIRouter(
    prefix="/shredding",
    tags=["Shredding"]
)

@router.post("/start")
def start_shredding(barcode: str, line_code: str, db: Session = Depends(get_db)):
    """
    Spustí proces drtenia pre paletu.
    """
    # Očistíme vstup od prípadných prázdnych znakov/medzier
    clean_barcode = barcode.strip()
    clean_line = line_code.strip()

    # 1. Overenie lokácie linky (napr. "HALA-12-LTR1")
    location = db.query(Location).filter(Location.code == clean_line).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drtiacia linka '{clean_line}' neexistuje."
        )

    # 2. Vyhľadanie palety (použijeme funkciu func.trim na odstránenie skrytých medzier z DB)
    from sqlalchemy import func
    pallet = db.query(Pallet).filter(func.trim(Pallet.barcode) == clean_barcode).first()
    
    if not pallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Paleta s kódom '{clean_barcode}' sa v databáze nenašla. Skontroluj, či sa uložila pri splite."
        )
    
    # 3. Očistíme stav z DB od medzier pre bezpečné porovnanie
    current_status = pallet.status.strip() if pallet.status else ""

    # Povolené stavy pre drvenie (berieme do úvahy aj stavy s medzerami)
    allowed_statuses = ["WEIGHTED", "SORTED", "RECEIVED", "TRANSFERRED"]

    if current_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paletu {clean_barcode} nie je možné drviť. Aktuálny čistý stav je: '{current_status}'"
        )

    # 4. Aktualizácia pre začiatok drtenia
    pallet.status = "SHREDDING"
    pallet.location_id = location.id
    
    db.commit()
    db.refresh(pallet)
    
    return {"message": f"Drtenie palety {clean_barcode} úspešne spustené.", "pallet": pallet}

@router.post("/end")
def end_shredding(barcode: str, db: Session = Depends(get_db)):
    """
    Ukončí proces drtenia.
    """
    clean_barcode = barcode.strip()
    from sqlalchemy import func
    pallet = db.query(Pallet).filter(func.trim(Pallet.barcode) == clean_barcode).first()
    
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta sa nenašla.")
    
    current_status = pallet.status.strip() if pallet.status else ""
    if current_status != "SHREDDING":
        raise HTTPException(status_code=400, detail=f"Materiál sa momentálne nedrtí. Stav: '{current_status}'")

    pallet.status = "CRUSHED"
    pallet.location_id = None  
    
    db.commit()
    db.refresh(pallet)
    return {"message": f"Materiál z palety {clean_barcode} bol úspešne zdrvený.", "pallet": pallet}
