import requests
import json
from datetime import datetime

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8216569304:AAFrWNUFtDFeUwS4TylFULp_ZkEvNakd8b8"      # from Step 2
TELEGRAM_CHAT_ID = "8779455773"      # from Step 2
ODDS_API_KEY = "4bdba5b98d90cc609eeadf39b1c0be2d"     # from Step 3 (optional but recommended)

# Your own algorithm goes here — replace this whole function
def run_your_mlb_betting_algorithm():
    report = f"🧢 MLB Betting Report – {datetime.now().strftime('%B %d, %Y')}\n\n"
    
    # Example 1: Fetch today's MLB odds (clean & reliable)
    try:
        url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",          # or "us,eu" etc.
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american"
        }
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        
        report += "Today's Games & Odds:\n"
        for game in data[:10]:  # limit to first 10 for report length
            home = game['home_team']
            away = game['away_team']
            start = game['commence_time'][:16]
            odds = game['bookmakers'][0]['markets'][0]['outcomes'] if game.get('bookmakers') else "N/A"
            report += f"• {away} @ {home} | {start} | {odds}\n"
    except Exception as e:
        report += f"⚠️ Odds fetch failed: {e}\n"
    
    # Example 2: Add your own web-scraping here (Fangraphs, Baseball-Reference, etc.)
    # Example scraping Fangraphs projected standings (or any table you want):
    # try:
    #     resp = requests.get("https://fangraphs.com/standings/projections")
    #     # parse with BeautifulSoup if you want more data
    # except: pass
    
    # ===================== YOUR ALGORITHM GOES HERE =====================
    # Example: simple "value bet" logic
    # value_bets = []
    # for game in data:
    #     if your_edge_calculation(game) > 5:   # your custom logic
    #         value_bets.append(...)
    # report += f"\n🔥 Value Bets Today:\n{value_bets}\n"
    
    report += "\n✅ Script completed. Good luck today! ⚾"
    return report

# ========================= SEND TO TELEGRAM =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

# ========================= MAIN =========================
if __name__ == "__main__":
    report = run_your_mlb_betting_algorithm()
    send_telegram(report)
    print("✅ Daily MLB report sent!")
