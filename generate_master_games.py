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

GAMES_PER_PLAYER = 15 

# 🌟 ၃ လစာ (သို့) ခန့်မှန်းခြေ နောက်ဆုံး ပွဲ ၅၀၀၀ ကိုသာ မှတ်ထားမည့် ကန့်သတ်ချက်
MAX_HISTORY = 5000 

def ensure_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def load_history():
    """ယခင်ဆွဲယူပြီးသား ပွဲစဉ် ID များကို ပြန်ဖတ်မည်"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f) # အစဉ်လိုက် မှတ်ထားနိုင်ရန် List အနေဖြင့် ထုတ်မည်
    return []

def save_history(history_list):
    """ယခုအသစ်ရလာသော ပွဲစဉ် ID များကို မှတ်တမ်းထဲ ပြန်ထည့်မည်"""
    
    # 🌟 နောက်ဆုံး ၅၀၀၀ ကိုသာ ဖြတ်ယူမည် (ပိုနေသောအဟောင်းများကို ဖယ်ရှားမည်)
    if len(history_list) > MAX_HISTORY:
        history_list = history_list[-MAX_HISTORY:]
        
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history_list, f)

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
    history_list = load_history()
    seen_set = set(history_list) # အမြန်ရှာဖွေနိုင်ရန် Set အဖြစ် ခဏပြောင်းမည်
    
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
                    
                    # မှတ်တမ်းအသစ်ကို List ရော Set ထဲပါ ပေါင်းထည့်မည်
                    seen_set.add(game_id)
                    history_list.append(game_id) 
                    
            else:
                print(f"❌ {player} အတွက် ဆွဲယူမှု မအောင်မြင်ပါ။ (Code: {response.status_code})")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        time.sleep(2) # Rate Limit ကာကွယ်ရန်

    save_history(history_list) # ပြောင်းလဲသွားသော မှတ်တမ်းကို သိမ်းမည်
    return new_games

def update_today_file(new_games):
    if not new_games:
        print("\n✅ ယနေ့အတွက် ပွဲအသစ် မရှိသေးပါ။ (အားလုံး ယူပြီးသားများဖြစ်နေပါသည်)")
        return

    # ယနေ့ ရက်အမည်ကို အလိုအလျောက် ယူမည် (ဥပမာ - monday)
    today_str = datetime.datetime.now().strftime("%A").lower()
    if today_str not in DAYS:
        today_str = "monday"

    print(f"\n🎉 ပွဲအသစ် စုစုပေါင်း {len(new_games)} ပွဲ ရရှိပါသည်။ '{today_str}.json' သို့ Update လုပ်ပါမည်။")

    out_path = os.path.join(OUTPUT_DIR, f"{today_str}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(new_games, f, ensure_ascii=False, indent=2)

    versions = load_versions()
    versions[today_str] += 1
    save_versions(versions)
    
    print(f"✅ {today_str}.json ကို Version {versions[today_str]} ဖြင့် အောင်မြင်စွာ Update ပြုလုပ်ပြီးပါပြီ!")

if __name__ == "__main__":
    ensure_directories()
    new_master_games = fetch_new_games()
    update_today_file(new_master_games)
