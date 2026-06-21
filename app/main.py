from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, seed_locations
from app import models
from app.routes import pallet, shredding, sorting, customers, auth, shipping, recycled

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_locations()
    yield

# Inicializácia aplikácie
app = FastAPI(title="Skladový Systém API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrácia routerov
app.include_router(shredding.router)
app.include_router(pallet.router)
app.include_router(sorting.router)
app.include_router(customers.router)
app.include_router(auth.router)
app.include_router(shipping.router)
app.include_router(recycled.router)

# 🔐 Správna úprava OpenAPI schémy pre zobrazenie tlačidla Authorize
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title="Skladový Systém WMS",
        version="1.0.0",
        description="API pre správu recyklačného skladu",
        routes=app.routes,
    )
    
    # Bezpečné pridanie bezpečnostného protokolu
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "auth/login",
                    "scopes": {}
                }
            }
        }
    }
    
    # Aplikovanie zámku globálne na dokumentáciu
    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
def root():
    return {"message": "Recycling WMS API running"}
