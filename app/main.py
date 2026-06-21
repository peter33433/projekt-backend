from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import databázy, seederu a tvojich modelov
from app.database import engine, Base, seed_locations
from app import models
from app.routes import pallet, shredding, sorting, customers

# Správa životního cyklu aplikace (výměna za staré @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicializácia databázy a seeding při startu
    Base.metadata.create_all(bind=engine)
    
    # Pokud seed_locations potřebuje session, ujistěte se, že ji uvnitř správně zavíráte
    seed_locations() 
    
    yield # Zde aplikace běží a přijímá požadavky
    
    # Zde můžete uvést kód, který se spustí při vypínání aplikace (např. odpojení DB)

# Inicializácia aplikácie s definovaným lifespanem
app = FastAPI(title="Skladový Systém API", lifespan=lifespan)

# Nastavenie CORS pre frontend
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrácia všetkých routerov
app.include_router(shredding.router)
app.include_router(pallet.router)
app.include_router(sorting.router)
app.include_router(customers.router)

# Root endpoint
@app.get("/")
def root():
    return {"message": "Recycling WMS API running"}