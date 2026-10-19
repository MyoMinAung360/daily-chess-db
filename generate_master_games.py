import os
import json
import time
import requests
import chess.pgn
import io
import datetime

OUTPUT_DIR = "daily_games"
DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
HISTORY_FILE = os.path.join(OUTPUT_DIR, "seen_games.json")

# 🌟 သဘောတူညီချက် သတ်မှတ်ချက်များ 🌟
TARGET_GAMES = 100           # တစ်ရက်လျှင် စုစုပေါင်း ရရှိလိုသော ပွဲစဉ် အရေအတွက်
MAX_GAMES_PER_PLAYER = 3    # ကစားသမား ၁ ဦးလျှင် အများဆုံး ယူမည့် ပွဲစဉ် အရေအတွက်
MAX_HISTORY = 5000          # မှတ်တမ်းအဟောင်း ထိန်းသိမ်းမည့် ကန့်သတ်ချက်

def ensure_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def load_history():
    """ယခင်ဆွဲယူပြီးသား ပွဲစဉ် ID များကို ပြန်ဖတ်မည်"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            return []
    return []

def save_history(history_list):
    """ယခုအသစ်ရလာသော ပွဲစဉ် ID များကို မှတ်တမ်းထဲ ပြန်ထည့်မည် (Atomic operation အနေဖြင့် ဖိုင်ရေးပြီးမှ ခေါ်မည်)"""
    if len(history_list) > MAX_HISTORY:
        history_list = history_list[-MAX_HISTORY:]
        
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history_list, f, indent=2)

def load_versions():
    version_file = os.path.join(OUTPUT_DIR, "versions.json")
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {day: 0 for day in DAYS}

def save_versions(versions):
    version_file = os.path.join(OUTPUT_DIR, "versions.json")
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(versions, f, indent=4)

def fetch_top_players(headers, limit=100):
    """Lichess Leaderboard မှ ထိပ်တန်း ကစားသမားစာရင်းကို Dynamic Fetch လုပ်မည်"""
    print("🏆 Lichess Top Leaderboard ကစားသမားစာရင်းကို ရယူနေပါသည်...")
    url = f"https://lichess.org/api/player/top/{limit}/classical" # Classical/Blitz/Rapid ကြိုက်ရာ ပြောင်းနိုင်ပါသည်
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            users = [player['username'] for player in data.get('users', [])]
            print(f"✅ ထိပ်တန်း ကစားသမား {len(users)} ဦး စာရင်း ရရှိပါပြီ။\n")
            return users
        else:
            print(f"⚠️ Leaderboard ရယူ၍ မရပါ (Status: {response.status_code})။ Default စာရင်းဖြင့် ဆက်လက်လုပ်ဆောင်ပါမည်။")
    except Exception as e:
        print(f"❌ Leaderboard Fetch Error: {e}")
    
    # API တက်မလာပါက အရန်အသုံးပြုရန် GM စာရင်း
    return ['DrNykterstein', 'Hikaru', 'AlirezaFirouzja', 'DanielNaroditsky', 'nihalsarin2004']

def fetch_new_games():
    new_games = []
    history_list = load_history()
    seen_set = set(history_list)
    
    lichess_token = os.environ.get("LICHESS_TOKEN")
    headers = {
        'User-Agent': 'DailyChessApp/1.0 (https://github.com/MyoMinAung360/daily-chess-db)',
        'Accept': 'application/x-chess-pgn'
    }
    if lichess_token:
        headers['Authorization'] = f'Bearer {lichess_token}'

    # Top Players စာရင်းကို ရယူခြင်း
    top_players = fetch_top_players(headers, limit=100)

    print("🚀 Lichess မှ Master Games အသစ်များကို စတင်ရှာဖွေနေပါသည်...\n")

    for player in top_players:
        if len(new_games) >= TARGET_GAMES:
            print(f"🎯 သတ်မှတ်ထားသော Target Quota ({TARGET_GAMES} ပွဲ) ပြည့်သွားပါပြီ။")
            break

        print(f"⏳ {player} ၏ နောက်ဆုံးပွဲစဉ်များကို စစ်ဆေးနေသည်...")
        # ကစားသမားတစ်ဦးစီထံမှ Recent Games အနည်းငယ် ရယူမည်
        url = f"https://lichess.org/api/games/user/{player}?max=10"
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                pgn_io = io.StringIO(response.text)
                player_added_count = 0
                
                while True:
                    if player_added_count >= MAX_GAMES_PER_PLAYER or len(new_games) >= TARGET_GAMES:
                        break

                    game = chess.pgn.read_game(pgn_io)
                    if game is None:
                        break 
                    
                    game_id = game.headers.get("Site", "")
                    
                    # ရွှေ့ကွက်မပါခြင်း သို့မဟုတ် ယခင်က ယူပြီးသားပွဲဖြစ်နေလျှင် ကျော်သွားမည်
                    if (not game.mainline_moves()) or (game_id in seen_set) or (game_id == ""):
                        continue

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
                    
                    new_games.append(game_data)
                    seen_set.add(game_id)
                    history_list.append(game_id)
                    
                    player_added_count += 1
                    
            else:
                print(f"❌ {player} အတွက် ဆွဲယူမှု မအောင်မြင်ပါ။ (Code: {response.status_code})")
                
        except Exception as e:
            print(f"❌ Error for {player}: {e}")
            
        time.sleep(1.5) # Rate Limit ကာကွယ်ရန်

    return new_games, history_list

def update_today_file(new_games, history_list):
    if not new_games:
        print("\n✅ ယနေ့အတွက် ပွဲအသစ် မရှိသေးပါ။ (အားလုံး ယူပြီးသားများဖြစ်နေပါသည်)")
        return

    today_str = datetime.datetime.now().strftime("%A").lower()
    if today_str not in DAYS:
        today_str = "monday"

    print(f"\n🎉 ပွဲအသစ် စုစုပေါင်း {len(new_games)} ပွဲ ရရှိပါသည်။ '{today_str}.json' သို့ Update လုပ်ပါမည်။")

    # ၁။ ပွဲစဉ်အသစ်များကို JSON ဖိုင်ထဲသို့ ရေးသားခြင်း
    out_path = os.path.join(OUTPUT_DIR, f"{today_str}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(new_games, f, ensure_ascii=False, indent=2)

    # ၂။ Version နံပါတ် အပ်ဒိတ်လုပ်ခြင်း
    versions = load_versions()
    versions[today_str] += 1
    save_versions(versions)

    # ၃။ Atomic Operation: ဖိုင် ရေးသားပြီးမြောက်မှသာ seen_games.json ကို သိမ်းဆည်းမည်
    save_history(history_list)
    
    print(f"✅ {today_str}.json ကို Version {versions[today_str]} ဖြင့် အောင်မြင်စွာ Update ပြုလုပ်ပြီးပါပြီ!")

if __name__ == "__main__":
    ensure_directories()
    new_master_games, updated_history = fetch_new_games()
    update_today_file(new_master_games, updated_history)
