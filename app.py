import os
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="EUR/USD Intelligence", version="1.0.0")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
API_KEY = os.getenv("TWELVE_DATA_KEY", "").strip()
TD_URL = "https://api.twelvedata.com/time_series"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

def ema(values, period):
    if len(values) < period:
        return None
    alpha = 2 / (period + 1)
    result = sum(values[:period]) / period
    for value in values[period:]:
        result = value * alpha + result * (1 - alpha)
    return result

def rsi(values, period=14):
    if len(values) <= period:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0)) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))

@app.get("/api/analysis")
def analysis():
    if not API_KEY:
        return JSONResponse(status_code=503, content={
            "error": "TWELVE_DATA_KEY non configurata su Render.",
            "setup": "Aggiungi TWELVE_DATA_KEY in Environment."
        })
    try:
        response = requests.get(TD_URL, params={
            "symbol": "EUR/USD",
            "interval": "5min",
            "outputsize": 120,
            "apikey": API_KEY,
            "format": "JSON"
        }, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if "values" not in payload:
            message = payload.get("message") or payload.get("code") or "Risposta non valida da Twelve Data"
            return JSONResponse(status_code=502, content={"error": str(message)})
        candles = list(reversed(payload["values"]))
        closes = [float(c["close"]) for c in candles]
        current = closes[-1]
        e9, e21, e50 = ema(closes, 9), ema(closes, 21), ema(closes, 50)
        r = rsi(closes, 14)
        score = 0
        if e9 is not None and e21 is not None:
            score += 1 if e9 > e21 else -1 if e9 < e21 else 0
        if e21 is not None and e50 is not None:
            score += 1 if e21 > e50 else -1 if e21 < e50 else 0
        if r is not None:
            score += 1 if 50 < r < 70 else -1 if 30 < r < 50 else 0
        signal = "BUY" if score >= 2 else "SELL" if score <= -2 else "WAIT"
        return {
            "symbol": "EUR/USD",
            "interval": "5min",
            "price": current,
            "ema9": e9,
            "ema21": e21,
            "ema50": e50,
            "rsi14": r,
            "score": score,
            "signal": signal,
            "updated": candles[-1].get("datetime"),
            "candles": candles[-30:],
            "note": "Segnale tecnico euristico, non probabilità né garanzia di rendimento. Solo analisi: nessun ordine viene eseguito."
        }
    except requests.RequestException as exc:
        return JSONResponse(status_code=502, content={"error": f"Errore connessione Twelve Data: {exc}"})
    except (ValueError, KeyError, TypeError) as exc:
        return JSONResponse(status_code=500, content={"error": f"Errore elaborazione dati: {exc}"})
