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
        # 1. Načteme všechny existující kódy z DB jedním dotazem pro rychlé ověření v paměti
        existing_codes = {row[0] for row in db.query(Location.code).all()}
        
        locations_to_create = []

        # 2. Definice fixních bodů
        fixed_locations = [
            {"code": "LTR1", "zone": "Hala 12", "status": "empty"},
            {"code": "LTR2", "zone": "Hala 12", "status": "empty"},
            {"code": "SORTING_H12", "zone": "Hala 12", "status": "empty"},
            {"code": "RECEIVING_H9", "zone": "Hala 9", "status": "empty"}
        ]
        
        for loc_data in fixed_locations:
            if loc_data["code"] not in existing_codes:
                locations_to_create.append(Location(**loc_data))

        # 3. Vygenerování regálů pro Halu 9 (5 regálů x 3 police)
        for regal in range(1, 6):
            for polica in range(1, 4):
                code = f"H9-R{regal}-P{polica}"
                if code not in existing_codes:
                    locations_to_create.append(
                        Location(code=code, zone="Hala 9", status="empty")
                    )

        # 4. Hromadné uložení pouze pokud existují nové lokace
        if locations_to_create:
            db.add_all(locations_to_create)
            db.commit()
            print(f"Úspěšně naseedováno {len(locations_to_create)} nových lokací.")
            
    except Exception as e:
        print(f"Chyba pri seedovaní lokácií: {e}")
        db.rollback()
    finally:
        db.close()
