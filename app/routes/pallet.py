from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import socket
from datetime import datetime

from app.database import get_db
from app.models.pallet import Pallet
from app.models.location import Location
from app.models.pallet_event import PalletEvent
from app.models.CustomerOrder import CustomerOrder

router = APIRouter(prefix="/pallets", tags=["Pallets"])

# Globální definice vah obalů (definováno pouze jednou pro celý soubor)
TARE_WEIGHTS = {
    "paleta": 25.0,
    "plastovy_box": 35.0,
    "big_bag": 3.0
}

@router.get("/order/{order_id}")
def get_order_pallets(order_id: int, db: Session = Depends(get_db)):
    pallets = db.query(Pallet).filter(Pallet.customer_order_id == order_id).all()
    return pallets

@router.post("/print-labels-for-order/{order_id}")
def print_all_labels_for_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Objednávka sa nenašla.")
        
    pallets = db.query(Pallet).filter(Pallet.customer_order_id == order_id).all()
    if not pallets:
        raise HTTPException(status_code=404, detail="Pre túto objednávku nie sú vygenerované žiadne palety.")

    # Vyfiltrujeme pouze ty, které ještě nebyly vytištěny
    pending_pallets = [p for p in pallets if p.status == "PENDING"]
    if not pending_pallets:
        return {"message": "Všetky palety pre túto objednávku už boli vytlačené.", "printed_count": 0}

    printer_ip = "192.168.1.50"
    printer_port = 9100
    printed_barcodes = []

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((printer_ip, printer_port))

        for pallet in pending_pallets:
            if not pallet.barcode:
                pallet.barcode = f"PAL-{order_id}-{pallet.id:04d}"
            
            zpl = f"""
            ^XA
            ^FO50,50^A0N,40,40^FDObjednavka: {order.order_number}^FS
            ^FO50,100^A0N,30,30^FDPaleta ID: {pallet.id}^FS
            ^FO50,150^BY3
            ^BCN,100,Y,N,N
            ^FD{pallet.barcode}^FS
            ^XZ
            """
            s.sendall(zpl.encode('utf-8'))
            pallet.status = "LABELED"
            printed_barcodes.append(pallet.barcode)

        s.close()
        db.commit()
        return {"message": f"Úspešne vytlačených {len(printed_barcodes)} štítkov.", "barcodes": printed_barcodes}

    except Exception as e:
        # V případě chyby sítě se pokusíme uložit vygenerované čárové kódy, ale stav zůstane nebo se rollbackne
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Chyba komunikácie s tlačiarňou ZPL: {e}")

@router.post("/{barcode}/weigh-and-store")
def weigh_and_store_pallet(barcode: str, gross_weight: float, location_code: str, db: Session = Depends(get_db)):
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta podľa čiarového kódu sa nenašla.")

    if pallet.status != "LABELED":
        raise HTTPException(status_code=400, detail=f"Paleta má stav {pallet.status}, očakáva sa LABELED.")

    location = db.query(Location).filter(Location.code == location_code).first()
    if not location:
        raise HTTPException(status_code=404, detail="Zadaná skladová lokácia neexistuje.")

    if location.status != "empty":
        raise HTTPException(status_code=400, detail="Zadaná lokácia nie je voľná.")

    packaging = pallet.packaging_type or "paleta"
    tare = TARE_WEIGHTS.get(packaging, 25.0)
    net_weight = gross_weight - tare

    if net_weight <= 0:
        raise HTTPException(status_code=400, detail="Čistá hmotnosť nemôže byť záporná alebo nulová.")

    pallet.gross_weight = gross_weight
    pallet.net_weight = net_weight
    pallet.location_id = location.id
    pallet.status = "STORED"
    
    location.status = "occupied"

    event = PalletEvent(
        pallet_id=pallet.id,
        event_type="WEIGHED_AND_STORED",
        description=f"Váha brutto: {gross_weight}kg, netto: {net_weight}kg. Uložené na pozíciu {location_code}."
    )
    db.add(event)
    db.commit()

    return {
        "message": "Paleta bola úspešne odvážená a naskladnená.",
        "net_weight": net_weight,
        "location": location_code
    }

