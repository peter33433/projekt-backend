from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.models.pallet import Pallet  
from app.models.location import Location
from app.database import get_db

router = APIRouter(
    prefix="/sorting",
    tags=["Sorting"]
)

# Schéma pre prichádzajúce dáta pri rozdelení palety
class NewPalletSchema(BaseModel):
    barcode: str
    material_type: str
    package_type: str
    net_weight: float

class SplitPalletRequest(BaseModel):
    parent_barcode: str
    new_pallets: List[NewPalletSchema]


# 1. ODOSLANIE PALETY NA TRIEDENIE (SORTING)
@router.post("/send")
def send_to_sorting(barcode: str, hall: str, db: Session = Depends(get_db)):
    """
    Presunie namixovanú paletu do triediacej zóny (buď na Hale 9 alebo Hale 12).
    """
    if hall not in ["9", "12"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neplatná hala. Zadaj '9' alebo '12'."
        )

    # Vyhľadanie príslušnej lokácie podla naseedovaného kódu
    target_code = f"HALA-{hall}-SORTING"
    location = db.query(Location).filter(Location.code == target_code).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triediaca lokácia {target_code} sa v systéme nenašla."
        )

    # Vyhľadanie palety
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paleta sa nenašla."
        )

    # Aktualizácia stavu a lokácie
    pallet.status = "TO_SORT"
    pallet.location_id = location.id
    
    db.commit()
    db.refresh(pallet)
    return {"message": f"Paleta {barcode} bola presunutá na triedenie do Haly {hall}.", "pallet": pallet}


# 2. ROZDELENIE A VYTRIEDENIE PALETY
@router.post("/split")
def split_pallet(request: SplitPalletRequest, db: Session = Depends(get_db)):
    """
    Ukončí triedenie pôvodnej namixovanej palety a vytvorí z nej nové, vybalené palety.
    """
    # Vyhľadanie pôvodnej (rodičovskej) palety
    parent_pallet = db.query(Pallet).filter(Pallet.barcode == request.parent_barcode).first()
    if not parent_pallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pôvodná paleta na triedenie sa nenašla."
        )

    if parent_pallet.is_sorted == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Táto paleta už bola v minulosti kompletne roztriedená."
        )

    # Uzatvorenie pôvodnej palety
    parent_pallet.is_sorted = 1
    parent_pallet.status = "SORTED_DONE"

    created_pallets = []
    
    # Generovanie nových čistých paliet z namixovanej krabice/palety
    for p_data in request.new_pallets:
        # Skontrolovať duplicitu kódu pre istotu
        duplicate = db.query(Pallet).filter(Pallet.barcode == p_data.barcode).first()
        if duplicate:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Čiarový kód {p_data.barcode} už v systéme existuje. Zvoľ unikátny kód."
            )

        new_pallet = Pallet(
            barcode=p_data.barcode,
            customer_name=parent_pallet.customer_name,  # Dedí zákazníka
            material_type=p_data.material_type,        # Nový konkrétny materiál po vytriedení
            package_type=p_data.package_type,          # Nový obal (už vybalený z krabičiek)
            net_weight=p_data.net_weight,
            status="SORTED",                            # Nový stav (pripravená na drvenie / výdaj)
            parent_id=parent_pallet.id,                 # Prepojenie na pôvodnú paletu
            location_id=parent_pallet.location_id       # Zostáva zatiaľ na rovnakej hale v sorting zóne
        )
        db.add(new_pallet)
        created_pallets.append(new_pallet)

    db.commit()

    return {
        "message": f"Paleta {request.parent_barcode} úspešne rozdelená na {len(created_pallets)} nových produktov.",
        "parent_pallet": parent_pallet,
        "new_pallets": created_pallets
    }