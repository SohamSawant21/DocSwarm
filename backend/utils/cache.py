import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'audit_cache.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_results (
            file_hash TEXT PRIMARY KEY,
            audit_json TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_cached_audit(file_hash: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT audit_json FROM audit_results WHERE file_hash = ?", (file_hash,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception as e:
        print(f"Cache read error: {e}")
    return None

def set_cached_audit(file_hash: str, audit_data: dict):
    if not file_hash:
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO audit_results (file_hash, audit_json) VALUES (?, ?)",
            (file_hash, json.dumps(audit_data))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cache write error: {e}")

init_db()
