import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG & KEYS =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"
WEATHER_API_KEY = "40b796258caa0b4933609f73c70860b9"

STADIUM_DATA = {
    "NYM": {"lat": 40.757, "lon": -73.846, "roof": "open", "factor": 0.94},
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 1.00},
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.02},
    "SEA": {"lat": 47.591, "lon": -122.332, "roof": "retractable", "factor": 0.91}
}

TEAM_MAP = {
    "Pittsburgh Pirates": "PIT", "New York Mets": "NYM", "Chicago Cubs": "CHC", 
    "Arizona Diamondbacks": "ARI", "Los Angeles Dodgers": "LAD"
}

# ========================= ANALYTICS ENGINES =========================

def get_weather_impact(team_code):
    stadium = STADIUM_DATA.get(team_code, {"roof": "retractable", "factor": 1.0})
    if stadium['roof'] != 'open': return 1.0, "Indoor"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={stadium['lat']}&lon={stadium['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        t, w = r['main']['temp'], r['wind']['speed']
        mult = (1 + (t - 70) * 0.0035) * (1 + w * (0.012 if team_code == "CHC" else 0.006))
        return round(mult, 3), f"{int(t)}°F {int(w)}mph"
    except: return 1.0, "Weather Err"

def fetch_metrics():
    # FIXED: Updated column names to 'K%' and 'BB%' to match latest pybaseball/FanGraphs schema
    try:
        pit = pyb.pitching_stats(2025, qual=0)[['Team', 'FIP', 'K%', 'WHIP']]
        bat = pyb.batting_stats(2025, qual=0)[['Team', 'wOBA', 'K%']] # Changed 'SO%' to 'K%'
        return bat.groupby('Team').mean().to_dict('index'), pit.groupby('Team').mean().to_dict('index')
    except KeyError as e:
        print(f"Column Error: {e}")
        # Fallback logic if the data is missing
        return {}, {}

# ========================= EXECUTION =========================

def main():
    bat_stats, pit_stats = fetch_metrics()
    if not bat_stats:
        print("Error: Could not retrieve batting/pitching stats.")
        return

    # Markets: Moneyline, Totals, NRFI (1st Inning Under 0.5)
    markets = "h2h,totals,totals_1st_1_innings"
    odds_url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    games = requests.get(odds_url, params={"apiKey": ODDS_API_KEY, "regions": "us", "markets": markets}).json()

    report = f"⚾ <b>MLB OMNI-REPORT: {datetime.now().strftime('%b %d')}</b>\n\n"

    for game in games:
        h_f, a_f = game['home_team'], game['away_team']
        h_k, a_k = TEAM_MAP.get(h_f), TEAM_MAP.get(a_f)
        if not h_k or not a_k: continue

        w_mult, w_desc = get_weather_impact(h_k)
        h_p, a_p = pit_stats.get(h_k, {'FIP': 4.2, 'K%': .22}), pit_stats.get(a_k, {'FIP': 4.2, 'K%': .22})
        h_b, a_b = bat_stats.get(h_k, {'wOBA': .31}), bat_stats.get(a_k, {'wOBA': .31})

        # 1. Moneyline & Projections
        ml_lean = h_f if h_p['FIP'] < a_p['FIP'] - 0.5 else a_f if a_p['FIP'] < h_p['FIP'] - 0.5 else "TOSS-UP"
        proj_full = round((((h_p['FIP'] + a_p['FIP'])/2)*0.85 + (h_b['wOBA'] + a_b['wOBA'])*10.5) * w_mult, 1)
        proj_f5 = round(proj_full * 0.52, 1)

        # 2. NRFI Engine
        avg_k = (h_p['K%'] + a_p['K%']) / 2
        nrfi_status = "🔥 STRONG" if avg_k > 0.27 and w_mult < 1.0 else "LEAN"

        report += f"<b>{a_f} @ {h_f}</b>\n"
        report += f"🌡️ {w_desc} | Proj: {proj_full} (F5: {proj_f5})\n"
        report += f"📈 ML: {ml_lean} | 🎯 NRFI: {nrfi_status}\n\n"

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "HTML"})

if __name__ == "__main__":
    main()
