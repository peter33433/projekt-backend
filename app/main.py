from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, seed_locations
from app import models
# Import nového auth modulu
from app.routes import pallet, shredding, sorting, customers, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_locations()
    yield

app = FastAPI(title="Skladový Systém API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrace routerů včetně auth
app.include_router(shredding.router)
app.include_router(pallet.router)
app.include_router(sorting.router)
app.include_router(customers.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Recycling WMS API running"}
