import requests
from datetime import datetime
import pybaseball as pyb
import pandas as pd
import numpy as np

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"
TELEGRAM_CHAT_ID = "8779455773"
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"

# Use 2025 data for the first 14 days of the 2026 season to ensure accuracy
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
        print(f"⚠️ Odds API error: {e}")
        return []

def fetch_predictive_metrics():
    """
    Fetches FIP (Predictive Pitching) and wOBA (Predictive Hitting)
    """
    try:
        # Pulling season-level stats for the designated DATA_YEAR
        batting = pyb.batting_stats(DATA_YEAR)
        pitching = pyb.pitching_stats(DATA_YEAR)
        
        # Mapping metrics to teams
        # wOBA (Weighted On-Base Average) is the gold standard for offense
        batting_team = batting.groupby('Team')['wOBA'].mean().to_dict()
        
        # FIP (Fielding Independent Pitching) isolates pitcher skill from defense/luck
        pitching_team = pitching.groupby('Team')['FIP'].mean().to_dict()
        
        return batting_team, pitching_team
    except Exception as e:
        print(f"⚠️ pybaseball error: {e}")
        return {}, {}

# ========================= MAIN ALGORITHM =========================
def run_mlb_betting_algorithm():
    report = f"⚾ <b>MLB Pro-Model Report</b> – {datetime.now().strftime('%B %d, %Y')}\n"
    report += f"<i>Using {DATA_YEAR} baseline data for Opening Week accuracy</i>\n\n"
    
    games = fetch_odds_api()
    batting_team, pitching_team = fetch_predictive_metrics()

    if not games:
        return "⚠️ No games found or API error."

    for game in games[:15]:  # Process full slate
        home_full = game.get('home_team')
        away_full = game.get('away_team')
        home_key = TEAM_MAP.get(home_full, home_full)
        away_key = TEAM_MAP.get(away_full, away_full)

        # Get Predictive Stats (Defaults to league average if missing)
        h_fip = pitching_team.get(home_key, 4.20)
        a_fip = pitching_team.get(away_key, 4.20)
        h_woba = batting_team.get(home_key, 0.320)
        a_woba = batting_team.get(away_key, 0.320)

        # --- ALGORITHM LOGIC ---
        # 1. Projected Total: Weighted FIP + wOBA scale
        projected_total = round(((h_fip + a_fip) / 2) * 0.85 + (h_woba + a_woba) * 10, 1)
        
        # 2. Win Probability: FIP delta + wOBA delta + Home Field Advantage (4%)
        home_win_prob = 0.5 + (a_fip - h_fip) * 0.08 + (h_woba - a_woba) * 1.2 + 0.04
        home_win_prob = max(0.05, min(0.95, home_win_prob))

        # Parse Bookie Odds
        ml_home = ml_away = total_line = None
        bookmakers = game.get('bookmakers', [])
        if bookmakers:
            markets = bookmakers[0].get('markets', [])
            for m in markets:
                if m['key'] == 'h2h':
                    for outcome in m['outcomes']:
                        if outcome['name'] == home_full: ml_home = outcome['price']
                        else: ml_away = outcome['price']
                elif m['key'] == 'totals':
                    total_line = m['outcomes'][0].get('point')

        # --- VALUE DETECTION ---
        value_bets = []
        if ml_home:
            # Calculate Implied Probability from American Odds
            implied = (abs(ml_home) / (abs(ml_home) + 100)) if ml_home < 0 else (100 / (ml_home + 100))
            edge = (home_win_prob - implied) * 100
            if edge > 5:
                value_bets.append(f"💰 <b>ML: {home_full}</b> ({ml_home}) | Edge: +{edge:.1f}%")

        if total_line:
            diff = projected_total - total_line
            if diff > 0.6:
                value_bets.append(f"🔥 <b>OVER {total_line}</b> (Proj: {projected_total})")
            elif diff < -0.6:
                value_bets.append(f"🧊 <b>UNDER {total_line}</b> (Proj: {projected_total})")

        # --- FORMAT REPORT ---
        report += f"<b>{away_full} @ {home_full}</b>\n"
        report += f"Proj: {projected_total} runs | Home Win: {home_win_prob:.1%}\n"
        if value_bets:
            report += "\n".join(value_bets) + "\n"
        else:
            report += "No significant edge detected.\n"
        report += "──────────────
