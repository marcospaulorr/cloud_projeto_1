import yfinance as yf
from datetime import datetime, timedelta

def get_bovespa_data():
    hoje = datetime.now()
    inicio = hoje - timedelta(days=14)
    df = yf.download("^BVSP",
                     start=inicio.strftime("%Y-%m-%d"),
                     end=hoje.strftime("%Y-%m-%d"))
    # Pega só até 10 dias e formata
    df = df.tail(10).reset_index()
    if df.empty:
        return []
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    resultado = []
    for _, row in df.iterrows():
        resultado.append({
            "Date":  row["Date"],
            "Open":  round(row["Open"],  2),
            "High":  round(row["High"],  2),
            "Low":   round(row["Low"],   2),
            "Close": round(row["Close"], 2),
            "Volume": int(row["Volume"]),
        })
    return resultado
