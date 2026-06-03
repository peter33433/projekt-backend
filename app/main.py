from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import databázy, seederu a tvojich modelov
from app.database import engine, Base, seed_locations
from app import models 
from app.routes import pallet, shredding, sorting, customers

# 1. Inicializácia aplikácie
app = FastAPI(title="Skladový Systém API")

# 2. Nastavenie CORS pre frontend
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

# 3. Inicializácia databázy a seeding (modely sú už načítané vďaka importu hore)
Base.metadata.create_all(bind=engine)
seed_locations()

# 4. Registrácia všetkých routerov
app.include_router(shredding.router)
app.include_router(pallet.router)
app.include_router(sorting.router)
app.include_router(customers.router)

# 5. Root endpoint
@app.get("/")
def root():
    return {"message": "Recycling WMS API running"}