import pandas as pd
import sqlite3
import random
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

print("၁။ Lichess Database ကို ဖတ်နေပါသည်...")
df = pd.read_csv('lichess_db_puzzle.csv', low_memory=False)

def get_level(rating):
    if rating <= 1200: return 'Easy'
    elif rating <= 1800: return 'Normal'
    else: return 'Hard'

phases = ['opening', 'middlegame', 'endgame', 'mix']
levels = ['Easy', 'Normal', 'Hard']

daily_puzzles = []
page_number = 1

print("၂။ Category ၁၂ မျိုးအတွက် ပုစ္ဆာများကို ရွေးချယ်နေပါသည်...")
for phase in phases:
    for level in levels:
        if phase == 'mix':
            filtered_df = df.copy()
        else:
            filtered_df = df[df['Themes'].str.contains(phase, na=False, case=False)].copy()
        
        if level == 'Easy': final_df = filtered_df[filtered_df['Rating'] <= 1200]
        elif level == 'Normal': final_df = filtered_df[(filtered_df['Rating'] > 1200) & (filtered_df['Rating'] <= 1800)]
        else: final_df = filtered_df[filtered_df['Rating'] > 1800]
            
        final_df = final_df[final_df['Popularity'] >= 90]
        sample_size = min(len(final_df), 10)
        selected_puzzles = final_df.sample(n=sample_size)

        diagram_number = 1
        for _, row in selected_puzzles.iterrows():
            title = f"{phase.capitalize()} ({level})"
            description = row['OpeningTags'] if phase == 'opening' and pd.notna(row['OpeningTags']) else str(row['Themes'])

            # 🌟 ပြုပြင်ထားသောအပိုင်း: Json Array အစား Mock Data အတိုင်း စာသားရိုးရိုး ပြန်သုံးပါမည် 🌟
            original_moves = str(row['Moves'])
            move_list = original_moves.strip().split() 
            
            if len(move_list) > 1:
                blunder_move = move_list[0]
                solution_only = move_list[1:]
                formatted_solution = f"{blunder_move}|{','.join(solution_only)}"
            else:
                formatted_solution = ",".join(move_list)

            daily_puzzles.append({
                'chapter_info': page_number,   
                'diagram_no': diagram_number,  
                'title': title,
                'description': description,
                'puzzle_mode': 1,
                'question_fen': row['FEN'],    
                'solution_list': formatted_solution, 
                'hint_mode': 1
            })
            diagram_number += 1
            
        page_number += 1

print("၃။ daily_puzzles.db ဖိုင်ကို တည်ဆောက်နေပါသည်...")
conn = sqlite3.connect('daily_puzzles.db')
cursor = conn.cursor()

cursor.execute('DROP TABLE IF EXISTS puzzles')

cursor.execute('''
    CREATE TABLE puzzles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_info INTEGER,
        diagram_no INTEGER,
        title TEXT,
        description TEXT,
        puzzle_mode INTEGER,
        question_fen TEXT,
        highlight_squares TEXT,
        spawn_piece TEXT,
        is_looping INTEGER,
        allow_king_sacrifice INTEGER,
        max_moves INTEGER,
        hint_mode INTEGER,
        solution_list TEXT,
        target_status TEXT,
        correct_rights TEXT,
        correct_option TEXT,
        correct_status TEXT,
        solution_move TEXT,
        arrows_data TEXT,
        explanation_text TEXT,
        explanation_highlights TEXT
    )
''')

for p in daily_puzzles:
    cursor.execute('''
        INSERT INTO puzzles (
            chapter_info, diagram_no, title, description, puzzle_mode, 
            question_fen, solution_list, hint_mode, is_looping, allow_king_sacrifice
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
    ''', (
        p['chapter_info'], p['diagram_no'], p['title'], p['description'], p['puzzle_mode'],
        p['question_fen'], p['solution_list'], p['hint_mode']
    ))

conn.commit()
conn.close()
print("Database ဖန်တီးမှု အောင်မြင်ပါသည်။")

# ---------------------------------------------------------
# Firebase Update
# ---------------------------------------------------------
print("၄။ Firebase တွင် Version အသစ်ကို ကြေညာနေပါသည်...")
try:
    cert_dict = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(cert_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    repo_name = os.environ.get('GITHUB_REPOSITORY')
    download_url = f"https://raw.githubusercontent.com/{repo_name}/main/daily_puzzles.db"

    doc_ref = db.collection('books').document('daily_puzzles')
    doc_ref.set({
        'title': 'Daily Tactics Training',
        'description': 'နေ့စဉ် လေ့ကျင့်ရန် Tactics ပုစ္ဆာ (၁၂၀) ပုဒ်။ (Lichess Database)',
        'url': download_url,
        'price': 0,
        'diagrams': 120,
        'isVisible': True,
        'order': -1,
        'version': firestore.Increment(1)
    }, merge=True)

    print("✅ အားလုံး အောင်မြင်စွာ ပြီးစီးပါပြီ!")

except Exception as e:
    print(f"❌ Firebase Update Error: {e}")
    exit(1)
