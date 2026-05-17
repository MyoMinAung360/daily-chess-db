import urllib.request
import csv
import sqlite3
import os
import chess
import json
import codecs

# 🌟 ဆရာပြောသော Lichess CSV Link အား ထည့်သွင်းထားပါသည် 🌟
CSV_URL = "https://database.lichess.org/lichess_db_puzzle.csv" 

def get_level(rating_str):
    try:
        r = int(float(rating_str))
        if r < 1000: return 1
        elif r < 1200: return 2
        elif r < 1400: return 3
        elif r < 1600: return 4
        elif r < 1800: return 5
        elif r < 2000: return 6
        elif r < 2200: return 7
        elif r < 2400: return 8
        else: return 9
    except: return 1 

def get_chapter(themes_str):
    t = themes_str.lower()
    if 'opening' in t: return 1
    elif 'middlegame' in t: return 2
    elif 'endgame' in t: return 3
    else: return 4 

def build_databases():
    print("🌐 Downloading and reading Lichess CSV...")
    
    # Github တွင် ဖိုင်ဆိုဒ်ကြီး၍ Error မတက်စေရန် တစ်ကြောင်းချင်း ဖတ်မည့်စနစ်
    response = urllib.request.urlopen(CSV_URL)
    reader = csv.DictReader(codecs.iterdecode(response, 'utf-8'))
    
    level_buckets = {i: {1:[], 2:[], 3:[], 4:[]} for i in range(1, 10)}

    print("📂 Processing puzzles...")
    for row in reader:
        fen = row.get('FEN', row.get('fen', ''))
        moves = row.get('Moves', row.get('moves', ''))
        rating = row.get('Rating', row.get('rating', '1000'))
        themes = row.get('Themes', row.get('themes', 'mix'))

        if not fen or not moves: continue

        lvl = get_level(rating)
        chap = get_chapter(themes)
        
        # Level ၁ ခုလျှင် Chapter တစ်ခုကို ၁၀ ပုဒ် ပြည့်/မပြည့် စစ်မည်
        if len(level_buckets[lvl][chap]) < 10:
            moves_list = moves.split()
            if len(moves_list) > 1:
                try:
                    board = chess.Board(fen)
                    board.push_uci(moves_list[0])
                    new_fen = board.fen()
                    new_moves = json.dumps([" ".join(moves_list[1:])])
                    diag_no = len(level_buckets[lvl][chap]) + 1
                    level_buckets[lvl][chap].append((new_fen, new_moves, chap, diag_no))
                except: pass 
                
        # Database အားလုံး ပုစ္ဆာပြည့်သွားပါက ဆက်မဖတ်ဘဲ ရပ်မည် (အချိန်သက်သာစေရန်)
        is_full = all(len(level_buckets[l][c]) == 10 for l in range(1, 10) for c in range(1, 5))
        if is_full:
            print("✅ ပုစ္ဆာအားလုံး ပြည့်သွားပါပြီ။ CSV ဖတ်ခြင်းကို ရပ်ပါမည်။")
            break

    print("💾 Creating .db files...")
    for lvl in range(1, 10):
        db_name = f"level_{lvl}.db"
        if os.path.exists(db_name): os.remove(db_name)
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE puzzles (id INTEGER PRIMARY KEY AUTOINCREMENT, question_fen TEXT, solution_list TEXT, chapter_info INTEGER, diagram_no INTEGER)")
        
        for chap in range(1, 5):
            cursor.executemany("INSERT INTO puzzles (question_fen, solution_list, chapter_info, diagram_no) VALUES (?, ?, ?, ?)", level_buckets[lvl][chap])
            
        conn.commit()
        conn.close()
        print(f"✅ Created: {db_name}")

if __name__ == "__main__":
    build_databases()
