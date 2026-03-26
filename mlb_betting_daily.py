import requests
import json
from datetime import datetime, date
import pybaseball as pyb
import pandas as pd

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"          # ← GitHub secret
TELEGRAM_CHAT_ID = "8779455773"          # ← GitHub secret
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"         # ← GitHub secret

CURRENT_SEASON = datetime.now().year
TODAY = date.today().isoformat()

# ========================= FETCH DATA =========================
def fetch_odds_api():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        return []
    return r.json()

def fetch_pybaseball_stats():
    try:
        batting = pyb.batting_stats(CURRENT_SEASON, CURRENT_SEASON)
        pitching = pyb.pitching_stats(CURRENT_SEASON, CURRENT_SEASON)
        # Team-level averages (simple aggregation)
        batting_team = batting.groupby('Team').agg({'OPS': 'mean', 'wOBA': 'mean'}).to_dict()
        pitching_team = pitching.groupby('Team').agg({'ERA': 'mean', 'FIP': 'mean'}).to_dict()
        return batting_team, pitching_team
    except:
        return {}, {}

def fetch_sportsdata_team_stats():
    if not SPORTS_DATA_API_KEY or SPORTS_DATA_API_KEY == "YOUR_SPORTS_DATA_KEY_HERE":
        return None
    try:
        url = f"https://api.sportsdata.io/v3/mlb/scores/json/TeamSeasonStats/{CURRENT_SEASON}?key={SPORTS_DATA_API_KEY}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            df = pd.DataFrame(r.json())
            return {
                row['Name']: {
                    'era': row.get('EarnedRunAverage', 4.5),
                    'ops': row.get('BattingOPS', 0.72)
                } for _, row in df.iterrows()
            }
    except:
        pass
    return None

# ========================= SIMPLE BETTING ALGORITHM =========================
def run_mlb_betting_algorithm():
    report = f"⚾ MLB Betting Report – {datetime.now().strftime('%B %d, %Y')} (Chicago time)\n\n"
    
    # 1. Get today's odds + games
    games = fetch_odds_api()
    if not games:
        report += "⚠️ No games or API error today.\n"
        return report

    # 2. Get pitching & hitting stats
    batting_team, pitching_team = fetch_pybaseball_stats()
    sportsdata_stats = fetch_sportsdata_team_stats()

    report += f"📊 {len(games)} games today\n\n"

    for game in games[:12]:  # limit report length
        home = game.get('home_team', 'N/A')
        away = game.get('away_team', 'N/A')
        commence = game.get('commence_time', '')[:16]

        # Get stats (prefer SportsData.io if available, else pybaseball)
        if sportsdata_stats and home in sportsdata_stats:
            h_era = sportsdata_stats[home]['era']
            h_ops = sportsdata_stats[home]['ops']
            a_era = sportsdata_stats.get(away, {'era': 4.5})['era']
            a_ops = sportsdata_stats.get(away, {'ops': 0.72})['ops']
        else:
            h_era = pitching_team.get('ERA', {}).get(home, 4.5)
            a_era = pitching_team.get('ERA', {}).get(away, 4.5)
            h_ops = batting_team.get('OPS', {}).get(home, 0.72)
            a_ops = batting_team.get('OPS', {}).get(away, 0.72)

        # === CORE ALGORITHM: Pitching + Hitting + Environment ===
        # Simple projected total runs (you can make this much smarter)
        projected_total = round(((h_era + a_era) / 2) * 0.9 + (h_ops + a_ops) * 4.5, 1)
        
        # Simple home win probability (adjust coefficients as you like)
        home_win_prob = 0.5 + (a_era - h_era) * 0.12 + (h_ops - a_ops) * 0.65 + 0.04  # +4% home advantage (environment)
        home_win_prob = max(0.05, min(0.95, home_win_prob))

        # === PARSE ODDS (first bookmaker for simplicity) ===
        ml_home = ml_away = spread_home = total_line = None
        book = game.get('bookmakers', [{}])[0]
        for market in book.get('markets', []):
            if market['key'] == 'h2h':
                outcomes = market['outcomes']
                ml_home = outcomes[0].get('price') if outcomes else None
                ml_away = outcomes[1].get('price') if len(outcomes) > 1 else None
            elif market['key'] == 'spreads':
                outcomes = market['outcomes']
                spread_home = outcomes[0].get('price') if outcomes else None
            elif market['key'] == 'totals':
                outcomes = market['outcomes']
                total_line = outcomes[0].get('point') if outcomes else None

        # === VALUE DETECTION (5%+ edge) ===
        value_bets = []
        
        # Moneyline value
        if ml_home:
            implied_prob = (100 / abs(ml_home)) if ml_home < 0 else (abs(ml_home) / (abs(ml_home) + 100))
            edge = (home_win_prob - implied_prob) * 100
            if edge > 5:
                value_bets.append(f"✅ ML: {home} ({ml_home}) — +{edge:.1f}% edge")
        
        # Over/Under value
        if total_line:
            ou_recommend = "OVER" if projected_total > total_line + 0.3 else "UNDER" if projected_total < total_line - 0.3 else "EVEN"
            if ou_recommend != "EVEN":
                value_bets.append(f"✅ O/U {total_line}: {ou_recommend} (proj {projected_total})")
        
        # Spread value (simple)
        if spread_home and abs(spread_home) > 100:  # only if odds present
            value_bets.append(f"📈 Spread available for {home}")

        # Game header
        report += f"**{away} @ {home}** — {commence}\n"
        report += f"   Pitching: {home} ERA≈{h_era:.2f} vs {away} ERA≈{a_era:.2f}\n"
        report += f"   Hitting:  {home} OPS≈{h_ops:.3f} vs {away} OPS≈{a_ops:.3f}\n"
        report += f"   Proj Total: {projected_total} runs | Home win ≈{home_win_prob:.1%}\n"
        
        if value_bets:
            report += "   🔥 Value bets:\n" + "\n".join([f"      {v}" for v in value_bets]) + "\n"
        else:
            report += "   No strong value detected\n"
        report += "\n"

    report += "📌 Algorithm uses: Pitching (ERA), Hitting (OPS), Environment (home advantage)\n"
    report += "✅ Script finished. Bet responsibly! ⚾"
    return report

# ========================= SEND TO TELEGRAM =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=10)

# ========================= MAIN =========================
if __name__ == "__main__":
    report = run_mlb_betting_algorithm()
    send_telegram(report)
    print("✅ Daily MLB betting report sent via Telegram!")

