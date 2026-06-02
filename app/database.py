from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_locations():
    """
    Automaticky vytvorí základné lokácie pre Halu 9 a Halu 12, ak ešte neexistujú.
    """
    from app.models.location import Location
    
    # Definujeme zoznam tvojich kľúčových lokácií
    initial_locations = [
        {"code": "HALA-12-LTR1", "zone": "LTR1"},
        {"code": "HALA-12-LTR2", "zone": "LTR2"},
        {"code": "HALA-12-SORTING", "zone": "SORTING"},
        {"code": "HALA-9-SORTING", "zone": "SORTING"},
    ]
    
    db = SessionLocal()
    try:
        for loc_data in initial_locations:
            # Skontrolujeme, či lokácia s týmto kódom už náhodou v DB existuje
            exists = db.query(Location).filter(Location.code == loc_data["code"]).first()
            if not exists:
                new_loc = Location(code=loc_data["code"], zone=loc_data["zone"])
                db.add(new_loc)
        db.commit()
    except Exception as e:
        print(f"Chyba pri seedovaní lokácií: {e}")
        db.rollback()
    finally:
        db.close()