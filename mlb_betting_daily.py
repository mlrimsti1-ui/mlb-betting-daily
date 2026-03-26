import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG & KEYS =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"
WEATHER_API_KEY = "40b796258caa0b4933609f73c70860b9"

# Updated for 2026 Opening Day Matchups
TEAM_MAP = {
    "Pittsburgh Pirates": "PIT", "New York Mets": "NYM", "Chicago Cubs": "CHC",
    "Washington Nationals": "WSN", "Milwaukee Brewers": "MIL", "Chicago White Sox": "CHW",
    "Arizona Diamondbacks": "ARI", "Los Angeles Dodgers": "LAD"
}

STADIUM_DATA = {
    "NYM": {"lat": 40.757, "lon": -73.846, "roof": "open", "factor": 0.94}, # Citi Field
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 1.05}, # Wrigley (Wind Out)
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.02}
}

# ========================= CORE ENGINES =========================

def get_weather(team_code):
    stadium = STADIUM_DATA.get(team_code, {"roof": "retractable", "factor": 1.0})
    if stadium['roof'] != 'open': return 1.0, "Indoor"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={stadium['lat']}&lon={stadium['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        temp, wind = r['main']['temp'], r['wind']['speed']
        # 2026 Physics: Balls carry ~1% further for every 10 degrees above 70°F
        mult = (1 + (temp - 70) * 0.003) * (1 + wind * 0.006)
        return round(mult, 3), f"{int(temp)}°F {int(wind)}mph"
    except: return 1.0, "Weather Error"

def fetch_stats():
    # Fetching 2025 data as the baseline for the start of 2026
    pit = pyb.pitching_stats(2025, qual=0)[['Team', 'FIP', 'K%', 'WHIP', 'ERA']]
    bat = pyb.batting_stats(2025, qual=0)[['Team', 'wOBA', 'SO%', 'BB%']]
    return bat.groupby('Team').mean().to_dict('index'), pit.groupby('Team').mean().to_dict('index')

# ========================= EXECUTION =========================

def run_model():
    bat_stats, pit_stats = fetch_stats()
    
    # Call multiple markets: Moneyline (h2h) and Totals
    odds_url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    games = requests.get(odds_url, params={"apiKey": ODDS})
