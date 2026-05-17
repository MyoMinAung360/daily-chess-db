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

# 🌟 Chapter ခွဲခြားသည့် Logic အား Mix Tactics ပါဝင်အောင် ပြင်ဆင်ထားပါသည် 🌟
def get_chapter_data(themes_str):
    t = themes_str.lower()
    if 'opening' in t: 
        return 1, "Opening"
    elif 'middlegame' in t: 
        return 2, "Middlegame"
    elif 'endgame' in t: 
        return 3, "Endgame"
    else: 
        # Opening, Middlegame, Endgame တစ်ခုမှ မဟုတ်လျှင် Mix Tactics ဟု သတ်မှတ်မည်
        return 4, "Mix Tactics"

def build_databases():
    print("🌐 Downloading and reading Lichess CSV...")
    
    response = urllib.request.urlopen(CSV_URL)
    reader = csv.DictReader(codecs.iterdecode(response, 'utf-8'))
    
    # Level ၉ ခု၊ Chapter ၄ ခု (Opening, Middle, End, Mix) အတွက် နေရာချခြင်း
    level_buckets = {i: {1:[], 2:[], 3:[], 4:[]} for i in range(1, 10)}

    print("📂 Processing puzzles (Building Static DBs with Mix Tactics)...")
    for row in reader:
        fen = row.get('FEN', row.get('fen', ''))
        moves_string = row.get('Moves', row.get('moves', ''))
        rating = row.get('Rating', row.get('rating', '1000'))
        themes = row.get('Themes', row.get('themes', ''))

        if not fen or not moves_string: continue

        lvl, rating_range = get_level_and_range(rating)
        chap_id, chap_name = get_chapter_data(themes)
        
        # သက်ဆိုင်ရာ Level နဲ့ Chapter အလိုက် ၁၀ ပုဒ် ပြည့်/မပြည့် စစ်မည်
        if len(level_buckets[lvl][chap_id]) < 10:
            moves_list = re.findall(r'[a-h][1-8][a-h][1-8][qrbn]?', moves_string.lower())

            if len(moves_list) > 1:
                first_move = moves_list[0]
                try:
                    board = chess.Board(fen)
                    board.push_uci(first_move)
                    new_fen = board.fen()
                    
                    remaining_moves = moves_list[1:]
                    new_moves_string = ", ".join(remaining_moves) 
                    new_solution_list_str = json.dumps([new_moves_string])
                    
                    diag_no = len(level_buckets[lvl][chap_id]) + 1
                    
                    # 🌟 Title တွင် Mix Tactics အပါအဝင် အမျိုးအစားနှင့် Rating ကို သိမ်းမည် 🌟
                    title = f"{chap_name} ({rating_range})" 
                    description = themes.replace(" ", ", ") 
                    
                    level_buckets[lvl][chap_id].append((new_fen, new_solution_list_str, chap_id, diag_no, title, description))
                except: pass 
                
        # စုစုပေါင်း ၃၆၀ ပုဒ် (Level ၉ ခု x Chapter ၄ ခု x ၁၀ ပုဒ်) ပြည့်သွားလျှင် ရပ်မည်
        is_full = all(len(level_buckets[l][c]) == 10 for l in range(1, 10) for c in range(1, 5))
        if is_full:
            print("✅ ပုစ္ဆာအားလုံး (Opening, Middlegame, Endgame, Mix) ပြည့်စုံစွာ ရရှိပြီးပါပြီ။")
            break

    print("💾 Creating .db files...")
    for lvl in range(1, 10):
        db_name = f"level_{lvl}.db"
        if os.path.exists(db_name): os.remove(db_name)
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE puzzles (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                question_fen TEXT, 
                solution_list TEXT, 
                chapter_info INTEGER, 
                diagram_no INTEGER, 
                title TEXT, 
                description TEXT
            )
        ''')
        
        for chap_id in range(1, 5):
            cursor.executemany('''
                INSERT INTO puzzles (question_fen, solution_list, chapter_info, diagram_no, title, description) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', level_buckets[lvl][chap_id])
            
        conn.commit()
        conn.close()
        print(f"✅ Created: {db_name}")

if __name__ == "__main__":
    build_databases()
