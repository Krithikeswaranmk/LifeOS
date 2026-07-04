from typing import Optional, List
"""
LifeOS v2 — Dashboard API (read-only, serves history + stats + weather)
Run alongside monitor.py to power the dashboard at http://localhost:8000
"""
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from agents.weather_agent import WeatherAgent
from data.store import get_history, get_stats

app = FastAPI(title="LifeOS v2 Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/history")
def api_history():
    return {"history": get_history(200)}

@app.get("/api/stats")
def api_stats():
    return get_stats()

@app.get("/api/weather")
def api_weather():
    return WeatherAgent(city=config.CITY, unit=config.TEMP_UNIT).get_weather()

@app.get("/api/health")
def health():
    return {"status": "ok"}

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")
