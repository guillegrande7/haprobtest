import os
import json
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Acme Logistics Carrier API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOADS_PATH = os.path.join(BASE_DIR, "loads.json")
HISTORTY_PATH = os.path.join(BASE_DIR, "calls_history.json")

# --- Autenticación con Api Key ---
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-KEY")

def get_api_key(header: str = Depends(api_key_header)):
    if header != API_KEY:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return header

# --- BASE DE DATOS LOCAL ---
with open(LOADS_PATH, "r") as f:
    loads_db = json.load(f)

class CallSummary(BaseModel):
    load_id: str
    mc_number: str
    outcome: str  # Ejemplo: "BOOKED", "FAILED_NEGOTIATION"
    sentiment: str # Ejemplo: "Happy", "Frustrated"
    final_rate: Optional[float] = None
    transcript_summary: str

# --- ENDPOINTS ---
@app.get("/search-load")
def search_load(origin: str, destination: str, token: str = Depends(get_api_key)):
    """Busca cargas que coincidan con los criterios"""
    results = [l for l in loads_db if origin.lower() in l["origin"].lower() 
               and destination.lower() in l["destination"].lower()]
    
    if not results:
        raise HTTPException(status_code=404, detail="No matching loads found")
    return results[0]

@app.post("/call-end")
def handle_call_end(summary: CallSummary, token: str = Depends(get_api_key)):
    """
    Objetivo: Extraer y clasificar datos de la llamada (Requirement 26-29)
    """
    # Aquí deberías guardar esto en un archivo (ej. calls.json) 
    # para que tu Dashboard de Streamlit pueda leerlo después.
    with open(HISTORTY_PATH, "a+") as f:
        # Lógica para persistir la data
        f.write(json.dumps(summary.dict()) + "\n")
    
    return {"status": "success", "message": "Call data analyzed and stored"}