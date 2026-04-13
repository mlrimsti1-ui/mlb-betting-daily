import os
import requests
import pandas as pd
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG & KEYS =========================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

# Final verification logs
print(f"DEBUG: Odds API Key present: {bool(ODDS_API_KEY)}")
print(f"DEBUG: Telegram Token present: {bool(TELEGRAM_TOKEN)}")

# Model Constants
BULLPEN_TAX = 1.08         
ABS_INFLATION = 1.02       
INDOOR_FLOOR = 1.03
POWER_TEAMS = ["LAD", "ATL", "NYY"]

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

def fetch_metrics():
    # Attempting to go back as far as 2024 if 2026/2025 isn't ready
    for year in [2026, 2025, 2024]:
        try:
            print(f"Attempting Statcast fetch for {year}...")
            b_func = getattr(pyb, 'statcast_batter_exit_velocity_barrels', None)
            p_func = getattr(pyb, 'statcast_pitcher_exit_velocity_barrels', None)
            if b_func and p_func:
                bat_raw = b_func(year)
                pit_raw = p_func(year)
                if bat_raw is not None and not bat_raw.empty:
                    bat_df = bat_raw[['team', 'woba']].copy()
                    bat_df.columns = ['Team', 'wOBA']
                    pit_df = pit_raw[['team', 'fip', 'k_percent']].copy()
                    pit_df.columns = ['Team', 'FIP', 'K%']
                    pit_df['K%'] = pit_df['K%'] / 100
                    return bat_df.groupby('Team').mean().to_dict('index'), pit_df.groupby('Team').mean().to_dict('index')
        except: continue
    return None, None

def get_weather_impact(team_code, avg_k_pct):
    if not WEATHER_API_KEY: return 1.0, "No Key"
    stadium = STADIUM_DATA.get(team_code, {"roof": "retractable", "factor": 1.0})
    if stadium['roof'] != 'open': return INDOOR_FLOOR, "Indoor"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={stadium['lat']}&lon={stadium['lon']}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        r = requests.get(url, timeout=5).json()
        t, w, deg = r['main']['temp'], r['wind']['speed'], r['wind'].get('deg', 0)
        is_blowing_out = 180 <= deg <= 270 
        wind_mod = (0.012 if is_blowing_out else -0.010)
        mult = (1 + (t - 70) * 0.0035) * (1 + w * wind_mod)
        return round(mult, 3), f"{int(t)}°F {int(w)}mph"
    except: return 1.0, "Weather N/A"

def main():
    bat_stats, pit_stats = fetch_metrics()
    
    if not bat_stats: 
        print("Using generic metrics fallback.")
        bat_stats = {k: {'wOBA': 0.315} for k in TEAM_MAP.values()}
        pit_stats = {k: {'FIP': 4.20, 'K%': 0.22} for k in TEAM_MAP.values()}

    if not ODDS_API_KEY:
        print("CRITICAL: ODDS_API_KEY is missing.")
        return

    try:
        params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "h2h,totals", "oddsFormat": "american"}
        response = requests.get(f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds", params=params)
        data = response.json()
    except: return

    if not isinstance(data, list): 
        print(f"Error: {data}")
        return

    report = f"⚾ <b>MLB OMNI-REPORT v12.7: {datetime.now().strftime('%b %d')}</b>\n\n"
    game_count = 0
    for game in data:
        try:
            h_f, a_f = game['home_team'], game['away_team']
            h_k, a_k = TEAM_MAP.get(h_f), TEAM_MAP.get(a_f)
            if not h_k or not a_k: continue

            h_p, a_p = pit_stats.get(h_k, {'FIP': 4.1, 'K%': .22}), pit_stats.get(a_k, {'FIP': 4.1, 'K%': .22})
            w_mult, w_desc = get_weather_impact(h_k, (h_p['K%'] + a_p['K%']) / 2)
            park = STADIUM_DATA.get(h_k, {"factor": 1.0})['factor']
            
            h_b, a_b = bat_stats.get(h_k, {'wOBA': .31}), bat_stats.get(a_k, {'wOBA': .31})
            proj = (((h_p['FIP'] + a_p['FIP'])/2)*0.85 + (h_b['wOBA'] + a_b['wOBA'])*10.5) * w_mult * park * BULLPEN_TAX * ABS_INFLATION
            
            if h_k in POWER_TEAMS or a_k in POWER_TEAMS: proj += 0.5

            report += f"<b>{a_f} @ {h_f}</b>\n🌡️ {w_desc} | Proj: {round(proj, 1)}\n\n"
            game_count += 1
        except: continue

    if game_count > 0 and TELEGRAM_TOKEN:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "HTML"})
        print("Success.")

if __name__ == "__main__":
    main()
