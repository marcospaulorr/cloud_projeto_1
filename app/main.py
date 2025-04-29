from fastapi import FastAPI, Depends, HTTPException, status
from app.config import settings

app = FastAPI(debug=settings.debug)

@app.get("/health")
def health_check():
    return {"status": "ok", "debug": settings.debug}
