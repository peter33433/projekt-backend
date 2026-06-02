from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.pallet import Pallet  
from app.models.location import Location
from app.database import get_db

router = APIRouter(
    prefix="/shredding",
    tags=["Shredding"]
)

# 1. SPUSTENIE DRTENIA
@router.post("/start")
def start_shredding(barcode: str, line_code: str, db: Session = Depends(get_db)):
    """
    Spustí proces drtenia pre paletu. Presunie ju na lokáciu linky (napr. 'LTR1' alebo 'LTR2').
    """
    # 1. Overíme, či zadaná drtiaca linka (lokácia) existuje v systéme
    location = db.query(Location).filter(Location.code == line_code, Location.is_active == True).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drtiacia linka/lokácia '{line_code}' neexistuje alebo nie je aktívna."
        )

    # 2. Vyhľadáme paletu podľa čiarového kódu
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paleta s týmto čiarovým kódom sa nenašla."
        )
    
    # 3. Validácia stavu palety pred drtením
    # Drviť môžeme len odváženú paletu (WEIGHTED), prijatú (RECEIVED) alebo vytriedenú (SORTED)
    if pallet.status not in ["WEIGHTED", "SORTED", "RECEIVED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paletu nie je možné hneď drviť. Aktuálny stav je: {pallet.status}"
        )

    # 4. Aktualizácia údajov palety
    pallet.status = "SHREDDING"
    pallet.location_id = location.id  # Prepojenie na ID nájdenej lokácie
    
    db.commit()
    db.refresh(pallet)
    
    return {"message": f"Drtenie palety {barcode} úspešne spustené na lokácii {line_code}.", "pallet": pallet}


# 2. UKONČENIE DRTENIA
@router.post("/end")
def end_shredding(barcode: str, db: Session = Depends(get_db)):
    """
    Ukončí proces drtenia, zmení stav palety na CRUSHED a uvoľní ju z linky.
    """
    # 1. Vyhľadáme paletu
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paleta s týmto čiarovým kódom sa nenašla."
        )
    
    # 2. Kontrola, či sa paleta naozaj v tejto chvíli drtí
    if pallet.status != "SHREDDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tento materiál sa momentálne nedrtí (nie je v stave SHREDDING)."
        )

    # 3. Finálna aktualizácia stavu po zdrvení
    pallet.status = "CRUSHED"
    # Po zdrvení materiálu môžeme lokáciu vynulovať (materiál už fyzicky ako paleta neexistuje)
    pallet.location_id = None  
    
    db.commit()
    db.refresh(pallet)
    
    return {"message": f"Materiál z palety {barcode} bol úspešne zdrvený.", "pallet": pallet}