import urllib.request
import csv
import sqlite3
import os
import chess
import json
import codecs
import re

CSV_URL = "https://database.lichess.org/lichess_db_puzzle.csv" 

def get_level_and_range(rating_str):
    try:
        r = int(float(rating_str))
        if r < 1000: return 1, "Under 1000"
        elif r < 1200: return 2, "1000-1199"
        elif r < 1400: return 3, "1200-1399"
        elif r < 1600: return 4, "1400-1599"
        elif r < 1800: return 5, "1600-1799"
        elif r < 2000: return 6, "1800-1999"
        elif r < 2200: return 7, "2000-2199"
        elif r < 2400: return 8, "2200-2399"
        else: return 9, "2400+"
    except: return 1, "Under 1000"

def build_databases():
    print("🌐 Downloading and reading Lichess CSV...")
    response = urllib.request.urlopen(CSV_URL)
    reader = csv.DictReader(codecs.iterdecode(response, 'utf-8'))
    
    # Chapter 1: Opening, 2: Middlegame, 3: Endgame, 4: Mix
    level_buckets = {i: {1:[], 2:[], 3:[], 4:[]} for i in range(1, 10)}

    print("📂 Processing puzzles (Static DBs - Discarding Blunder Move)...")
    for row in reader:
        fen = row.get('FEN', row.get('fen', ''))
        moves_string = row.get('Moves', row.get('moves', ''))
        rating = row.get('Rating', row.get('rating', '1000'))
        themes = row.get('Themes', row.get('themes', '')).lower()

        if not fen or not moves_string: continue

        lvl, rating_range = get_level_and_range(rating)
        
        # Chapter သတ်မှတ်ခြင်း Logic
        # Opening, Middlegame, Endgame မဟုတ်လျှင် Mix (4) ထဲသို့ အလိုလို ထည့်မည်
        if 'opening' in themes: 
            target_chapter = 1
            chap_name = "Opening"
        elif 'middlegame' in themes: 
            target_chapter = 2
            chap_name = "Middlegame"
        elif 'endgame' in themes: 
            target_chapter = 3
            chap_name = "Endgame"
        else:
            target_chapter = 4
            chap_name = "Mix Tactics"

        # သက်ဆိုင်ရာ Chapter တွင် ၁၀ ပုဒ် မပြည့်သေးလျှင် ထည့်မည်
        if len(level_buckets[lvl][target_chapter]) < 10:
            moves_list = re.findall(r'[a-h][1-8][a-h][1-8][qrbn]?', moves_string.lower())
            
            if len(moves_list) > 1:
                try:
                    # 🌟 Blunder Move ကို ပယ်ဖျက်၍ FEN အသစ်ထုတ်သည့် လော့ဂျစ် 🌟
                    board = chess.Board(fen)
                    blunder_move = moves_list[0]
                    board.push_uci(blunder_move) # Blunder ကို ကစားလိုက်သည်
                    
                    new_fen = board.fen() # Blunder ကစားပြီးနောက် FEN (မေးခွန်းအတွက် FEN)
                    
                    # Blunder ကို ဖြုတ်ပြီး ကျန်သောအကွက်များကို ", " ခံ၍ သိမ်းသည်
                    remaining_moves = moves_list[1:]
                    formatted_solution = ", ".join(remaining_moves)
                    sol_json = json.dumps([formatted_solution])
                    
                    diag_no = len(level_buckets[lvl][target_chapter]) + 1
                    title = f"{chap_name} ({rating_range})" 
                    desc = themes.replace(" ", ", ") 
                    
                    level_buckets[lvl][target_chapter].append((new_fen, sol_json, target_chapter, diag_no, title, desc))
                except: pass 
                
        # အားလုံး (360 ပုဒ်) ပြည့်လျှင် ရပ်မည်
        is_full = all(len(level_buckets[l][c]) == 10 for l in range(1, 10) for c in range(1, 5))
        if is_full: break

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
        print(f"✅ Created: {db_name} (Contains 4 Chapters)")

if __name__ == "__main__":
    build_databases()
