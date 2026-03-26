import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG & KEYS =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"
WEATHER_API_KEY = "40b796258caa0b4933609f73c70860b9"

# 2026 Opening Day Venues
STADIUM_DATA = {
    "NYM": {"lat": 40.757, "lon": -73.846, "roof": "open", "factor": 0.94},   # Citi Field
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 1.00},   # Wrigley
    "MIL": {"lat": 43.028, "lon": -87.971, "roof": "retractable", "factor": 1.00}, 
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.02},  # Dodger Stadium
    "SEA": {"lat": 47.591, "lon": -122.332, "roof": "retractable", "factor": 0.91},
    "BAL": {"lat": 39.284, "lon": -76.622, "roof": "open", "factor": 1.01}
}

TEAM_MAP = {
    "Pittsburgh Pirates": "PIT", "New York Mets": "NYM", "Chicago Cubs": "CHC", 
    "Washington Nationals": "WSN", "Milwaukee Brewers": "MIL", "Arizona Diamondbacks": "ARI",
    "Los Angeles Dodgers": "LAD", "Baltimore Orioles": "BAL", "Minnesota Twins": "MIN"
}

# ========================= ANALYTICS ENGINES =========================

def get_weather_impact(team_code):
    stadium = STADIUM_DATA.get(team_code, {"roof": "retractable", "factor": 1.0})
    if stadium['roof'] != 'open': return 1.0, "Indoor"
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={stadium['lat']}&lon={stadium['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        temp, wind = r['main']['temp'], r['wind']['speed']
        # Adjusted 2026 formula: Wind is deadlier in cold March air
        mult = (1 + (temp - 70) * 0.0035) * (1 + wind * (0.012 if team_code == "CHC" else 0.006))
        return round(mult, 3), f"{int(temp)}°F {int(wind)}mph"
    except: return 1.0, "Weather Err"

def fetch_metrics():
    # Early 2026 relies on 2025 stability metrics
    pit = pyb.pitching_stats(2025, qual=0)[['Team', 'FIP', 'K%', 'WHIP']]
    bat = pyb.batting_stats(2025, qual=0)[['Team', 'wOBA', 'SO%']]
    return bat.groupby('Team').mean().to_dict('index'), pit.groupby('Team').mean().to_dict('index')

# ========================= EXECUTION =========================

def main():
    bat_stats, pit_stats = fetch_metrics()
    
    # Updated Market List for Full Game, ML, F5, and NRFI
    markets = "h2h,totals,h2h_1st_5_innings,totals_1st_1_innings"
    odds_url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    games = requests.get(odds_url, params={"apiKey": ODDS_API_KEY, "regions": "us", "markets": markets}).json()

    report = f"⚾ <b>MLB OMNI-REPORT: OPENING DAY 2026</b>\n\n"

    for game in games:
        h_f, a_f = game['home_team'], game['away_team']
        h_k, a_k = TEAM_MAP.get(h_f), TEAM_MAP.get(a_f)
        if not h_k or not a_k: continue

        w_mult, w_desc = get_weather_impact(h_k)
        h_p, a_p = pit_stats.get(h_k, {'FIP': 4.1, 'K%': .22}), pit_stats.get(a_k, {'FIP': 4.1, 'K%': .22})
        h_b, a_b = bat_stats.get(h_k, {'wOBA': .31}), bat_stats.get(a_k, {'wOBA': .31})

        # 1. Moneyline & F5 Logic
        ml_lean = h_f if h_p['FIP'] < a_p['FIP'] - 0.5 else a_f if a_p['FIP'] < h_p['FIP'] - 0.5 else "TOSS-UP"
        
        # 2. Total & F5 Projections
        proj_full = round((((h_p['FIP'] + a_p['FIP'])/2)*0.85 + (h_b['wOBA'] + a_b['wOBA'])*10.5) * w_mult, 1)
        proj_f5 = round(proj_full * 0.52, 1)

        # 3. NRFI Engine (High K% + Cold Weather = NRFI)
        avg_k = (h_p['K%'] + a_p['K%']) / 2
        nrfi_status = "🔥 STRONG" if avg_k > 0.27 and w_mult < 1.0 else "LEAN" if avg_k > 0.24 else "PASS"

        # Edge Detection
        edge_msg = ""
        bookies = game.get('bookmakers', [])
        if bookies:
            for market in bookies[0]['markets']:
                if market['key'] == 'totals':
                    line = market['outcomes'][0]['point']
                    if proj_full > line + 0.8: edge_msg = f"🟢 <b>EDGE: OVER {line}</b>"
                    elif proj_full < line - 0.8: edge_msg = f"🔴 <b>EDGE: UNDER {line}</b>"

        report += f"<b>{a_f} @ {h_f}</b>\n"
        report += f"🌡️ {w_desc} | Proj: {proj_full} (F5: {proj_f5})\n"
        report += f"📈 ML: {ml_lean} | 🎯 NRFI: {nrfi_status}\n"
        if edge_msg: report += f"{edge_msg}\n"
        report += "\n"

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "HTML"})

if __name__ == "__main__":
    main()
