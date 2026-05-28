import os
import json
import math
import time
import requests
import chess.pgn
import io

OUTPUT_DIR = "daily_games"
DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
HISTORY_FILE = os.path.join(OUTPUT_DIR, "seen_games.json")

GM_ACCOUNTS = [
    'DrNykterstein', 'Hikaru', 'AlirezaFirouzja', 'DanielNaroditsky', 
    'nihalsarin2004', 'GMWSO', 'lachesisQ', 'LevonAronian', 'AnishGiri', 'Duhless'
]
GAMES_PER_PLAYER = 40 # ၇ ရက်စာအတွက်မို့ ပွဲများများဆွဲပါမည်

def ensure_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def setup_all_days():
    all_games = []
    seen_history = set()
    
    print("🚀 ပထမဆုံးအကြိမ် ၇ ရက်စာ Initial Data စတင်ဆွဲယူနေပါသည်...\n")

    for player in GM_ACCOUNTS:
        print(f"⏳ {player} ထံမှ ဆွဲယူနေသည်...")
        url = f"https://lichess.org/api/games/user/{player}?max={GAMES_PER_PLAYER}&perfType=blitz,rapid,classical"
        try:
            response = requests.get(url, headers={'Accept': 'application/x-chess-pgn'})
            if response.status_code == 200:
                pgn_io = io.StringIO(response.text)
                while True:
                    game = chess.pgn.read_game(pgn_io)
                    if game is None: break 
                    
                    game_id = game.headers.get("Site", "")
                    if (not game.mainline_moves()) or (game_id in seen_history): continue

                    game_data = {
                        "white": game.headers.get("White", "Unknown"),
                        "black": game.headers.get("Black", "Unknown"),
                        "whiteElo": game.headers.get("WhiteElo", "0"),
                        "blackElo": game.headers.get("BlackElo", "0"),
                        "event": game.headers.get("Event", "Lichess Game"),
                        "date": game.headers.get("UTCDate", "").replace("-", "."),
                        "eco": game.headers.get("ECO", "A00"),
                        "result": game.headers.get("Result", "*"),
                        "moves": str(game.mainline_moves())
                    }
                    all_games.append(game_data)
                    seen_history.add(game_id)
        except Exception as e:
            print(f"❌ Error: {e}")
        time.sleep(2)

    total_games = len(all_games)
    print(f"\n✅ စုစုပေါင်း ပွဲစဉ်: {total_games} ပွဲ။ ၇ ရက်စာ ခွဲဝေပါမည်။")

    # ၇ ရက်စာ ခွဲဝေခြင်း
    chunk_size = math.ceil(total_games / 7)
    versions = {day: 1 for day in DAYS} # အစပိုင်းမို့ Version အားလုံး 1 ထားမည်
    
    for i, day in enumerate(DAYS):
        day_games = all_games[i * chunk_size : min((i + 1) * chunk_size, total_games)]
        if day_games:
            with open(os.path.join(OUTPUT_DIR, f"{day}.json"), 'w', encoding='utf-8') as f:
                json.dump(day_games, f, ensure_ascii=False, indent=2)
            print(f"📄 {day}.json \t-> {len(day_games)} ပွဲ (Version: 1)")

    # Versions နှင့် History ကို သိမ်းမည်
    with open(os.path.join(OUTPUT_DIR, "versions.json"), 'w') as f:
        json.dump(versions, f, indent=4)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(list(seen_history), f)
        
    print("\n🎉 Initial Setup ပြီးဆုံးပါပြီ။")

if __name__ == "__main__":
    ensure_directories()
    setup_all_days()
