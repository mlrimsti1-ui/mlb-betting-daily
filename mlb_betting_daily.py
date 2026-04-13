import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb
import os  # Add this at the top

# ========================= CONFIG & KEYS =========================
# Use os.getenv to pull from GitHub Secrets, with your hardcoded ones as fallbacks
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8779455773")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "4bdba5b98d90cc609eeadf39b1c0be2d")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "40b796258caa0b4933609f73c70860b9")

# v12.1 LEAK-FIX CONSTANTS
BULLPEN_TAX = 1.08        
ABS_INFLATION = 1.02      
INDOOR_FLOOR = 1.03
POWER_TEAMS = ["LAD", "ATL", "NYY"]
EXPERIENCE_TAX = 0.4
PLATOON_PENALTY = -0.3
SUNDAY_LINEUP_TAX = 0.02 

STADIUM_DATA = {
    "ARI": {"lat": 33.445, "lon": -112.067, "roof": "retractable", "factor": 1.01}, 
    "ATL": {"lat": 33.891, "lon": -84.468, "roof": "open", "factor": 1.03},        
    "BAL": {"lat": 39.284, "lon": -76.622, "roof": "open", "factor": 1.01},        
    "BOS": {"lat": 42.346, "lon": -71.098, "roof": "open", "factor": 1.09},        
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 0.92},        
    "CHW": {"lat": 41.830, "lon": -87.634, "roof": "open", "factor": 0.97},        
    "CIN": {"lat": 39.097, "lon": -84.506, "roof": "open", "factor": 1.13},        
    "CLE": {"lat": 41.496, "lon": -81.685, "roof": "open", "factor": 1.01},        
    "COL": {"lat": 39.756, "lon": -104.994, "roof": "open", "factor": 1.34},       
    "DET": {"lat": 42.339, "lon": -83.049, "roof": "open", "factor": 1.06},       
    "HOU": {"lat": 29.757, "lon": -95.356, "roof": "retractable", "factor": 1.01}, 
    "KCR": {"lat": 39.052, "lon": -94.480, "roof": "open", "factor": 1.11},        
    "LAA": {"lat": 33.800, "lon": -117.883, "roof": "open", "factor": 1.02},       
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.05},       
    "MIA": {"lat": 25.778, "lon": -80.220, "roof": "retractable", "factor": 1.06}, 
    "MIL": {"lat": 43.028, "lon": -87.971, "roof": "retractable", "factor": 1.01}, 
    "MIN": {"lat": 44.982, "lon": -93.278, "roof": "open", "factor": 1.06},        
    "NYM": {"lat": 40.757, "lon": -73.846, "roof": "open", "factor": 0.96},        
    "NYY": {"lat": 40.830, "lon": -73.926, "roof": "open", "factor": 1.02},        
    "OAK": {"lat": 38.581, "lon": -121.505, "roof": "open", "factor": 1.09},       
    "PHI": {"lat": 39.906, "lon": -75.166, "roof": "open", "factor": 1.03},        
    "PIT": {"lat": 40.447, "lon": -80.006, "roof": "open", "factor": 1.01},        
    "SDP": {"lat": 32.708, "lon": -117.157, "roof": "open", "factor": 0.94},       
    "SEA": {"lat": 47.591, "lon": -122.332, "roof": "retractable", "factor": 0.81}, 
    "SFG": {"lat": 37.778, "lon": -122.390, "roof": "open", "factor": 0.91},        
    "STL": {"lat": 38.623, "lon": -90.193, "roof": "open", "factor": 0.97},        
    "TBR": {"lat": 27.768, "lon": -82.653, "roof": "dome", "factor": 1.02},        
    "TEX": {"lat": 32.751, "lon": -97.083, "roof": "retractable", "factor": 1.00}, 
    "TOR": {"lat": 43.641, "lon": -79.389, "roof": "retractable", "factor": 0.98},        
    "WSN": {"lat": 38.873, "lon": -77.007, "roof": "open", "factor": 1.01}          
}

TEAM_MAP = {
    "New York Yankees": "NYY", "Boston Red Sox": "BOS", "Toronto Blue Jays": "TOR",
    "Baltimore Orioles": "BAL", "Tampa Bay Rays": "TBR", "Chicago White Sox": "CHW",
    "Cleveland Guardians": "CLE", "Detroit Tigers": "DET", "Kansas City Royals": "KCR",
    "Minnesota Twins": "MIN", "Houston Astros": "HOU", "Los Angeles Angels": "LAA",
    "Athletics": "OAK", "Seattle Mariners": "SEA", 
    "Texas Rangers": "TEX", "Atlanta Braves": "ATL", "Miami Marlins": "MIA", 
    "New York Mets": "NYM", "Philadelphia Phillies": "PHI", "Washington Nationals": "WSN", 
    "Chicago Cubs": "CHC", "Cincinnati Reds": "CIN", "Milwaukee Brewers": "MIL", 
    "Pittsburgh Pirates": "PIT", "St. Louis Cardinals": "STL", "Arizona Diamondbacks": "ARI", 
    "Colorado Rockies": "COL", "Los Angeles Dodgers": "LAD", "San Diego Padres": "SDP", 
    "San Francisco Giants": "SFG"
}

# ========================= ENGINES =========================

def fetch_metrics():
    try:
        pit = pyb.pitching_stats(2025, qual=0)[['Team', 'FIP', 'K%', 'WHIP']]
        bat = pyb.batting_stats(2025, qual=0)[['Team', 'wOBA', 'K%']]
        return bat.groupby('Team').mean().to_dict('index'), pit.groupby('Team').mean().to_dict('index')
    except Exception as e:
        print(f"Stat Fetch Error: {e}")
        return None, None

