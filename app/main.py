from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models.pallet import Pallet
from app.models import pallet, pallet_event
from app.routes import pallet

app = FastAPI(title="Skladový Systém API")

# ✨ NASTAVENIE CORS PRE FRONTEND ✨
origins = [
    "http://localhost:3000",    # Častý port pre React / Next.js
    "http://localhost:5173",    # Častý port pre Vite / Vue / Svelte
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Povolí požiadavky z týchto adries
    allow_credentials=True,
    allow_methods=["*"],         # Povolí všetky metódy (GET, POST, PATCH...)
    allow_headers=["*"],         # Povolí všetky hlavičky
)

Base.metadata.create_all(bind=engine)

app.include_router(pallet.router)


@app.get("/")
def root():
    return {"message": "Recycling WMS API running"}