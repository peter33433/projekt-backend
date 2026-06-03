# app/database.py
from sqlalchemy import create_engine  # <-- OPRAVENÉ (Vymazané create_url)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Tvoja pôvodná konfigurácia SQLite databázy
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Náš nový seeder pre Halu 9 a Halu 12
def seed_locations():
    from app.models.location import Location  
    db = SessionLocal()                       
    try:
        # 1. Fixné body na Hale 12 a príjem na Hale 9
        fixed_locations = [
            {"code": "LTR1", "zone": "Hala 12", "status": "empty"},
            {"code": "LTR2", "zone": "Hala 12", "status": "empty"},
            {"code": "SORTING_H12", "zone": "Hala 12", "status": "empty"},
            {"code": "RECEIVING_H9", "zone": "Hala 9", "status": "empty"}
        ]
        
        for loc_data in fixed_locations:
            exists = db.query(Location).filter(Location.code == loc_data["code"]).first()
            if not exists:
                db.add(Location(**loc_data))
                
        # 2. Vygenerovanie regálov pre Halu 9 (5 regálov x 3 police)
        for regal in range(1, 6):
            for polica in range(1, 4):
                code = f"H9-R{regal}-P{polica}"
                exists = db.query(Location).filter(Location.code == code).first()
                if not exists:
                    db.add(Location(code=code, zone="Hala 9", status="empty"))
                    
        db.commit()
    except Exception as e:
        print(f"Chyba pri seedovaní lokácií: {e}")
        db.rollback()
    finally:
        db.close()
