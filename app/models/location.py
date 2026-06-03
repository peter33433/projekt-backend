# app/database.py
from sqlalchemy.orm import Session
from app.models.location import Location

def seed_locations(db: Session):
    # 1. Definuje fixné body pre Halu 12 a základnú zónu Haly 9
    fixed_locations = [
        {"code": "LTR1", "zone": "Hala 12", "status": "empty"},          # Drvička 1
        {"code": "LTR2", "zone": "Hala 12", "status": "empty"},          # Drvička 2
        {"code": "SORTING_H12", "zone": "Hala 12", "status": "empty"},   # Mix zóna (HDPE, PS...)
        {"code": "RECEIVING_H9", "zone": "Hala 9", "status": "empty"}    # Príjem na Hale 9
    ]
    
    for loc_data in fixed_locations:
        exists = db.query(Location).filter(Location.code == loc_data["code"]).first()
        if not exists:
            db.add(Location(**loc_data))
            
    # 2. Vygeneruje regály pre Halu 9 (napr. 5 regálov, 3 police)
    for regal in range(1, 6):
        for polica in range(1, 4):
            code = f"H9-R{regal}-P{polica}" # napr. H9-R1-P3
            exists = db.query(Location).filter(Location.code == code).first()
            if not exists:
                db.add(Location(code=code, zone="Hala 9", status="empty"))
                
    db.commit()