@router.post("/receive")
def create_pallet(customer_order_id: int, packaging_type: str, db: Session = Depends(get_db)):
    if packaging_type not in TARE_WEIGHTS:
        raise HTTPException(status_code=400, detail=f"Neplatný typ obalu. Povolené sú: {list(TARE_WEIGHTS.keys())}")

    order = db.query(CustomerOrder).filter(CustomerOrder.id == customer_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Objednávka sa nenašla.")

    new_pallet = Pallet(
        customer_order_id=customer_order_id,
        packaging_type=packaging_type,
        status="RECEIVED",
        created_at=datetime.utcnow()
    )
    db.add(new_pallet)
    db.commit()
    db.refresh(new_pallet)

    event = PalletEvent(
        pallet_id=new_pallet.id,
        event_type="RECEIVED",
        description="Paleta bola prijatá na sklad bez váhy."
    )
    db.add(event)
    db.commit()

    return {"message": "Paleta úspešne zaevidovaná.", "pallet_id": new_pallet.id, "status": new_pallet.status}

@router.post("/{barcode}/receive-and-weigh")
def receive_and_weigh_pallet(barcode: str, gross_weight: float, db: Session = Depends(get_db)):
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta sa nenašla.")

    packaging = pallet.packaging_type or "paleta"
    tare = TARE_WEIGHTS.get(packaging, 25.0)
    net_weight = gross_weight - tare

    pallet.gross_weight = gross_weight
    pallet.net_weight = net_weight
    pallet.status = "WEIGHTED"

    event = PalletEvent(
        pallet_id=pallet.id,
        event_type="WEIGHTED",
        description=f"Paleta bola odvážená. Brutto: {gross_weight}kg, Netto: {net_weight}kg."
    )
    db.add(event)
    db.commit()

    return {"message": "Váha bola úspešne priradená.", "net_weight": net_weight}

@router.post("/{pallet_id}/add-weight")
def add_weight(pallet_id: int, gross_weight: float, db: Session = Depends(get_db)):
    pallet = db.query(Pallet).filter(Pallet.id == pallet_id).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta sa nenašla.")

    packaging = pallet.packaging_type or "paleta"
    tare = TARE_WEIGHTS.get(packaging, 25.0)
    net_weight = gross_weight - tare

    pallet.gross_weight = gross_weight
    pallet.net_weight = net_weight
    pallet.status = "WEIGHTED"

    event = PalletEvent(
        pallet_id=pallet.id,
        event_type="WEIGHTED",
        description=f"Hmotnosť manuálne upravená cez ID. Brutto: {gross_weight}kg, Netto: {net_weight}kg."
    )
    db.add(event)
    db.commit()

    return {"message": "Hmotnosť úspešne priradená k palete.", "pallet_id": pallet_id, "net_weight": net_weight}

@router.post("/{barcode}/transfer-to-hala12")
def transfer_to_hala12(barcode: str, db: Session = Depends(get_db)):
    pallet = db.query(Pallet).filter(Pallet.barcode == barcode).first()
    if not pallet:
        raise HTTPException(status_code=404, detail="Paleta sa nenašla.")

    # OPRAVA: Sparované so správným kódom zo seederu v database.py ("SORTING_H12")
    target_location = db.query(Location).filter(Location.code == "SORTING_H12").first()
    if not target_location:
        raise HTTPException(status_code=404, detail="Cieľová lokácia SORTING_H12 v databáze neexistuje. Spusťte znova seeder.")

    # Uvoľníme starú lokáciu, ak nejakú paleta mala
    if pallet.location_id:
        old_location = db.query(Location).filter(Location.id == pallet.location_id).first()
        if old_location:
            old_location.status = "empty"

    pallet.location_id = target_location.id
    pallet.status = "TRANSFERRED"

    event = PalletEvent(
        pallet_id=pallet.id,
        event_type="TRANSFERRED_TO_HALA12",
        description="Paleta bola presunutá na Halu 12 na triedenie."
    )
    db.add(event)
    db.commit()

    return {"message": f"Paleta {barcode} úspešne presunutá na Halu 12 do zóny triedenia."}
