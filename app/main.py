import socket
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db, engine
from app.models   import Base, User
from app.schemas  import UserCreate, UserLogin, Token
from app.auth     import (
    hash_password, verify_password,
    get_user_by_email, create_jwt_token, decode_jwt
)
from app.scraping import get_bovespa_data

# Cria as tabelas se ainda não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API RESTful Projeto 2025.1",
    version="1.0.0",
    description="Cadastro, login e endpoint protegido com JWT"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

bearer_scheme = HTTPBearer()

@app.post("/registrar", response_model=Token, summary="Registrar usuário")
def registrar(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já registrado."
        )
    novo = User(
        nome=user.name,
        email=user.email,
        senha_hash=hash_password(user.senha)
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    token = create_jwt_token(novo)
    return {"jwt": token}

@app.post("/login", response_model=Token, summary="Login de usuário")
def login(data: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, data.email)
    if not db_user or not verify_password(data.senha, db_user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas."
        )
    token = create_jwt_token(db_user)
    return {"jwt": token}

@app.get(
    "/consultar",
    summary="Consultar dados da Bovespa",
    description="🔒 **Endpoint Protegido** - Requer autenticação JWT via botão Authorize",
    response_model=List[dict]
)
def consultar(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    payload = decode_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return get_bovespa_data()

@app.get("/health_check", summary="Health Check")
def health_check():
    return {
        "status":    "ok",
        "hostname":  socket.gethostname(),
        "timestamp": datetime.utcnow().isoformat()
    }
