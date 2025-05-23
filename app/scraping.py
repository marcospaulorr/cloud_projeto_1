# app/scraping.py
import httpx
from datetime import datetime

AWESOME_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL"

async def get_usd_brl_rate():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(AWESOME_URL)
        r.raise_for_status()
        data = r.json().get("USDBRL") or {}
    return {
        "date": data.get("create_date", datetime.utcnow().isoformat()),
        "rate": float(data.get("bid", 0.0)),
    }
