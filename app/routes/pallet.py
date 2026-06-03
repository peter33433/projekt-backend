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
from app.models.order import CustomerOrder

from app.schemas.pallet import PalletCreate, DashboardSummary
from app.services.barcode import generate_pallet_code
from app.services.zpl import generate_zpl
from app.services.printer import print_zpl

import socket

router = APIRouter()

@router.get("/orders/{order_number}/pallets")
def get_order_pallets(order_number: str, db: Session = Depends(get_db)):
    order = db.query(CustomerOrder).filter(CustomerOrder.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Zakázka nenájdená")
    return order.pallets  # Logista uvidí zoznam a vie, ktoré sú ešte v stave "PENDING"

# Defonícia fixných váh obalov
TARE_WEIGHTS = {
    "paleta": 25.0,
    "plastovy_box": 35.0,
    "big_bag": 3.0
}

@router.post("/orders/{order_number}/print-all-labels")
def print_all_labels_for_order(order_number: str, ip_tlaciarne: str = "192.168.1.150", db: Session = Depends(get_db)):
    # 1. Nájdi zakázku pod číslom napr. Xerox 1234
    order = db.query(CustomerOrder).filter(CustomerOrder.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Zakázka nenájdená")
        
    # 2. Vyber iba palety, ktoré ešte nemajú vytlačený štítok
    pending_pallets = db.query(Pallet).filter(Pallet.order_id == order.id, Pallet.status == "PENDING").all()
    if not pending_pallets:
        raise HTTPException(status_code=400, detail="Žiadne palety nečakajú na tlač štítkov")

    zpl_hromadny_kod = ""
    
    # 3. Prejdi každú paletu, vygeneruj kód a priprav tlač
    for index, pallet in enumerate(pending_pallets, start=1):
        # Generujeme unikátny čiarový kód, napr. PAL-123-20260603
        cas_vytvorenia = datetime.utcnow().strftime('%Y%m%d%H%M')
        generovany_barcode = f"PAL-{pallet.id}-{cas_vytvorenia}"
        
        pallet.barcode = generovany_barcode
        pallet.status = "LABELED"  # Paleta má štítok, čaká na zváženie
        
        # Príprava ZPL kódu pre tlačiareň (Váha a obal sú zatiaľ prázdne)
        zpl_hromadny_kod += f"""
        ^XA
        ^FO50,40^A0N,45,45^FDZakazka: {order.order_number}^FS
        ^FO50,95^A0N,35,35^FDCislo palety: {index}/{len(pending_pallets)}^FS
        ^FO50,140^A0N,35,35^FDMaterial: {pallet.material_type}^FS
        ^FO50,185^A0N,30,30^FDCaká na vazenie...^FS
        ^FO50,230^BCN,90,Y,N,N^FD{generovany_barcode}^FS
        ^XZ
        """
    
    # 4. Odoslanie hromadnej tlače na sieťovú tlačiareň na hale
    try:
        mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mysocket.settimeout(3.0)
        mysocket.connect((ip_tlaciarne, 9100))
        mysocket.send(bytes(zpl_hromadny_kod, "utf-8"))
        mysocket.close()
    except Exception as e:
        # Ak tlačiareň zlyhá, dáta v DB radšej potvrdíme, ale upozorníme používateľa
        db.commit()
        raise HTTPException(status_code=503, detail=f"Palety pripravené, ale tlačiareň neodpovedá: {e}")

    db.commit()
    return {"status": "success", "message": f"Vytlačených {len(pending_pallets)} štítkov. Palety sú pripravené na olepenie."}

@router.patch("/pallets/{pallet_id}/receive")
def receive_and_weigh_pallet(
    pallet_id: int, 
    gross_weight: float, 
    package_type: str, 
    location_id: int, 
    db: Session = Depends(get_db)
):
    pallet = db.query(Pallet).filter(Pallet.id == pallet_id).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta nenájdená")
        
    if package_type not in TARE_WEIGHTS:
        raise HTTPException(status_code=400, detail="Neplatný typ obalu")

    # 1. Výpočet čistej váhy
    tare = TARE_WEIGHTS[package_type]
    net = gross_weight - tare
    
    # 2. Aktualizácia dát palety
    pallet.barcode = f"PAL-{pallet.id}-{datetime.utcnow().strftime('%m%d%H%M')}" # Generovanie unikátneho kódu pre štítok
    pallet.gross_weight = gross_weight
    pallet.tare_weight = tare
    pallet.net_weight = max(0.0, net) # Ochrana pred zápornou váhou
    pallet.package_type = package_type
    pallet.location_id = location_id
    pallet.status = "WEIGHTED" # Paleta je pripravená na hale
    
    db.commit()
    db.refresh(pallet)
    
    # Backend vráti dáta, frontend vygeneruje z tohto JSONu čiarový kód na tlačiareň lejblov
    return {"message": "Paleta úspešne odvážená a naskladnená", "pallet": pallet}


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

# Fixné váhy obalov, ktoré odpočítavame
TARE_WEIGHTS = {
    "paleta": 25.0,
    "plastovy_box": 35.0,
    "big_bag": 3.0
}

@router.patch("/weigh-and-store")
def weigh_and_store_pallet(
    barcode: str, 
    gross_weight: float, 
    package_type: str, 
    location_id: int, 
    db: Session = Depends(get_db)
):
    # 1. Backend vyhľadá paletu podľa naskenovaného čiarového kódu
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Naskenovaná paleta nebola nájdená v systéme")
        
    if pallet.status != "LABELED":
        raise HTTPException(status_code=400, detail=f"Táto paleta už bola zvážená alebo spracovaná (Status: {pallet.status})")

    if package_type not in TARE_WEIGHTS:
        raise HTTPException(status_code=400, detail="Zvolený neplatný typ obalu")

    # 2. Automatický výpočet čistej váhy
    tare = TARE_WEIGHTS[package_type]
    net = gross_weight - tare

    # 3. Zápis finálnych údajov z váhy
    pallet.gross_weight = gross_weight
    pallet.tare_weight = tare
    pallet.net_weight = max(0.0, net)  # Zabráni zápornej váhe, ak by logista zadal zlú váhu
    pallet.package_type = package_type
    pallet.location_id = location_id
    pallet.status = "STORED"           # Paleta je úspešne odvážená a umiestnená na pozícii
    
    db.commit()
    db.refresh(pallet)
    
    return {
        "status": "success", 
        "message": "Paleta bola úspešne zaevidovaná a odvážená", 
        "cista_vaha": pallet.net_weight
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
    if not pallet:
        raise HTTPException(status_code=404, detail="Pallet not found")
    # OPRAVENÉ: Používame net_weight z modelu a odstránený neexistujúci weight_added_at
    pallet.net_weight = weight 
    pallet.status = "WEIGHTED"
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


# OPRAVENÉ: Čisté hľadanie histórie splitov cez parent_id (bez PalletSplit)
@router.get("/{label}/history")
def pallet_history(label: str, db: Session = Depends(get_db)):
    parent_pallet = db.query(Pallet).filter(Pallet.barcode == label).first()
    if not parent_pallet:
        raise HTTPException(status_code=404, detail="Parent pallet not found")
    return {"parent": label, "children": parent_pallet.children}

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