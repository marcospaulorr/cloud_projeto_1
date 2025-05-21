import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import requests
import socket
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://projeto:projeto@db:5432/projeto"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Configuração do JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "segredo_super_secreto_para_desenvolvimento"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configuração de criptografia para senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelos de dados
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Criação das tabelas
Base.metadata.create_all(bind=engine)

# Modelos Pydantic para validação e serialização
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    senha: str

class UserLogin(BaseModel):
    email: EmailStr
    senha: str

class Token(BaseModel):
    jwt: str

class HealthCheck(BaseModel):
    statusCode: int = 200
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    hostname: str = Field(default_factory=lambda: socket.gethostname())

# Funções auxiliares
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
        
    return user

# Função para obter dados da Bolsa (web scraping)
def get_bovespa_data():
    # Simulação de dados da Bovespa
    # Em produção, isso seria substituído por web scraping real ou API
    data = [
        {"Date": "2024-09-05", "Open": 136112.0, "High": 136656.0, "Low": 135959.0, "Close": 136502.0, "Volume": 7528700},
        {"Date": "2024-09-06", "Open": 136508.0, "High": 136653.0, "Low": 134476.0, "Close": 134572.0, "Volume": 7563300},
        {"Date": "2024-09-09", "Open": 134574.0, "High": 135250.0, "Low": 134399.0, "Close": 134737.0, "Volume": 6587600},
        {"Date": "2024-09-10", "Open": 134738.0, "High": 134738.0, "Low": 133754.0, "Close": 134320.0, "Volume": 8253500},
        {"Date": "2024-09-11", "Open": 134319.0, "High": 135087.0, "Low": 133757.0, "Close": 134677.0, "Volume": 7947300},
        {"Date": "2024-09-12", "Open": 134677.0, "High": 134777.0, "Low": 133591.0, "Close": 134029.0, "Volume": 7004900},
        {"Date": "2024-09-13", "Open": 134031.0, "High": 135879.0, "Low": 134031.0, "Close": 134882.0, "Volume": 8866000},
        {"Date": "2024-09-16", "Open": 134885.0, "High": 135715.0, "Low": 134870.0, "Close": 135118.0, "Volume": 6707000}
    ]
    return data

# Inicialização da aplicação FastAPI
app = FastAPI(title="API RESTful Projeto 2025.1")

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints
@app.post("/registrar", response_model=Token)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar se o email já existe
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=409, detail="Email já registrado")
    
    # Criar novo usuário
    hashed_password = get_password_hash(user.senha)
    db_user = User(name=user.name, email=user.email, hashed_password=hashed_password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Gerar token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"jwt": access_token}

@app.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    # Autenticar usuário
    user = authenticate_user(db, user_data.email, user_data.senha)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Gerar token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"jwt": access_token}

@app.get("/consultar")
def get_data(current_user: User = Depends(get_current_user)):
    # Obter dados da Bovespa
    bovespa_data = get_bovespa_data()
    return bovespa_data

@app.get("/health-check", response_model=HealthCheck)
def health_check():
    return HealthCheck()

# Execução da aplicação
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)