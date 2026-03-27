import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG & KEYS =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"
WEATHER_API_KEY = "40b796258caa0b4933609f73c70860b9"

# v11.0 TUNING
BULLPEN_TAX = 1.05
INDOOR_FLOOR = 1.03
POWER_TEAMS = ["LAD", "ATL", "NYY"]

STADIUM_DATA = {
    "ARI": {"lat": 33.445, "lon": -112.067, "roof": "retractable", "factor": 1.02}, 
    "ATL": {"lat": 33.891, "lon": -84.468, "roof": "open", "factor": 1.03},        
    "BAL": {"lat": 39.284, "lon": -76.622, "roof": "open", "factor": 1.01},        
    "BOS": {"lat": 42.346, "lon": -71.098, "roof": "open", "factor": 1.09},        
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 1.00},        
    "CHW": {"lat": 41.830, "lon": -87.634, "roof": "open", "factor": 0.99},        
    "CIN": {"lat": 39.097, "lon": -84.506, "roof": "open", "factor": 1.13},        
    "CLE": {"lat": 41.496, "lon": -81.685, "roof": "open", "factor": 1.01},        
    "COL": {"lat": 39.756, "lon": -104.994, "roof": "open", "factor": 1.34},       
    "DET": {"lat": 42.339, "lon": -83.049, "roof": "open", "factor": 0.97},        
    "HOU": {"lat": 29.757, "lon": -95.356, "roof": "retractable", "factor": 1.01}, 
    "KCR": {"lat": 39.052, "lon": -94.480, "roof": "open", "factor": 1.02},        
    "LAA": {"lat": 33.800, "lon": -117.883, "roof": "open", "factor": 1.02},       
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.05},       
    "MIA": {"lat": 25.778, "lon": -80.220, "roof": "retractable", "factor": 0.96}, 
    "MIL": {"lat": 43.028, "lon": -87.971, "roof": "retractable", "factor": 1.00}, 
    "MIN": {"lat": 44.982, "lon": -93.278, "roof": "open", "factor": 1.01},        
    "NYM": {"lat": 40.757, "lon": -73.846, "roof": "open", "factor": 0.94},        
    "NYY": {"lat": 40.830, "lon": -73.926, "roof": "open", "factor": 1.02},        
    "OAK": {"lat": 38.581, "lon": -121.505, "roof": "open", "factor": 1.03},       
    "PHI": {"lat": 39.906, "lon": -75.166, "roof": "open", "factor": 1.03},        
    "PIT": {"lat": 40.447, "lon": -80.006, "roof": "open", "factor": 0.96},        
    "SDP": {"lat": 32.708, "lon": -117.157, "roof": "open", "factor": 0.92},       
    "SEA": {"lat": 47.591, "lon": -122.332, "roof": "retractable", "factor": 0.91}, 
    "SFG": {"lat": 37.778, "lon": -122.390, "roof": "open", "factor": 0.94},        
    "STL": {"lat": 38.623, "lon": -90.193, "roof": "open", "factor": 0.96},        
    "TBR": {"lat": 27.768, "lon": -82.653, "roof": "dome", "factor": 0.95},        
    "TEX": {"lat": 32.751, "lon": -97.083, "roof": "retractable", "factor": 1.00}, 
    "TOR": {"lat": 43.641, "lon": -79.389, "roof": "retractable", "factor": 1.01}, 
    "WSN": {"lat": 38.873, "lon": -77.007, "roof": "open", "factor": 0.97}         
}

