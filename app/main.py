from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from jose import jwt, JWTError
from datetime import datetime, timedelta
import io

from app.config import settings
from app.database import SessionLocal, engine
from app.models import Base, User
from app.schemas import UserCreate, UserLogin, Token
from app.auth import create_access_token

# Criar tabelas no banco de dados
Base.metadata.create_all(bind=engine)

app = FastAPI(debug=settings.debug)
security = HTTPBearer()

# Dependency para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint para verificar a saúde da aplicação
@app.get("/health")
def health_check():
    return {"status": "ok", "debug": settings.debug}

# Endpoint para registrar um novo usuário
@app.post("/registrar", response_model=Token)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar se o email já existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Criar o novo usuário
    hashed_password = User.get_password_hash(user.senha)
    new_user = User(
        nome=user.nome,
        email=user.email,
        hashed_password=hashed_password
    )
    
    # Salvar no banco de dados
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Gerar o token JWT
    token_data = {"sub": user.email, "name": user.nome}
    jwt_token = create_access_token(token_data)
    
    return {"jwt": jwt_token}

# Endpoint para login de usuário
@app.post("/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # Verificar se o usuário existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verificar a senha
    if not User.verify_password(user.senha, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Gerar o token JWT
    token_data = {"sub": db_user.email, "name": db_user.nome}
    jwt_token = create_access_token(token_data)
    
    return {"jwt": jwt_token}

# Verificar o token JWT
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials"
        )
    return payload

# Endpoint para consultar dados externos (Índice Bovespa)
@app.get("/consultar")
def fetch_data(current_user: dict = Depends(get_current_user)):
    # Aqui você pode implementar o web scraping para os dados que você escolher
    # Exemplo: Dados do índice Bovespa (últimos 10 dias)
    
    try:
        # Exemplo usando Yahoo Finance para dados do Ibovespa
        url = "https://finance.yahoo.com/quote/%5EBVSP/history/"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraindo dados da tabela (este é um exemplo e pode precisar de ajustes)
        data = []
        table = soup.find('table', {'data-test': 'historical-prices'})
        if table:
            rows = table.find_all('tr')
            for row in rows[1:11]:  # Limitar aos últimos 10 dias
                cols = row.find_all('td')
                if len(cols) >= 6:
                    date = cols[0].text
                    open_price = cols[1].text
                    high = cols[2].text
                    low = cols[3].text
                    close = cols[4].text
                    volume = cols[5].text
                    
                    data.append({
                        'Date': date,
                        'Open': open_price,
                        'High': high,
                        'Low': low,
                        'Close': close,
                        'Volume': volume
                    })
        
        # Retornar os dados em formato JSON
        return data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching data: {str(e)}"
        )