import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG & KEYS =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"
WEATHER_API_KEY = "40b796258caa0b4933609f73c70860b9"

# Seasonal Logic
CURRENT_DATE = datetime.now()
DATA_YEAR = 2025 if (CURRENT_DATE.month == 3 or (CURRENT_DATE.month == 4 and CURRENT_DATE.day < 10)) else 2026

STADIUM_DATA = {
    "ARI": {"lat": 33.445, "lon": -112.067, "roof": "retractable", "factor": 1.02},
    "ATL": {"lat": 33.891, "lon": -84.468, "roof": "open", "factor": 0.98},
    "BAL": {"lat": 39.284, "lon": -76.622, "roof": "open", "factor": 1.01},
    "BOS": {"lat": 42.346, "lon": -71.098, "roof": "open", "factor": 1.10},
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 1.00},
    "CIN": {"lat": 39.097, "lon": -84.506, "roof": "open", "factor": 1.12},
    "COL": {"lat": 39.756, "lon": -104.994, "roof": "open", "factor": 1.35},
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.02},
    "PHI": {"lat": 39.906, "lon": -75.166, "roof": "open", "factor": 0.98},
    "SDP": {"lat": 32.708, "lon": -117.157, "roof": "open", "factor": 0.90},
    "SEA": {"lat": 47.591, "lon": -122.332, "roof": "retractable", "factor": 0.92},
    "STL": {"lat": 38.623, "lon": -90.193, "roof": "open", "factor": 0.96}
}

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

# ========================= ENGINES =========================

def get_weather_mult(team_code):
    data = STADIUM_DATA.get(team_code)
    if not data or data['roof'] != 'open': return 1.0, "Stable"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={data['lat']}&lon={data['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        temp, wind = r['main']['temp'], r['wind']['speed']
        mult = (1 + (temp - 70) * 0.003) * (1 + wind * (0.01 if team_code == "CHC" else 0.005))
        return round(mult, 3), f"{int(temp)}°F {int(wind)}mph"
    except: return 1.0, "Weather Err"

def fetch_metrics():
    try:
        bat = pyb.batting_stats(DATA_YEAR, qual=0)
        pit = pyb.pitching_stats(DATA_YEAR, qual=0)
        bat['Disc'] = bat['BB%'] / bat['SO%']
        return bat.groupby('Team').agg({'wOBA': 'mean', 'Disc': 'mean'}).to_dict('index'), \
               pit.groupby('Team').agg({'FIP': 'mean', 'K%': 'mean'}).to_dict('index')
    except: return {}, {}

# ========================= EXECUTION =========================

def main():
    report = f"⚾ <b>MLB PRO-MODEL</b> – {datetime.now().strftime('%b %d')}\n\n"
    bat_stats, pit_stats = fetch_metrics()
    
    # Fetch Odds
    odds_url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    games = requests.get(odds_url, params={"apiKey": ODDS_API_KEY, "regions": "us", "markets": "h2h,totals"}).json()

    for game in games:
        home_f, away_f = game['home_team'], game['away_team']
        h_k, a_k = TEAM_MAP.get(home_f), TEAM_MAP.get(away_f)
        
        # Weather & Park Factors
        w_mult, w_desc = get_weather_mult(h_k)
        p_factor = STADIUM_DATA.get(h_k, {}).get('factor', 1.0)
        
        # Proj Math
        h_p, a_p = pit_stats.get(h_k, {'FIP': 4.2}), pit_stats.get(a_k, {'FIP': 4.2})
        h_b, a_b = bat_stats.get(h_k, {'wOBA': .32, 'Disc': .4}), bat_stats.get(a_k, {'wOBA': .32, 'Disc': .4})
        
        proj_total = round((((h_p['FIP'] + a_p['FIP'])/2)*0.8 + (h_b['wOBA'] + a_b['wOBA'])*11) * p_factor * w_mult, 1)
        
        # Value Check
        bookies = game.get('bookmakers', [])
        edge_txt = "No Edge"
        if bookies:
            for m in bookies[0]['markets']:
                if m['key'] == 'totals':
                    line = m['outcomes'][0]['point']
                    if proj_total > line + 0.8: edge_txt = f"🔥 OVER {line}"
                    elif proj_total < line - 0.8: edge_txt = f"🧊 UNDER {line}"

        report += f"<b>{away_f} @ {home_f}</b>\n"
        report += f"Weather: {w_desc} | Proj: {proj_total}\n"
        report += f"Action: {edge_txt}\n\n"

    # Send to Telegram
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "HTML"})

if __name__ == "__main__":
    main()
