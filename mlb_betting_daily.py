import requests
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"      # GitHub secret
TELEGRAM_CHAT_ID = "8779455773"      # GitHub secret
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"     # GitHub secret

CURRENT_SEASON = datetime.now().year

# Simple team name mapping (Odds API full name → pybaseball-friendly key)
TEAM_MAP = {
    "New York Yankees": "NYY",
    "Boston Red Sox": "BOS",
    "Toronto Blue Jays": "TOR",
    "Baltimore Orioles": "BAL",
    "Tampa Bay Rays": "TBR",
    "Chicago White Sox": "CWS",
    "Cleveland Guardians": "CLE",
    "Detroit Tigers": "DET",
    "Kansas City Royals": "KCR",
    "Minnesota Twins": "MIN",
    "Houston Astros": "HOU",
    "Los Angeles Angels": "LAA",
    "Oakland Athletics": "OAK",
    "Seattle Mariners": "SEA",
    "Texas Rangers": "TEX",
    "Atlanta Braves": "ATL",
    "Miami Marlins": "MIA",
    "New York Mets": "NYM",
    "Philadelphia Phillies": "PHI",
    "Washington Nationals": "WSN",
    "Chicago Cubs": "CHC",
    "Cincinnati Reds": "CIN",
    "Milwaukee Brewers": "MIL",
    "Pittsburgh Pirates": "PIT",
    "St. Louis Cardinals": "STL",
    "Arizona Diamondbacks": "ARI",
    "Colorado Rockies": "COL",
    "Los Angeles Dodgers": "LAD",
    "San Diego Padres": "SDP",
    "San Francisco Giants": "SFG"
}

# ========================= FETCH DATA =========================
def fetch_odds_api():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"⚠️ Odds API error: {e}")
        return []

def fetch_pybaseball_team_stats():
    try:
        batting = pyb.batting_stats(CURRENT_SEASON, CURRENT_SEASON)
        pitching = pyb.pitching_stats(CURRENT_SEASON, CURRENT_SEASON)
        
        batting_team = batting.groupby('Team')['OPS'].mean().to_dict()
        pitching_team = pitching.groupby('Team')['ERA'].mean().to_dict()
        
        return batting_team, pitching_team
    except Exception as e:
        print(f"⚠️ pybaseball error: {e}")
        return {}, {}

# ========================= MAIN ALGORITHM =========================
def run_mlb_betting_algorithm():
    report = f"⚾ MLB Betting Report – {datetime.now().strftime('%B %d, %Y')} (Chicago time)\n\n"
    
    games = fetch_odds_api()
    batting_team, pitching_team = fetch_pybaseball_team_stats()

    if not games:
        report += "⚠️ No games found or Odds API issue today.\n"
        return report

    report += f"📊 {len(games)} games today\n\n"

    for game in games[:12]:
        home_full = game.get('home_team', 'N/A')
        away_full = game.get('away_team', 'N/A')
        commence = game.get('commence_time', '')[:16]

        # Map to pybaseball keys
        home_key = TEAM_MAP.get(home_full, home_full)
        away_key = TEAM_MAP.get(away_full, away_full)

        h_era = pitching_team.get(home_key, 4.50)
        a_era = pitching_team.get(away_key, 4.50)
        h_ops = batting_team.get(home_key, 0.720)
        a_ops = batting_team.get(away_key, 0.720)

        # Core logic: Pitching + Hitting + Environment (home advantage)
        projected_total = round(((h_era + a_era) / 2) * 0.9 + (h_ops + a_ops) * 4.5, 1)
        
        home_win_prob = 0.5 + (a_era - h_era) * 0.12 + (h_ops - a_ops) * 0.65 + 0.04
        home_win_prob = max(0.05, min(0.95, home_win_prob))

        # Parse odds
        ml_home = ml_away = total_line = None
        book = game.get('bookmakers', [{}])[0]
        for market in book.get('markets', []):
            if market.get('key') == 'h2h' and market.get('outcomes'):
                outcomes = market['outcomes']
                if len(outcomes) > 0:
                    ml_home = outcomes[0].get('price')
                if len(outcomes) > 1:
                    ml_away = outcomes[1].get('price')
            elif market.get('key') == 'totals' and market.get('outcomes'):
                total_line = market['outcomes'][0].get('point')

        # Value bets (5%+ edge)
        value_bets = []
        if ml_home:
            implied_prob = (100 / abs(ml_home)) if ml_home < 0 else (abs(ml_home) / (abs(ml_home) + 100))
            edge = (home_win_prob - implied_prob) * 100
            if edge > 5:
                value_bets.append(f"✅ ML: Bet {home_full} ({ml_home}) — +{edge:.1f}% edge")
        
        if total_line:
            ou_recommend = "OVER" if projected_total > total_line + 0.3 else "UNDER" if projected_total < total_line - 0.3 else None
            if ou_recommend:
                value_bets.append(f"✅ O/U {total_line}: {ou_recommend} (proj {projected_total})")

        # Output
        report += f"**{away_full} @ {home_full}** — {commence}\n"
        report += f"   Pitching: {home_full} ERA≈{h_era:.2f} | {away_full} ERA≈{a_era:.2f}\n"
        report += f"   Hitting:  {home_full} OPS≈{h_ops:.3f} | {away_full} OPS≈{a_ops:.3f}\n"
        report += f"   Proj Total: {projected_total} runs | Home win ≈{home_win_prob:.1%}\n"
        
        if value_bets:
            report += "   🔥 Value bets:\n" + "\n".join([f"      {v}" for v in value_bets]) + "\n"
        else:
            report += "   No strong value detected\n"
        report += "\n"

    report += "📌 Algorithm: Pitching (ERA) + Hitting (OPS) + Environment (home advantage)\n"
    report += "✅ Powered by The Odds API + pybaseball. Bet responsibly! ⚾"
    return report

# ========================= SEND TO TELEGRAM =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")

# ========================= MAIN =========================
if __name__ == "__main__":
    try:
        report = run_mlb_betting_algorithm()
    except Exception as e:
        import traceback
        error_msg = f"⚠️ Script crashed!\nError: {type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        report = f"MLB Betting Report – {datetime.now().strftime('%B %d, %Y')}\n\n{error_msg}"
        print(error_msg)
    
    send_telegram(report)
    print("✅ Daily MLB script finished")
