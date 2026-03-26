import requests
from datetime import datetime
import pybaseball as pyb
import pandas as pd
import numpy as np

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"

# Opening Day Logic: Use 2025 data for the first 14 days of the 2026 season
CURRENT_DATE = datetime.now()
if CURRENT_DATE.month == 3 and CURRENT_DATE.day < 31:
    DATA_YEAR = 2025 
else:
    DATA_YEAR = 2026

TEAM_MAP = {
    "New York Yankees": "NYY", "Boston Red Sox": "BOS", "Toronto Blue Jays": "TOR",
    "Baltimore Orioles": "BAL", "Tampa Bay Rays": "TBR", "Chicago White Sox": "CHW",
    "Cleveland Guardians": "CLE", "Detroit Tigers": "DET", "Kansas City Royals": "KCR",
    "Minnesota Twins": "MIN", "Houston Astros": "HOU", "Los Angeles Angels": "LAA",
    "Oakland Athletics": "OAK", "Seattle Mariners": "SEA", "Texas Rangers": "TEX",
    "Atlanta Braves": "ATL", "Miami Marlins": "MIA", "New York Mets": "NYM",
    "Philadelphia Phillies": "PHI", "Washington Nationals": "WSN", "Chicago Cubs": "CHC",
    "Cincinnati Reds": "CIN", "Milwaukee Brewers": "MIL", "Pittsburgh Pirates": "PIT",
    "St. Louis Cardinals": "STL", "Arizona Diamondbacks": "ARI", "Colorado Rockies": "COL",
    "Los Angeles Dodgers": "LAD", "San Diego Padres": "SDP", "San Francisco Giants": "SFG"
}

# ========================= FETCH DATA =========================
def fetch_odds_api():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "american"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Odds API error: {e}")
        return []

def fetch_predictive_metrics():
    try:
        # Pulling season-level stats for the designated DATA_YEAR
        batting = pyb.batting_stats(DATA_YEAR)
        pitching = pyb.pitching_stats(DATA_YEAR)
        
        # wOBA (Weighted On-Base Average)
        batting_team = batting.groupby('Team')['wOBA'].mean().to_dict()
        
        # FIP (Fielding Independent Pitching)
        pitching_team = pitching.groupby('Team')['FIP'].mean().to_dict()
        
        return batting_team, pitching_team
    except Exception as e:
        print(f"pybaseball error: {e}")
        return {}, {}

# ========================= MAIN ALGORITHM =========================
def run_mlb_betting_algorithm():
    report = f"⚾ <b>MLB Pro-Model Report</b> – {datetime.now().strftime('%B %d, %Y')}\n"
    report += f"<i>Using {DATA_YEAR} baseline data</i>\n\n"
    
    games = fetch_odds_api()
    batting_team, pitching_team = fetch_predictive_metrics()

    if not games:
        return "⚠️ No games found or API error."

    for game in games:
        home_full = game.get('home_team')
        away_full = game.get('away_team')
        home_key = TEAM_MAP.get(home_full, home_full)