def get_weather_impact(team_code, avg_k_pct):
    stadium = STADIUM_DATA.get(team_code, {"roof": "retractable", "factor": 1.0})
    if stadium['roof'] != 'open': return INDOOR_FLOOR, "Indoor"
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={stadium['lat']}&lon={stadium['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        t, w, deg = r['main']['temp'], r['wind']['speed'], r['wind'].get('deg', 0)
        is_blowing_out = 180 <= deg <= 270 
        wind_mod = (0.012 if is_blowing_out else -0.010)
        
        if avg_k_pct > 0.26:
            wind_mod *= 0.65 
            
        mult = (1 + (t - 70) * 0.0035) * (1 + w * wind_mod)
        desc = f"{int(t)}°F {int(w)}mph {'OUT' if is_blowing_out else 'IN/CROSS'}"
        return round(mult, 3), desc
    except: return 1.0, "Weather N/A"

def get_daily_pitchers():
    date_str = datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher"
    starters = {}
    try:
        data = requests.get(url).json()
        for date in data.get('dates', []):
            for game in date.get('games', []):
                for side in ['away', 'home']:
                    team_name = game['teams'][side]['team']['name']
                    team_code = TEAM_MAP.get(team_name)
                    pitcher = game['teams'][side].get('probablePitcher', {})
                    if team_code and pitcher:
                        p_id = pitcher.get('id')
                        p_info = requests.get(f"https://statsapi.mlb.com/api/v1/people/{p_id}").json()['people'][0]
                        hand = p_info.get('pitchHand', {}).get('code', 'R')
                        is_rookie = p_info.get('mlbDebutDate', '2000') > '2025-01-01'
                        starters[team_code] = {"hand": hand, "rookie": is_rookie, "id": p_id}
        return starters
    except: return {}

# ========================= MAIN EXECUTION =========================

def main():
    bat_stats, pit_stats = fetch_metrics()
    daily_pitchers = get_daily_pitchers()
    is_sunday = datetime.now().weekday() == 6
    if not bat_stats: return

    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "h2h,totals", "oddsFormat": "american"}
    response = requests.get(f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds", params=params)
    data = response.json()

    if not isinstance(data, list): return

    report = f"⚾ <b>MLB OMNI-REPORT v12.1: {datetime.now().strftime('%b %d')}</b>\n"
    report += f"<i>Logic: Dynamic NRFI + ABS Stability</i>\n\n"

    for game in data:
        try:
            h_f, a_f = game['home_team'], game['away_team']
            h_k, a_k = TEAM_MAP.get(h_f), TEAM_MAP.get(a_f)
            if not h_k or not a_k: continue

            h_p, a_p = pit_stats.get(h_k, {'FIP': 4.1, 'K%': .22}), pit_stats.get(a_k, {'FIP': 4.1, 'K%': .22})
            avg_k_pot = (h_p['K%'] + a_p['K%']) / 2
            
            w_mult, w_desc = get_weather_impact(h_k, avg_k_pot)
            park_info = STADIUM_DATA.get(h_k, {"factor": 1.0})
            park_factor = park_info['factor']
            
            h_ctx = daily_pitchers.get(h_k, {"hand": "R", "rookie": False})
            a_ctx = daily_pitchers.get(a_k, {"hand": "R", "rookie": False})
            h_b, a_b = bat_stats.get(h_k, {'wOBA': .31, 'K%': .22}), bat_stats.get(a_k, {'wOBA': .31, 'K%': .22})

            proj_base = (((h_p['FIP'] + a_p['FIP'])/2)*0.85 + (h_b['wOBA'] + a_b['wOBA'])*10.5) * \
                        w_mult * park_factor * BULLPEN_TAX * ABS_INFLATION
            
            if h_k in POWER_TEAMS: proj_base += (0.5 + (PLATOON_PENALTY if a_ctx['hand'] == "L" else 0))
            if a_k in POWER_TEAMS: proj_base += (0.5 + (PLATOON_PENALTY if h_ctx['hand'] == "L" else 0))
            
            h_tax = EXPERIENCE_TAX if h_ctx['rookie'] and h_p['K%'] < 0.25 else (EXPERIENCE_TAX / 2) if h_ctx['rookie'] else 0
            a_tax = EXPERIENCE_TAX if a_ctx['rookie'] and a_p['K%'] < 0.25 else (EXPERIENCE_TAX / 2) if a_ctx['rookie'] else 0
            proj_base += (h_tax + a_tax)
            
            if is_sunday: proj_base += SUNDAY_LINEUP_TAX

            proj_full = round(proj_base, 1)
            proj_f5 = round(proj_base * 0.52, 1)

            # --- v12.1 DYNAMIC NRFI LOGIC ---
            nrfi_score = avg_k_pot - (park_factor * 0.15)
            if nrfi_score > 0.08:
                nrfi = "STRONG"
            elif nrfi_score < 0.02:
                nrfi = "WEAK (YRIF)"
            else:
                nrfi = "NEUTRAL"

            ml_lean = h_f if h_p['FIP'] < a_p['FIP'] - 0.4 else a_f if a_p['FIP'] < h_p['FIP'] - 0.4 else "TOSS-UP"
            f5_ml_lean = h_f if h_p['FIP'] < a_p['FIP'] else a_f

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

            report += f"<b>{a_f} @ {h_f}</b>\n"
            report += f"🌡️ {w_desc} | Proj: {proj_full} (F5: {proj_f5})\n"
            report += f"📈 ML: {ml_lean} | F5 ML: {f5_ml_lean}\n"
            report += f"🎯 NRFI: {nrfi} | Total: {total_action} | F5: {f5_action}\n\n"

        except Exception as e:
            continue

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "HTML"})

if __name__ == "__main__":
    main()
