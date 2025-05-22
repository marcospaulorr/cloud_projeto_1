import os
import time
import socket
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Carrega variáveis de ambiente de .env
load_dotenv()

# 1) CONFIGURAÇÃO DO BANCO
# Configuração adicional para produção
DB_USER = os.getenv("DB_USER", "admin")  # Muda para admin (padrão Lightsail)
DB_PASSWORD = os.getenv("DB_PASSWORD", "SuaSenhaSegura123!")  
DB_HOST = os.getenv("DB_HOST", "seu-db-endpoint.lightsail.aws")  # Será preenchido depois
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "fastapi_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Espera o banco ficar pronto
for _ in range(10):
    try:
        engine = create_engine(DATABASE_URL)
        engine.connect().close()
        print("✅ Conectado ao banco com sucesso.")
        break
    except OperationalError:
        print("⏳ Aguardando banco...")
        time.sleep(2)
else:
    raise RuntimeError("❌ Não foi possível conectar ao banco de dados.")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# 2) MODELO SQLALCHEMY
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# 3) CONFIGURAÇÃO JWT / CRIPTOGRAFIA
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "troque_esta_string_para_producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🔐 CONFIGURAÇÃO CORRETA PARA SWAGGER AUTHORIZE
bearer_scheme = HTTPBearer()

# 4) SCHEMAS Pydantic
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

# 5) DEPENDÊNCIAS E FUNÇÕES AUXILIARES
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_access_token(sub: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, senha: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(senha, user.hashed_password):
        return None
    return user

# 🔐 FUNÇÃO DE AUTENTICAÇÃO QUE FUNCIONA COM AUTHORIZE
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise JWTError()
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# 6) INICIALIZAÇÃO DO FastAPI
app = FastAPI(
    title="API RESTful Projeto 2025.1",
    version="1.0.0",
    description="Cadastro, login e endpoint protegido com JWT"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 7) ENDPOINTS PÚBLICOS
@app.post("/registrar", response_model=Token, summary="Registrar usuário")
def registrar(user: UserCreate, db: Session = Depends(get_db)):
    """Registra um novo usuário e retorna JWT token"""
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=409, detail="Email já registrado")
    
    novo = User(
        name=user.name,
        email=user.email,
        hashed_password=hash_password(user.senha)
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    
    token = create_access_token(novo.email)
    return {"jwt": token}

@app.post("/login", response_model=Token, summary="Login de usuário")
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Autentica usuário e retorna JWT token"""
    user = authenticate_user(db, data.email, data.senha)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"jwt": create_access_token(user.email)}

# 8) ENDPOINT PROTEGIDO - CONFIGURAÇÃO CORRETA
@app.get(
    "/consultar",
    summary="Consultar dados da Bovespa",
    description="🔒 **Endpoint Protegido** - Requer autenticação JWT via botão Authorize",
    response_model=List[dict]
)
def consultar(current_user: User = Depends(get_current_user)):
    """
    🔒 **Endpoint Protegido** - Requer autenticação JWT
    
    Para usar:
    1. Registre-se ou faça login
    2. Copie o JWT token da resposta  
    3. Clique no botão 'Authorize' 🔒 acima
    4. Cole apenas o token (sem 'Bearer')
    5. Clique 'Authorize' e teste este endpoint
    
    Retorna dados simulados da Bovespa dos últimos 8 pregões.
    """
    return [
        {"Date": "2024-09-05","Open":136112.0,"High":136656.0,"Low":135959.0,"Close":136502.0,"Volume":7528700},
        {"Date": "2024-09-06","Open":136508.0,"High":136653.0,"Low":134476.0,"Close":134572.0,"Volume":7563300},
        {"Date": "2024-09-09","Open":134574.0,"High":135250.0,"Low":134399.0,"Close":134737.0,"Volume":6587600},
        {"Date": "2024-09-10","Open":134738.0,"High":134738.0,"Low":133754.0,"Close":134320.0,"Volume":8253500},
        {"Date": "2024-09-11","Open":134319.0,"High":135087.0,"Low":133757.0,"Close":134677.0,"Volume":7947300},
        {"Date": "2024-09-12","Open":134677.0,"High":134777.0,"Low":133591.0,"Close":134029.0,"Volume":7004900},
        {"Date": "2024-09-13","Open":134031.0,"High":135879.0,"Low":134031.0,"Close":134882.0,"Volume":8866000},
        {"Date": "2024-09-16","Open":134885.0,"High":135715.0,"Low":134870.0,"Close":135118.0,"Volume":6707000}
    ]

# 9) HEALTH CHECK
@app.get("/health-check", response_model=HealthCheck, summary="Health Check")
def health_check():
    """Verifica o status da aplicação"""
    return HealthCheck()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000, reload=True)