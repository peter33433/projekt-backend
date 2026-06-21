from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.pallet import Pallet
from app.models.location import Location
from app.models.pallet_event import PalletEvent

router = APIRouter(prefix="/sorting", tags=["Sorting"])

# Schémy pre validáciu vstupných dát z frontendu
class PalletSplitItem(BaseModel):
    material_type: str
    gross_weight: float
    packaging_type: str

class PalletSplitRequest(BaseModel):
    items: List[PalletSplitItem]

@router.post("/{barcode}/send")
def send_to_sorting(barcode: str, hall: int, db: Session = Depends(get_db)):
    """
    Presunie paletu z aktuálnej pozície do zóny triedenia v zadanej hale.
    OPRAVA: Kódy lokácií sú upravené tak, aby sedeli so seederom v database.py.
    """
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta podľa čiarového kódu sa nenašla.")

    # Priradenie správneho kódu lokácie podľa seederu z database.py
    if hall == 12:
        target_code = "SORTING_H12"
    elif hall == 9:
        target_code = "RECEIVING_H9"
    else:
        raise HTTPException(status_code=400, detail="Neplatné číslo haly. Podporované sú iba 9 a 12.")

    target_location = db.query(Location).filter(Location.code == target_code).first()
    if not target_location:
        raise HTTPException(
            status_code=404, 
            detail=f"Cieľová lokácia {target_code} neexistuje v DB. Skontrolujte seeder."
        )

    # Uvoľnenie starej pozície, ak nejakú paleta mala
    if pallet.location_id:
        old_location = db.query(Location).filter(Location.id == pallet.location_id).first()
        if old_location:
            old_location.status = "empty"

    # Aktualizácia palety
    pallet.location_id = target_location.id
    pallet.status = "IN_SORTING"

    # Zápis do histórie (Event)
    event = PalletEvent(
        pallet_id=pallet.id,
        event_type="SENT_TO_SORTING",
        description=f"Paleta poslaná na triedenie do zóny {target_code}."
    )
    db.add(event)
    db.commit()

    return {"message": f"Paleta presunutá do triedacej zóny {target_code}.", "status": pallet.status}

@router.post("/{barcode}/split")
def split_pallet_into_sorted(barcode: str, request: PalletSplitRequest, db: Session = Depends(get_db)):
    """
    Zoberie jednu pôvodnú paletu (napr. mix plastov) a rozdelí ju na viacero nových, 
    už vytriedených paliet podľa materiálu. Pôvodná paleta sa označí ako SORTED (spracovaná).
    """
    # 1. Nájdenie a validácia pôvodnej palety
    parent_pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not parent_pallet:
        raise HTTPException(status_code=404, detail="Pôvodná paleta sa nenašla.")
        
    if parent_pallet.status != "IN_SORTING":
        raise HTTPException(
            status_code=400, 
            detail=f"Paleta musí byť v stave IN_SORTING. Aktuálny stav: {parent_pallet.status}"
        )

    if not request.items:
        raise HTTPException(status_code=400, detail="Musíte zadať aspoň jednu vytriedenú položku.")

    # Fixné váhy obalov pre výpočet čistej hmotnosti (net_weight)
    TARE_WEIGHTS = {"paleta": 25.0, "plastovy_box": 35.0, "big_bag": 3.0}

    created_pallets = []

    try:
        # 2. Spracovanie nových vytriedených paliet z cyklu
        for index, item in enumerate(request.items):
            tare = TARE_WEIGHTS.get(item.packaging_type, 25.0)
            net_weight = item.gross_weight - tare

            if net_weight <= 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Položka č. {index + 1}: Čistá hmotnosť nemôže byť záporná alebo nulová. Skontrolujte váhu brutto a typ obalu."
                )

            # Vytvorenie novej palety (odvodenej z pôvodnej objednávky)
            new_pallet = Pallet(
                customer_order_id=parent_pallet.customer_order_id,
                material_type=item.material_type,
                packaging_type=item.packaging_type,
                gross_weight=item.gross_weight,
                net_weight=net_weight,
                status="LABELED",  # Rovno pripravená na tlač štítku/naskladnenie
                location_id=parent_pallet.location_id,  # Zatiaľ zostáva v triedacej zóne
                created_at=datetime.utcnow()
            )
            db.add(new_pallet)
            db.flush()  # Vygeneruje ID novej palety pred commitom

            # Vygenerovanie unikátneho čiarového kódu pre novú vytriedenú paletu
            new_pallet.barcode = f"PAL-SORT-{new_pallet.id:04d}"

            # Logovanie udalosti pre novú paletu
            new_event = PalletEvent(
                pallet_id=new_pallet.id,
                event_type="CREATED_BY_SORTING",
                description=f"Paleta vznikla vytriedením z pôvodnej palety {barcode}. Materiál: {item.material_type}."
            )
            db.add(new_event)
            created_pallets.append({
                "id": new_pallet.id,
                "barcode": new_pallet.barcode,
                "material": new_pallet.material_type,
                "net_weight": new_pallet.net_weight
            })

        # 3. Aktualizácia stavu pôvodnej materskej palety
        parent_pallet.status = "SORTED"
        
        # Uvoľnenie pozície pôvodnej palety (nové palety ju preberajú, alebo idú na sklad)
        parent_pallet.location_id = None

        parent_event = PalletEvent(
            pallet_id=parent_pallet.id,
            event_type="SORTED_AND_SPLIT",
            description=f"Paleta bola úspešne rozptýlená na {len(request.items)} nových produktov a ukončená."
        )
        db.add(parent_event)

        # Potvrdenie celej transakcie naraz (ak čokoľvek zlyhalo predtým, nič sa neuloží)
        db.commit()

        return {
            "message": "Paleta bola úspešne vytriedená a rozdelená.",
            "parent_pallet_status": parent_pallet.status,
            "new_pallets": created_pallets
        }

    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Chyba pri spracovaní triedenia: {e}")
