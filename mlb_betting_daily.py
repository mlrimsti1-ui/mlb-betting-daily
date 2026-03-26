import requests
from datetime import datetime
import pybaseball as pyb

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"      # GitHub secret
TELEGRAM_CHAT_ID = "8779455773"      # GitHub secret
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"     # GitHub secret

CURRENT_SEASON = datetime.now().year

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
        # Get season batting and pitching stats
        batting = pyb.batting_stats(CURRENT_SEASON, CURRENT_SEASON)
        pitching = pyb.pitching_stats(CURRENT_SEASON, CURRENT_SEASON)
        
        # Aggregate to team level (simple mean for OPS and ERA)
        batting_team = batting.groupby('Team')['OPS'].mean().to_dict()
        pitching_team = pitching.groupby('Team')['ERA'].mean().to_dict()
        
        return batting_team, pitching_team
    except Exception as e:
        print(f"⚠️ pybaseball error: {e}")
        return {}, {}

# ========================= SIMPLE BETTING ALGORITHM =========================
def run_mlb_betting_algorithm():
    report = f"⚾ MLB Betting Report – {datetime.now().strftime('%B %d, %Y')} (Chicago time)\n\n"
    
    # Fetch data
    games = fetch_odds_api()
    batting_team, pitching_team = fetch_pybaseball_team_stats()

    if not games:
        report += "⚠️ No games found or Odds API issue today.\n"
        return report

    report += f"📊 {len(games)} games today\n\n"

    for game in games[:12]:  # Limit report length
        home = game.get('home_team', 'N/A')
        away = game.get('away_team', 'N/A')
        commence = game.get('commence_time', '')[:16]

        # Get stats (fallback to league average if team not found)
        h_era = pitching_team.get(home, 4.50)
        a_era = pitching_team.get(away, 4.50)
        h_ops = batting_team.get(home, 0.720)
        a_ops = batting_team.get(away, 0.720)

        # Core Algorithm: Pitching + Hitting + Environment (basic home advantage)
        projected_total = round(((h_era + a_era) / 2) * 0.9 + (h_ops + a_ops) * 4.5, 1)
        
        home_win_prob = 0.5 + (a_era - h_era) * 0.12 + (h_ops - a_ops) * 0.65 + 0.04  # +4% home edge
        home_win_prob = max(0.05, min(0.95, home_win_prob))

        # Parse odds from first bookmaker
        ml_home = ml_away = total_line = None
        book = game.get('bookmakers', [{}])[0]
        for market in book.get('markets', []):
            if market

