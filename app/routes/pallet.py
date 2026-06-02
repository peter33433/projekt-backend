from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

# Importujeme LEN get_db zo súboru database.py
from app.database import get_db  

from app.models.pallet import Pallet
from app.models.pallet_split import PalletSplit
from app.models.location import Location
from app.models.pallet_event import PalletEvent

from app.schemas.pallet import PalletCreate, DashboardSummary
from app.services.barcode import generate_pallet_code
from app.services.zpl import generate_zpl
from app.services.printer import print_zpl

router = APIRouter()


@router.get("/pallets")
def get_pallets(db: Session = Depends(get_db)):
    return db.query(Pallet).all()

@router.get("/pallets/{barcode}")
def get_pallet(barcode: str, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    if not pallet:
        return {"error": "Pallet not found"}

    return pallet


@router.post("/pallets")
def create_pallet(payload: PalletCreate, db: Session = Depends(get_db)):

    pallet = Pallet(
        barcode="TEMP",
        customer_name=payload.customer_name,
        material_type=payload.material_type,
        package_type=payload.package_type,
        status="RECEIVED"
    )

    db.add(pallet)
    db.flush()

    pallet.barcode = generate_pallet_code(pallet.id)

    db.commit()
    db.refresh(pallet)

    zpl = generate_zpl(pallet)

    return {
        "id": pallet.id,
        "barcode": pallet.barcode,
        "zpl": zpl
    }

@router.post("/weigh")
def weigh_pallet():
    return {"message": "Pallet weighed"}


@router.patch("/pallets/{barcode}/status")
def update_status(barcode: str, status: str, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    if not pallet:
        return {"error": "Pallet not found"}

    pallet.status = status
    db.commit()
    db.refresh(pallet)

    return {
        "barcode": pallet.barcode,
        "status": pallet.status
    }

@router.post("/pallets/{barcode}/print")
def print_pallet(barcode: str, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    if not pallet:
        return {"error": "Pallet not found"}

    zpl = generate_zpl(pallet)

    success = print_zpl(zpl, printer_ip="SIMULATOR")

    return {
        "printed": success,
        "barcode": barcode
    }

@router.get("/scan/{barcode}")
def scan_pallet(barcode: str, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    if not pallet:
        return {"error": "Not found"}

    return pallet

@router.patch("/pallets/{barcode}/weight")
def add_weight(barcode: str, weight: float, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    pallet.weight = weight
    pallet.weight_added_at = datetime.utcnow()
    pallet.status = "WEIGHTED"

    db.commit()

    return pallet

@router.patch("/pallets/{barcode}/move")
def move_pallet(barcode: str, location: str, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    pallet.location = location

    db.commit()

    return pallet

@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    results = (
        db.query(Location.code, func.count(Pallet.id).label("pallet_count"))
        .join(Pallet, Location.id == Pallet.location_id)
        .group_by(Location.code)
        .all()
    )
    
    # Preformátovanie výsledkov do pekného slovníka pre frontend
    return [{"location": row.code, "count": row.pallet_count} for row in results]


@router.get("/{label}/history")
def pallet_history(label: str, db: Session = Depends(get_db)):

    splits = db.query(PalletSplit).filter(
        PalletSplit.parent_label == label
    ).all()

    children = db.query(Pallet).filter(
        Pallet.parent_id == db.query(Pallet.id).filter(Pallet.barcode == label).scalar_subquery()
    ).all()

    return {
        "parent": label,
        "split_records": splits,
        "children": children
    }

@router.post("/{barcode}/move/{location_id}")
def move_pallet(barcode: str, location_id: int, db: Session = Depends(get_db)):
    # 1. Vyhľadanie palety podľa čiarového kódu
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail=f"Paleta s kódom {barcode} nebola nájdená.")

    # 2. Vyhľadanie lokácie podľa číselného ID
    location = db.query(Location).filter(Location.id == location_id).first()
    
    # 🛡️ OCHRANA: Ak lokácia v DB chýba, vrátime 404 namiesto pádu servera!
    if not location:
        raise HTTPException(
            status_code=404, 
            detail=f"Lokácia s ID {location_id} v databáze neexistuje. Najskôr spustite /seed-locations."
        )

    # 3. Priradenie novej lokácie (keďže už naisto existuje)
    pallet.location_id = location.id
    
    # 4. Zápis do histórie
    new_event = PalletEvent(
        pallet_id=pallet.id,
        event_type="MOVED",
        description=f"Presun na pozíciu {location.code}" 
    )
    db.add(new_event)
    db.commit()

    return {"message": f"Paleta úspešne presunutá na lokáciu {location.code}"}

@router.post("/pallets/{pallet_id}/event")
def add_event(pallet_id: int, payload: dict, db: Session = Depends(get_db)):
    event = PalletEvent(
        pallet_id=pallet_id,
        event_type=payload["event_type"],
        from_location_id=payload.get("from_location_id"),
        to_location_id=payload.get("to_location_id"),
        metadata=str(payload.get("metadata"))
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event

@router.get("/locations")
def get_all_locations(db: Session = Depends(get_db)):
    # Vytiahne úplne všetky naseedované lokácie z databázy
    locations = db.query(Location).all()
    return locations

@router.post("/pallets/{barcode}/transfer-to-hala12")
def transfer_to_hala12(barcode: str, db: Session = Depends(get_db)):
    """
    Presunie vytriedenú paletu z Haly 9 na Halu 12 pre následné drtenie.
    """
    # 1. Vyhľadanie palety podľa čiarového kódu
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta sa nenašla.")
        
    # 2. Overenie, či je paleta pripravená (vytriedená) na presun
    if pallet.status != "SORTED":
        raise HTTPException(
            status_code=400, 
            detail=f"Na Halu 12 je možné presunúť len vytriedený materiál. Aktuálny stav: {pallet.status}"
        )

    # 3. Vyhľadanie cieľovej lokácie (sorting zóna na Hale 12)
    target_location = db.query(Location).filter(Location.code == "HALA-12-SORTING").first()
    if not target_location:
        raise HTTPException(status_code=404, detail="Cieľová lokácia HALA-12-SORTING v DB neexistuje.")

    # 4. Aktualizácia údajov
    pallet.location_id = target_location.id
    pallet.status = "TRANSFERRED"  # Stav, že paleta úspešne dorazila na Halu 12

    # 5. Zápis presunu do histórie pohybov (PalletEvent)
    new_event = PalletEvent(
        pallet_id=pallet.id,
        event_type="MOVED",
        description=f"Medzihalový presun z Haly 9 na Halu 12 (Pozícia: {target_location.code})"
    )
    db.add(new_event)
    
    db.commit()
    db.refresh(pallet)
    return {"message": f"Paleta {barcode} bola úspešne presunutá na Halu 12.", "pallet": pallet}    