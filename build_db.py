import urllib.request
import csv
import sqlite3
import os
import chess
import json
import codecs

CSV_URL = "https://database.lichess.org/lichess_db_puzzle.csv" 

def get_level_and_range(rating_str):
    try:
        r = int(float(rating_str))
        if r <= 1000: return 1, "Under 1000"
        elif r <= 1200: return 2, "1000-1199"
        elif r <= 1400: return 3, "1200-1399"
        elif r <= 1600: return 4, "1400-1599"
        elif r <= 1800: return 5, "1600-1799"
        elif r <= 2000: return 6, "1800-1999"
        elif r <= 2200: return 7, "2000-2199"
        elif r <= 2400: return 8, "2200-2399"
        else: return 9, "2400+"
    except: return 1, "Under 1000"

def build_databases():
    print("🌐 Downloading and reading Lichess CSV...")
    response = urllib.request.urlopen(CSV_URL)
    reader = csv.DictReader(codecs.iterdecode(response, 'utf-8'))
    
    level_buckets = {i: {1:[], 2:[], 3:[], 4:[]} for i in range(1, 10)}

    print("📂 Processing puzzles (Fixing Mix Chapter & FEN Generation)...")
    for row in reader:
        original_fen = row.get('FEN', row.get('fen', ''))
        moves_string = row.get('Moves', row.get('moves', ''))
        rating = row.get('Rating', row.get('rating', '1000'))
        themes = row.get('Themes', row.get('themes', '')).lower()

        if not original_fen or not moves_string: continue

        lvl, rating_range = get_level_and_range(rating)
        
        # 🌟 Mix (Chapter 4) သေချာပေါက် ပါဝင်လာစေမည့် Logic 🌟
        target_chap = None
        if 'opening' in themes and len(level_buckets[lvl][1]) < 10:
            target_chap = 1
            chap_name = "Opening"
        elif 'middlegame' in themes and len(level_buckets[lvl][2]) < 10:
            target_chap = 2
            chap_name = "Middlegame"
        elif 'endgame' in themes and len(level_buckets[lvl][3]) < 10:
            target_chap = 3
            chap_name = "Endgame"
        elif len(level_buckets[lvl][4]) < 10:
            # အပေါ်က ၃ မျိုး မဟုတ်တာတွေ၊ သို့မဟုတ် အပေါ်က ၃ မျိုး လူပြည့်သွားရင် 
            # Mix ထဲကို အလိုလို ရောက်သွားပါမည်။ (Mix လုံးဝ မကျန်ခဲ့တော့ပါ)
            target_chap = 4
            chap_name = "Mix Tactics"
        
        if target_chap is not None:
            moves_list = moves_string.strip().split()
            if len(moves_list) > 1:
                blunder_move = moves_list[0]
                solution_only = moves_list[1:]
                
                try:
                    # 🌟 (၁) နောက်ကွယ်တွင် Blunder ရွှေ့ပြီး FEN အသစ်ထုတ်ခြင်း 🌟
                    board = chess.Board(original_fen)
                    board.push_uci(blunder_move)
                    new_fen = board.fen()
                    
                    # 🌟 (၂) Answer တွင် Blunder ကို ပယ်ပြီး ကျန်တာကိုသာ ယူခြင်း 🌟
                    formatted_solution = ", ".join(solution_only)
                    sol_json = json.dumps([formatted_solution])
                    
                    diag_no = len(level_buckets[lvl][target_chap]) + 1
                    title = f"{chap_name} ({rating_range})"
                    desc = themes.replace(" ", ", ")
                    
                    level_buckets[lvl][target_chap].append((new_fen, sol_json, target_chap, diag_no, title, desc))
                except: pass 

        # အားလုံး (Level ၉ ခု x ၄၀ ပုဒ် = ၃၆၀) ပြည့်သွားလျှင် ရပ်မည်
        is_full = all(len(level_buckets[l][c]) == 10 for l in range(1, 10) for c in range(1, 5))
        if is_full: 
            print("✅ ပုစ္ဆာ (၃၆၀) ပုဒ်လုံး ပြည့်သွားပါပြီ! (Mix ပါဝင်ပါသည်)")
            break

    print("💾 Saving 9 Static Level Databases...")
    for lvl in range(1, 10):
        db_name = f"level_{lvl}.db"
        if os.path.exists(db_name): os.remove(db_name)
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE puzzles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            question_fen TEXT, 
                            solution_list TEXT, 
                            chapter_info INTEGER, 
                            diagram_no INTEGER, 
                            title TEXT, 
                            description TEXT)''')
        
        for c_id in range(1, 5):
            cursor.executemany("INSERT INTO puzzles (question_fen, solution_list, chapter_info, diagram_no, title, description) VALUES (?, ?, ?, ?, ?, ?)", 
                             level_buckets[lvl][c_id])
            
        conn.commit()
        conn.close()
        print(f"✅ Created: {db_name} (Contains all 4 Chapters)")

if __name__ == "__main__":
    build_databases()
