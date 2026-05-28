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

# 🌟 Lichess Master Accounts 🌟
GM_ACCOUNTS = [
    'DrNykterstein', 'Hikaru', 'AlirezaFirouzja', 'DanielNaroditsky', 
    'nihalsarin2004', 'GMWSO', 'lachesisQ', 'LevonAronian', 'AnishGiri', 'Duhless'
]

GAMES_PER_PLAYER = 15 # နေ့စဉ်ဖြစ်၍ တစ်ဦးလျှင် နောက်ဆုံး ပွဲ ၁၅ ပွဲခန့်သာ စစ်ဆေးလျှင် လုံလောက်ပါသည်

def ensure_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def load_history():
    """ယခင်ဆွဲယူပြီးသား ပွဲစဉ် ID များကို ပြန်ဖတ်မည် (Duplicate မဖြစ်စေရန်)"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_history(history_set):
    """ယခုအသစ်ရလာသော ပွဲစဉ် ID များကို မှတ်တမ်းထဲ ပြန်ထည့်မည်"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(history_set), f)

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

def fetch_new_games():
    new_games = []
    seen_history = load_history()
    updated_history = set(seen_history) # အသစ်တွေကိုပါ ပေါင်းထည့်ရန်
    
    print(f"🚀 Lichess မှ Master Games အသစ်များကို စတင်ရှာဖွေနေပါသည်...\n")

    for player in GM_ACCOUNTS:
        print(f"⏳ {player} ၏ နောက်ဆုံးပွဲစဉ်များကို စစ်ဆေးနေသည်...")
        url = f"https://lichess.org/api/games/user/{player}?max={GAMES_PER_PLAYER}&perfType=blitz,rapid,classical"
        
        try:
            response = requests.get(url, headers={'Accept': 'application/x-chess-pgn'})
            
            if response.status_code == 200:
                pgn_io = io.StringIO(response.text)
                
                while True:
                    game = chess.pgn.read_game(pgn_io)
                    if game is None:
                        break 
                    
                    # 🌟 Duplicate စစ်ဆေးခြင်း 🌟
                    # Lichess PGN တွင် Site header ၌ URL (e.g. https://lichess.org/xxxx) ပါဝင်သည်
                    game_id = game.headers.get("Site", "")
                    
                    # ရွှေ့ကွက်မပါခြင်း သို့မဟုတ် ယခင်က ယူပြီးသားပွဲဖြစ်နေလျှင် ကျော်သွားမည်
                    if (not game.mainline_moves()) or (game_id in seen_history):
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
                    updated_history.add(game_id) # မှတ်တမ်းထဲသို့ ပေါင်းထည့်မည်
                    
            else:
                print(f"❌ {player} အတွက် ဆွဲယူမှု မအောင်မြင်ပါ။ (Code: {response.status_code})")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        time.sleep(2) # Rate Limit ကာကွယ်ရန်

    save_history(updated_history) # မှတ်တမ်းအသစ်ကို သိမ်းမည်
    return new_games

def update_today_file(new_games):
    if not new_games:
        print("\n✅ ယနေ့အတွက် ပွဲအသစ် မရှိသေးပါ။ (အားလုံး ယူပြီးသားများဖြစ်နေပါသည်)")
        return

    # 🌟 ယနေ့ ရက်အမည်ကို အလိုအလျောက် ယူမည် (ဥပမာ - monday) 🌟
    today_str = datetime.datetime.now().strftime("%A").lower()
    
    # အကယ်၍ Script run သည့်ရက်သည် DAYS list ထဲတွင် မပါလျှင် (မဖြစ်နိုင်သလောက်ပါ)
    if today_str not in DAYS:
        today_str = "monday"

    print(f"\n🎉 ပွဲအသစ် စုစုပေါင်း {len(new_games)} ပွဲ ရရှိပါသည်။ '{today_str}.json' သို့ Update လုပ်ပါမည်။")

    # ယနေ့အတွက် JSON ဖိုင်ကို အသစ်ပြင်ရေးမည်
    out_path = os.path.join(OUTPUT_DIR, f"{today_str}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(new_games, f, ensure_ascii=False, indent=2)

    # Versions တိုးပေးမည်
    versions = load_versions()
    versions[today_str] += 1
    save_versions(versions)
    
    print(f"✅ {today_str}.json ကို Version {versions[today_str]} ဖြင့် အောင်မြင်စွာ Update ပြုလုပ်ပြီးပါပြီ!")

if __name__ == "__main__":
    ensure_directories()
    new_master_games = fetch_new_games()
    update_today_file(new_master_games)
