from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    nome: str
    email: str
    senha: str

class UserLogin(BaseModel):
    email: str
    senha: str

class Token(BaseModel):
    jwt: str