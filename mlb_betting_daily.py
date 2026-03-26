import requests
from datetime import datetime
import pybaseball as pyb
import pandas as pd

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"

# Opening Day Logic: Use 2025 data until April 10th, 2026
CURRENT_DATE = datetime.now()
DATA_YEAR = 2025 if (CURRENT_DATE.month == 3 or (CURRENT_DATE.month == 4 and CURRENT_DATE.day < 10)) else 2026

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

def fetch_odds_api():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "h2h,totals", "oddsFormat": "american"}
    try:
        r = requests.get(url, params=params, timeout=20)
        return r.json()
    except: return []

def fetch_predictive_metrics():
    try:
        # Added qual=0 to ensure data is returned even if no one is "qualified" yet
        batting = pyb.batting_stats(DATA_YEAR, qual=0)
        pitching = pyb.pitching_stats(DATA_YEAR, qual=0)
        
        batting_team = batting.groupby('Team')['wOBA'].mean().to_dict()
        pitching_team = pitching.groupby('Team')['FIP'].mean().to_dict()
        return batting_team, pitching_team
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return {}, {}

def run_mlb_betting_algorithm():
    report = f"⚾ <b>MLB Report</b> – {datetime.now().strftime('%b %d')}\n"
    games = fetch_odds_api()
    batting_team, pitching_team = fetch_predictive_metrics()

    if not games: return "⚠️ Odds API returned no games."

    for game in games:
        home_full, away_full = game.get('home_team'), game.get('away_team')
        home_key, away_key = TEAM_MAP.get(home_full), TEAM_MAP.get(away_full)

        h_fip = pitching_team.get(home_key, 4.25)
        a_fip = pitching_team.get(away_key, 4.25)
        h_woba = batting_team.get(home_key, 0.315)
        a_woba = batting_team.get(away_key, 0.315)

        proj_total = round(((h_fip + a_fip) / 2) * 0.85 + (h_woba + a_woba) * 10, 1)
        home_win_prob = 0.5 + (a_fip - h_fip) * 0.08 + (h_woba - a_woba) * 1.2 + 0.04
        
        ml_home = total_line = None
        bookies = game.get('bookmakers', [])
        if bookies:
            for m in bookies[0].get('markets', []):
                if m['key'] == 'h2h': ml_home = next((o['price'] for o in m['outcomes'] if o['name'] == home_full), None)
                if m['key'] == 'totals': total_line = m['outcomes'][0].get('point')

        # Logic for identifying value
        val = []
        if ml_home and home_win_prob:
            implied = (abs(ml_home)/(abs(ml_home)+100)) if ml_home < 0 else (100/(ml_home+100))
            if (home_win_prob - implied) > 0.05: val.append(f"💰 ML: {home_full}")
        if total_line:
            if proj_total > total_line + 0.7: val.append(f"🔥 OVER {total_line}")
            elif proj_total < total_line - 0.7: val.append(f"🧊 UNDER {total_line}")

        report += f"<b>{away_full} @ {home_full}</b>\nProj: {proj_total} | {' '.join(val) if val else 'No Edge'}\n\n"

    return report

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    response = requests.post(url, json=payload, timeout=10)
    print(f"Telegram Response: {response.status_code} - {response.text}")

if __name__ == "__main__":
    content = run_mlb_betting_algorithm()
    send_telegram(content)
