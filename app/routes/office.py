# app/routes/office.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.CustomerOrder import CustomerOrder
from pydantic import BaseModel

router = APIRouter(prefix="/office", tags=["Office / Kancelária"])

class OrderCreateInput(BaseModel):
    order_number: str   # napr. Xerox 1234

@router.post("/orders/create")
def create_customer_order(data: OrderCreateInput, db: Session = Depends(get_db)):
    existing_order = db.query(CustomerOrder).filter(CustomerOrder.order_number == data.order_number).first()
    if existing_order:
        raise HTTPException(status_code=400, detail="Zákazka s týmto číslom už existuje")

    new_order = CustomerOrder(order_number=data.order_number)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return {"status": "success", "message": f"Zákazka {new_order.order_number} úspešne vytvorená v kancelárii."}