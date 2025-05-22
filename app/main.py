# app/main.py
from fastapi import FastAPI

# reaproveite o objeto da sua app atual
from .app import app as fastapi_app   # supondo que app.py já possui "app = FastAPI()"

# Alias para manter o nome que o Uvicorn procura
app = fastapi_app