TEAM_MAP = {
    "New York Yankees": "NYY", "Boston Red Sox": "BOS", "Toronto Blue Jays": "TOR",
    "Baltimore Orioles": "BAL", "Tampa Bay Rays": "TBR", "Chicago White Sox": "CWS",
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

def fetch_metrics():
    print("Fetching 2025 player metrics...")
    try:
        pit = pyb.pitching_stats(2025, qual=0)[['Team', 'FIP', 'K%', 'WHIP']]
        bat = pyb.batting_stats(2025, qual=0)[['Team', 'wOBA', 'K%']]
        return bat.groupby('Team').mean().to_dict('index'), pit.groupby('Team').mean().to_dict('index')
    except Exception as e:
        print(f"Stat Fetch Error: {e}")
        return None, None

def get_weather(team_code):
    stadium = STADIUM_DATA.get(team_code, {"roof": "retractable", "factor": 1.0})
    if stadium['roof'] != 'open': return INDOOR_FLOOR, "Indoor"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={stadium['lat']}&lon={stadium['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        t, w = r['main']['temp'], r['wind']['speed']
        mult = (1 + (t - 70) * 0.0035) * (1 + w * (0.012 if team_code == "CHC" else 0.006))
        return round(mult, 3), f"{int(t)}°F {int(w)}mph"
    except: return 1.0, "Weather N/A"

# ========================= MAIN EXECUTION =========================

def main():
    bat_stats, pit_stats = fetch_metrics()
    if not bat_stats: return

    print("Fetching live odds...")
    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "h2h,totals", "oddsFormat": "american"}
    response = requests.get(f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds", params=params)
    data = response.json()

    if not isinstance(data, list):
        print(f"API Error: {data.get('message', 'Unknown Error')}")
        return

    report = f"⚾ <b>MLB OMNI-REPORT v11.0: {datetime.now().strftime('%b %d')}</b>\n"
    report += f"<i>Adjustments: Bullpen Tax (1.05x), Indoor Floor (1.03x)</i>\n\n"

    for game in data:
        try:
            h_f, a_f = game['home_team'], game['away_team']
            h_k, a_k = TEAM_MAP.get(h_f), TEAM_MAP.get(a_f)
            if not h_k or not a_k: continue

            w_mult, w_desc = get_weather(h_k)
            # FIX: Define park_factor before using it
            park_factor = STADIUM_DATA.get(h_k, {}).get('factor', 1.0)
            
            h_p, a_p = pit_stats.get(h_k, {'FIP': 4.1, 'K%': .22}), pit_stats.get(a_k, {'FIP': 4.1, 'K%': .22})
            h_b, a_b = bat_stats.get(h_k, {'wOBA': .31, 'K%': .22}), bat_stats.get(a_k, {'wOBA': .31, 'K%': .22})

            # 1. Projections
            proj_full = round((((h_p['FIP'] + a_p['FIP'])/2)*0.85 + (h_b['wOBA'] + a_b['wOBA'])*10.5) * w_mult * park_factor * BULLPEN_TAX, 1)
            
            # v11.0: Power Lineup Weighting
            if h_k in POWER_TEAMS:
                proj_full += 0.5

            proj_f5 = round(proj_full * 0.52, 1)

            # 2. Moneyline & NRFI
            ml_lean = h_f if h_p['FIP'] < a_p['FIP'] - 0.4 else a_f if a_p['FIP'] < h_p['FIP'] - 0.4 else "TOSS-UP"
            avg_k_pot = (h_p['K%'] + a_p['K%'] + h_b['K%'] + a_b['K%']) / 4
            nrfi = "STRONG" if avg_k_pot > 0.22 and w_mult < 1.05 else "NEUTRAL"

            # 3. Edge Detection
            total_action, f5_action = "Neutral", "Neutral"
            bookies = game.get('bookmakers', [])
            if bookies:
                for market in bookies[0]['markets']:
                    if market['key'] == 'totals':
                        line = market['outcomes'][0]['point']
                        if proj_full > line + 0.6: total_action = "Over"
                        elif proj_full < line - 0.6: total_action = "Under"
                        if proj_f5 > (line/2) + 0.4: f5_action = "Over"
                        elif proj_f5 < (line/2) - 0.4: f5_action = "Under"

            # 4. Final Formatting
            report += f"<b>{a_f} @ {h_f}</b>\n"
            report += f"🌡️ {w_desc} | Proj: {proj_full} (F5: {proj_f5})\n"
            report += f"📈 ML: {ml_lean} | 🎯 NRFI: {nrfi} | Total: {total_action} | F5: {f5_action}\n\n"
            print(f"Processed: {a_f} @ {h_f}")

        except Exception as e:
            print(f"Game error for {game.get('home_team')}: {e}")
            continue

    print("Sending report to Telegram...")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "HTML"})
    print("Done.")

if __name__ == "__main__":
    main()
