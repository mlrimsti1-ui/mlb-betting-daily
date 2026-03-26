import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG & 2026 ACCESS =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"
WEATHER_API_KEY = "40b796258caa0b4933609f73c70860b9"

# 2026 Opening Day Stadium Database & Park Factors
STADIUM_DATA = {
    "NYM": {"lat": 40.757, "lon": -73.846, "roof": "open", "factor": 0.94},   # Citi Field
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 1.00},   # Wrigley
    "MIL": {"lat": 43.028, "lon": -87.971, "roof": "retractable", "factor": 1.00}, 
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.02},  # Dodger Stadium
    "SEA": {"lat": 47.591, "lon": -122.332, "roof": "retractable", "factor": 0.91}
}

TEAM_MAP = {"Pittsburgh Pirates": "PIT", "New York Mets": "NYM", "Chicago Cubs": "CHC", 
            "Los Angeles Dodgers": "LAD", "Arizona Diamondbacks": "ARI", "Washington Nationals": "WSN"}

# ========================= ENGINES =========================

def get_weather_impact(team_code):
    data = STADIUM_DATA.get(team_code, {"roof": "retractable"})
    if data['roof'] != 'open': return 1.0, "Controlled"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={data['lat']}&lon={data['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        t, w = r['main']['temp'], r['wind']['speed']
        # 2026 Ball Flight Logic: Cold air suppresses, Wind at Wrigley multiplies
        mult = (1 + (t - 70) * 0.003) * (1 + w * (0.012 if team_code == "CHC" else 0.006))
        return round(mult, 3), f"{int(t)}°F {int(w)}mph"
    except: return 1.0, "Weather N/A"

def fetch_metrics():
    # Using 2025 full-season data for 2026 Opening Day projections
    pit = pyb.pitching_stats(2025, qual=0)[['Team', 'FIP', 'K%', 'WHIP']]
    bat = pyb.batting_stats(2025, qual=0)[['Team', 'wOBA', 'SO%']]
    return bat.
