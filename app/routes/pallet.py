from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.pallet import Pallet
from app.models.pallet_split import PalletSplit
from app.schemas.pallet import PalletCreate
from app.services.barcode import generate_pallet_code
from app.services.zpl import generate_zpl
from app.services.printer import print_zpl
from sqlalchemy import func
from datetime import datetime
from app.models.location import Location
from app.models.pallet_event import PalletEvent

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    pallet.location = "WAREHOUSE"

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

@router.patch("/pallets/{barcode}/send-to-sorting")
def send_to_sorting(barcode: str, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    pallet.location = "SORTING"

    db.commit()

    return pallet

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends


@router.post("/pallets/{barcode}/split")
def split_pallet(barcode: str, parts: list[dict], db: Session = Depends(get_db)):

    parent = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not parent:
        return {"error": "Parent pallet not found"}

    created = []

    for part in parts:

        # 1️⃣ create child
        child = Pallet(
            barcode="TEMP",  # dočasne kvôli NOT NULL
            customer_name=parent.customer_name,
            material_type=part["material_type"],
            package_type=parent.package_type,
            status="RECEIVED",
            location="WAREHOUSE",
            parent_id=parent.id
        )

        db.add(child)
        db.flush()  # dostane ID

        # 2️⃣ generate final barcode
        child.barcode = generate_pallet_code(child.id)

        # 3️⃣ SPLIT HISTORY (TOTO TI CHÝBALO)
        split_record = PalletSplit(
            parent_label=parent.barcode,
            child_label=child.barcode
        )
        db.add(split_record)

        created.append(child)

    # 4️⃣ update parent
    parent.is_sorted = 1
    parent.location = "SORTED"

    db.commit()

    return {
        "parent": parent.barcode,
        "children": [c.barcode for c in created]
    }

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

@router.post("/seed-locations")
def seed_locations(db: Session = Depends(get_db)):
    locations_to_seed = [
        {"code": "A1-01-01", "description": "Sektor A1"},
        {"code": "A1-01-02", "description": "Sektor A2"},
        # ... vaše ďalšie lokácie
    ]

    for loc_data in locations_to_seed:
        # Skontrolujeme, či lokácia s týmto kódom už existuje
        existing_loc = db.query(Location).filter(Location.code == loc_data["code"]).first()
        
        if not existing_loc:
            # Vložíme len vtedy, ak kód v DB chýba
            new_loc = Location(code=loc_data["code"], description=loc_data.get("description"))
            db.add(new_loc)
            
    db.commit()
    return {"message": "Seedovanie lokácií prebehlo úspešne."}

@router.post("/{barcode}/move/{location_code}")
def move_pallet(barcode: str, location_code: str, db: Session = Depends(get_db)):

    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()

    location = db.query(Location).filter(
        Location.code == location_code
    ).first()

    print("PALLET:")
    print(pallet)

    print("LOCATION:")
    print(location)

    print("LOCATION ID:")
    print(location.id)

    pallet.location = location


    print("PALLET LOCATION ID:")
    print(pallet.location_id)

    db.commit()

    return {"ok": True}

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