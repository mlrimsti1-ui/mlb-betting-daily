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
    "CHC": {"lat": 41.948, "lon": -87.656, "roof": "open", "factor": 1.05},
    "LAD": {"lat": 34.074, "lon": -118.240, "roof": "open", "factor": 1.02},
    "SEA": {"lat": 47.591, "lon": -122.332, "roof": "retractable", "factor": 0.91}
}

TEAM_MAP = {
    "Pittsburgh Pirates": "PIT", "New York Mets": "NYM", "Chicago Cubs": "CHC", 
    "Arizona Diamondbacks": "ARI", "Los Angeles Dodgers": "LAD", "Seattle Mariners": "SEA",
    "Milwaukee Brewers": "MIL", "Washington Nationals": "WSN", "Minnesota Twins": "MIN",
    "Baltimore Orioles": "BAL", "Detroit Tigers": "DET", "San Diego Padres": "SDP"
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

def get_weather(team_code):
    stadium = STADIUM_DATA.get(team_code, {"roof": "retractable", "factor": 1.0})
    if stadium['roof'] != 'open': return 1.0, "Indoor"
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

    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "h2h,totals", "oddsFormat": "american"}
    response = requests.get(f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds", params=params)
    data = response.json()

    if not isinstance(data, list):
        print(f"API Error: {data.get('message', 'Unknown Error')}")
        return

    report = f"⚾ <b>MLB OMNI-REPORT: {datetime.now().strftime('%b %d')}</b>\n\n"

    for game in data:
        try:
            h_f, a_f = game['home_team'], game['away_team']
            h_k, a_k = TEAM_MAP.get(h_f), TEAM_MAP.get(a_f)
            if not h_k or not a_k: continue

            w_mult, w_desc = get_weather(h_k)
            h_p, a_p = pit_stats.get(h_k, {'FIP': 4.1, 'K%': .22}), pit_stats.get(a_k, {'FIP': 4.1, 'K%': .22})
            h_b, a_b = bat_stats.get(h_k, {'wOBA': .31, 'K%': .22}), bat_stats.get(a_k, {'wOBA': .31, 'K%': .22})

            # 1. Projections
            proj_full = round((((h_p['FIP'] + a_p['FIP'])/2)*0.85 + (h_b['wOBA'] + a_b['wOBA'])*10.5) * w_mult, 1)
            proj_f5 = round(proj_full * 0.52, 1)

            # 2. Moneyline & NRFI
            ml_lean = h_f if h_p['FIP'] < a_p['FIP'] - 0.4 else a_f if a_p['FIP'] < h_p['FIP'] - 0.4 else "TOSS-UP"
            avg_k_pot = (h_p['K%'] + a_p['K%'] + h_b['K%'] + a_b['K%']) / 4
            nrfi = "STRONG" if avg_k_pot > 0.25 and w_mult < 1.0 else "NEUTRAL"

            # 3. Edge Detection (Comparing to Sportsbook)
            total_action = "Neutral"
            f5_action = "Neutral"
            bookies = game.get('bookmakers', [])
            if bookies:
                for market in bookies[0]['markets']:
                    if market['key'] == 'totals':
                        line = market['outcomes'][0]['point']
                        # Full Total Edge
                        if proj_full > line + 0.6: total_action = "Over"
                        elif proj_full < line - 0.6: total_action = "Under"
                        # F5 Total Edge (Line is usually half the full total)
                        if proj_f5 > (line/2) + 0.4: f5_action = "Over"
                        elif proj_f5 < (line/2) - 0.4: f5_action = "Under"

            # 4. Final Formatting
            report += f"<b>{a_f} @ {h_f}</b>\n"
            report += f"🌡️ {w_desc} | Proj: {proj_full} (F5: {proj_f5})\n"
            report += f"📈 ML: {ml_lean} | 🎯 NRFI: {nrfi} | Total: {total_action} | F5: {f5_action}\n\n"

        except Exception as e:
            print(f"Game error: {e}")
            continue

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "HTML"})

if __name__ == "__main__":
    main()
