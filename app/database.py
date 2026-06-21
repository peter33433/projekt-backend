from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_locations():
    from app.models.location import Location
    from app.models.CustomerOrder import CustomerOrder  # Import objednávky
    db = SessionLocal()
    try:
        # --- 1. AUTOMATICKÝ SEED TESTOVACÍ OBJEDNÁVKY ---
        # Ověříme, zda už v DB nějaká objednávka je, pokud ne, vytvoříme ji
        existing_order = db.query(CustomerOrder).filter(CustomerOrder.order_number == "TEST-ORDER-2026").first()
        if not existing_order:
            test_order = CustomerOrder(order_number="TEST-ORDER-2026")
            db.add(test_order)
            db.commit()
            print("Úspěšně naseedována testovací objednávka 'TEST-ORDER-2026' s ID 1.")

        # --- 2. SEED SKLADOVÝCH LOKACÍ ---
        existing_codes = {row[0] for row in db.query(Location.code).all()}
        locations_to_create = []

        fixed_locations = [
            {"code": "LTR1", "zone": "Hala 12", "status": "empty"},
            {"code": "LTR2", "zone": "Hala 12", "status": "empty"},
            {"code": "SORTING_H12", "zone": "Hala 12", "status": "empty"},
            {"code": "RECEIVING_H9", "zone": "Hala 9", "status": "empty"}
        ]
        
        for loc_data in fixed_locations:
            if loc_data["code"] not in existing_codes:
                locations_to_create.append(Location(**loc_data))

        for regal in range(1, 6):
            for polica in range(1, 4):
                code = f"H9-R{regal}-P{polica}"
                if code not in existing_codes:
                    locations_to_create.append(
                        Location(code=code, zone="Hala 9", status="empty")
                    )

        if locations_to_create:
            db.add_all(locations_to_create)
            db.commit()
            print(f"Úspěšně naseedováno {len(locations_to_create)} nových lokací.")
            
    except Exception as e:
        print(f"Chyba pri seedovaní databázy: {e}")
        db.rollback()
    finally:
        db.close()
