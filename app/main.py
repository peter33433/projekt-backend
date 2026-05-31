from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models.pallet import Pallet
from app.models import pallet, pallet_event
from app.routes import pallet

app = FastAPI()


Base.metadata.create_all(bind=engine)

app.include_router(pallet.router)


@app.get("/")
def root():
    return {"message": "Recycling WMS API running"}