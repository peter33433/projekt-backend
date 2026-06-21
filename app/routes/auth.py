from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.user import User  # Předpokládá existenci modelu User v app/models/user.py

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Konfigurace zabezpečení (V produkci přesuňte do .env souboru)
SECRET_KEY = "SUPER_TAJNY_KLIC_PRO_RECYCLING_WMS_APLIKACI"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # Token platí 8 hodin (jedna směna skladníka)

# Kontext pro hashování hesel
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Pydantic schémata pro validaci vstupů
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "skladnik"  # Výchozí role: admin, manazer, skladnik

class Token(BaseModel):
    access_token: str
    token_type: str

# Pomocné funkce pro hesla a JWT
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 1. Endpoint pro registraci nového uživatele (Skladníka / Manažera)
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    # Kontrola, zda uživatel se stejným jménem nebo emailem už neexistuje
    existing_user = db.query(User).filter((User.username == user_data.username) | (User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Užívateľ s týmto menom alebo e-mailom už existuje."
        )

    # Validace povolených rolí
    if user_data.role not in ["admin", "manazer", "skladnik"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neplatná rola. Povolené sú: admin, manazer, skladnik"
        )

    # Vytvoření nového uživatele s hashem hesla
    hashed_pwd = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pwd,
        role=user_data.role,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Užívateľ úspešne zaregistrovaný", "username": new_user.username, "role": new_user.role}

# 2. Endpoint pro přihlášení (Generuje JWT Token)
@router.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Vyhledání uživatele podle přihlašovacího jména
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nesprávne meno alebo heslo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tento používateľský účet je deaktivovaný.")

    # Generování tokenu – do payloadu ukládáme username a roli pro frontend
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# 3. Pomocná funkce pro ochranu ostatních endpointů (Získání aktuálního přihlášeného uživatele)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nepodarilo sa overiť prihlasovacie údaje.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
